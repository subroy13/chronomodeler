from typing import Dict, List
import pandas as pd
import numpy as np
import re
import datetime as dt

def guess_data_frequency(time_col: pd.Series):
    # Calculate the time differences between consecutive timestamps
    time_diff_mode = time_col.diff().dt.days.mode().values[0]
    if time_diff_mode == 1:
        return "D"
    elif time_diff_mode == 7:
        return "W"
    elif time_diff_mode >= 29 and time_diff_mode <= 31:
        return "M"
    elif time_diff_mode >= (3 * 29) and time_diff_mode <= (3 * 31):
        return "Q"
    else:
        return "Y"
    
def convert_to_datetime(d):
    if isinstance(d, dt.datetime):
        return d 
    elif isinstance(d, dt.date):
        return dt.datetime(year=d.year, month=d.month, day=d.day)
    else:
        return dt.datetime.strptime(d, "%Y-%m-%d")

    
def get_date_list(date_interval: List[dt.datetime], freq: str = "M"):
    result = []
    start = convert_to_datetime(date_interval[0])
    end = convert_to_datetime(date_interval[1])
    current = start
    while current <= end:
        result.append(current)
        if freq == "D":
            current += dt.timedelta(days = 1)
        elif freq == "W":
            current += dt.timedelta(days = 7)
        elif freq == "M":
            current = dt.datetime(
                year=current.year if current.month < 12 else current.year+1,
                month=current.month + 1 if current.month < 12 else 1,
                day=current.day
            )
        elif freq == "Q":
            current = dt.datetime(
                year=current.year if current.month < 10 else current.year + 1,
                month=current.month + 3 if current.month < 10 else (current.month + 3) % 12,
                day=current.day
            )
        elif freq == "Y":
            current = dt.datetime(
                year=current.year+1,
                month=current.month, day=current.day
            )
        else:
            raise NotImplementedError("Invalid date frequency")
    return result

def prev_date_list(cur_date: dt.datetime, freq: str = "M", n: int = 5):
    date_list = []
    current = convert_to_datetime(cur_date)
    for _ in range(n):
        date_list.append(current)
        if freq == "D":
            current -= dt.timedelta(days = 1)
        elif freq == "W":
            current -= dt.timedelta(days = 7)
        elif freq == "M":
            current = dt.datetime(
                year=current.year if current.month > 1 else current.year-1,
                month=current.month - 1 if current.month > 1 else 12,
                day=current.day
            )
        elif freq == "Q":
            current = dt.datetime(
                year=current.year if current.month > 3 else current.year - 1,
                month=current.month - 3 if current.month > 4 else (current.month + 9),
                day=current.day
            )
        elif freq == "Y":
            current = dt.datetime(
                year=current.year-1,
                month=current.month, day=current.day
            )
        else:
            raise NotImplementedError("Invalid date frequency")
    return date_list[::-1]
    

def convert_annual_growth_rate(growth_rate: float, freq: str = "M"):
    freq_map = {
        'D': 365, 'W': 52, 'M': 12, 'Q': 4, 'H': 2, 'Y': 1
    }
    return (growth_rate / (100 * freq_map[freq] ))

def get_data_cell_value(df, cond, colname):
    df1 = df.loc[cond, colname]
    if df1.shape[0] == 0:
        return None
    else:
        return df1.values[0]



def apply_single_transformation(x: pd.Series, method: str, parameter):
    if method == "Identity":
        return x
    elif method == "Sine":
        return np.sin(2 * np.pi * x / parameter)
    elif method == "Cosine":
        return np.cos(2 * np.pi * x / parameter)
    elif method == "Exponent":
        return np.expm1(x)
    elif method == "Log":
        return np.log1p(x)
    elif method == "Power":
        return x ** float(parameter)
    elif method == "Lag":
        return x.shift(int(parameter))
    else:
        raise NotImplementedError("Invalid transformation")


