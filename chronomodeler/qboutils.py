import requests, json
import pandas as pd
import datetime as dt
from stqdm import stqdm


def extract_rows(item):
    """
        Function that converts a QBO API response into a dataframe
    """
    extracted_rows = []
    if 'ColData' in item:
        amount = item['ColData'][1].get('value') if len(item['ColData']) > 1 else 0
        extracted_rows.append({
            "LineItem": item['ColData'][0].get('value'),
            "Amount": float(amount) if (amount is not None and amount != '') else 0
        })
    elif isinstance(item, dict):
        for _, subitem in item.items():
            if isinstance(subitem, dict) or isinstance(subitem, list):
                exrows = extract_rows(subitem)
                extracted_rows += exrows
    elif isinstance(item, list):
        for _, subitem in enumerate(item):
            if isinstance(subitem, dict) or isinstance(subitem, list):
                exrows = extract_rows(subitem)
                extracted_rows += exrows
    return extracted_rows


def get_qbo_report(realm_id, access_token, report_name, start_date: dt.datetime, end_date: dt.datetime):
    BASE_URL = "https://quickbooks.api.intuit.com"
    assert start_date < end_date
    assert report_name in ["ProfitAndLoss", "BalanceSheet"]
    payload = {
        "accounting_method": "Accrual",
        "start_date": start_date.strftime("%Y-%m-%d"),
        "end_date": end_date.strftime("%Y-%m-%d"),
    }
    headers = {
        "Accept": "application/json",
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }
    url = f"{BASE_URL}/v3/company/{realm_id}/reports/{report_name}"
    res = requests.get(url, headers=headers, params=payload)
    resobj = json.loads(res.text)
    rows = extract_rows(resobj)
    df = pd.DataFrame(rows)
    return df


def create_calendar_seq(start_year: int, end_year: int, data_freq = "Yearly"):
    """
        Create a sequence of datetimes between the start year and the end year
    """
    dates = []
    cur_date = dt.datetime(year=start_year, month=1, day=1)
    while cur_date.year <= end_year:
        dates.append(cur_date)
        if data_freq == "Yearly":
            cur_date = dt.datetime(year=cur_date.year + 1, month = 1, day = 1)
        elif data_freq == "Monthly":
            if cur_date.month < 12:
                cur_date = dt.datetime(year = cur_date.year, month=cur_date.month + 1, day = 1)
            else:
                cur_date = dt.datetime(year=cur_date.year + 1, month = 1, day = 1) # reset to january
    return dates


def fetch_all_qbo_data(realm_id, access_token, start_year: int, end_year: int, data_freq = "Yearly"):
    """
        Run the progress and collect all qbo data
    """
    report_list = ["ProfitAndLoss", "BalanceSheet"]
    datelist = create_calendar_seq(start_year, end_year, data_freq) + [dt.datetime(end_year + 1, 1, 1)]

    # make a combination of all parameters
    paramlist = []
    for r in report_list:
        for i in range(len(datelist) - 1):
            paramlist.append((r, datelist[i], datelist[i+1] - dt.timedelta(days = 1) ))

    # finally run the loop
    dflist = []
    for i in stqdm(range(len(paramlist))):
        report_name, start, end = paramlist[i]
        df = get_qbo_report(realm_id, access_token, report_name, start, end)
        df['Time'] = end  # accounting is consolidated as of end time
        df['ReportType'] = report_name
        dflist.append(df)
    
    df = pd.concat(dflist)

    df2 = pd.pivot_table(df, values = 'Amount', columns = 'LineItem', index = 'Time', fill_value = 0.0).reset_index()
    return df2