def apply_mixer_transformation(collist: List[pd.Series], method: str):
    if method == "Add":
        out = pd.Series(data=0, index=collist[0].index)
        for col in collist:
            out += col
    elif method == "Subtract":
        out = collist[0] - collist[1]
    elif method == "Multiply":
        out = collist[0] * collist[1]
    elif method == "Division":
        out = collist[0] / collist[1]
    else:
        raise NotImplementedError("Invalid mixer")
    return out


def apply_filters(dataframe: pd.DataFrame, filters: List[Dict]):
    """
        Returns a boolean series of rows to filter, using a list of dict configuration as below
        [
            {"Time": {"between": "2019/01/01-2023/04/30" } },
            { "Column1": {"geq": 100} }, 
            {
                "OR": [
                    { "Column1": {"leq": 150} },
                    { "Column2": {"between": 1.5-2.5} }
                ]
            }
        ]
    """
    filter_condition = pd.Series(True, index=dataframe.index)  # Initial condition (True for all rows)
    for filter_item in filters:
        key, value = list(filter_item.items())[0]
        key = re.sub(re.compile(r'#.*'), '', key)  # replace something like OR#12 => OR
        if key == 'OR':
            or_filter_condition = pd.Series(False, index=dataframe.index)  # Initial condition (False for all rows)
            for or_condition in value:
                or_filter_condition |= apply_filters(dataframe, [or_condition])
            return or_filter_condition
        elif key == 'AND':
            and_filter_condition = pd.Series(True, index=dataframe.index)  # Initial condition (True for all rows)
            for and_condition in value:
                and_filter_condition &= apply_filters(dataframe, [and_condition])
            return and_filter_condition
        else:
            filter_condition &= create_single_filter(dataframe, value, key)
    return filter_condition


def create_single_filter(
    dataframe: pd.DataFrame,
    filter_item: Dict,
    column_name: str
):
    filter_operator, filter_value = list(filter_item.items())[0]
    if filter_operator == 'geq':
        return dataframe[column_name] >= filter_value
    if filter_operator == 'ge':
        return dataframe[column_name] > filter_value
    elif filter_operator == 'leq':
        return dataframe[column_name] <= filter_value
    elif filter_operator == 'le':
        return dataframe[column_name] < filter_value
    elif filter_operator == 'eq':
        return dataframe[column_name] == filter_value
    elif filter_operator == 'neq':
        return dataframe[column_name] != filter_value
    elif filter_operator == 'between':
        filter_range_low, filter_range_high = filter_value.split('-')
        try:
            filter_range_low = float(filter_range_low)
            filter_range_high = float(filter_range_high)
            if filter_range_low is None or filter_range_high is None:
                raise ValueError()
            return (dataframe[column_name] >= filter_range_low) & (dataframe[column_name] <= filter_range_high)
        except:
            return (dataframe[column_name] >= filter_range_low) & (dataframe[column_name] <= filter_range_high)
    elif filter_operator == 'in':
        filter_values = filter_value.split(',')
        return dataframe[column_name].isin(filter_values)
    elif filter_operator == 'notin':
        filter_values = filter_value.split(',')
        return ~dataframe[column_name].isin(filter_values)
    elif filter_operator == 'startswith':
        return dataframe[column_name].str.startswith(filter_value)
    elif filter_operator == 'endswith':
        return dataframe[column_name].str.endswith(filter_value)
    elif filter_operator == 'contains':
        return dataframe[column_name].str.contains(filter_value)
    elif filter_operator == 'notcontains':
        return ~dataframe[column_name].str.contains(filter_value)
    else:
        raise NotImplementedError(f"Invalid filter operator: {filter_operator}")


def train_test_split(df: pd.DataFrame, filter_dates: List[dt.datetime]):
    split_dates = "-".join([x.strftime('%Y/%m/%d') for x in filter_dates])
    subdf = df.loc[apply_filters(df, [{'Time': {'between': split_dates } }])].dropna().copy(deep = True)
    return subdf