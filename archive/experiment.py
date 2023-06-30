from typing import List, Dict, Tuple
import re
import datetime as dt
import pandas as pd
import numpy as np
from barfi import Block

from .preprocessor import (
    apply_filters, apply_mixer_transformation, apply_single_transformation,
    guess_data_frequency, get_date_list, prev_date_list, convert_annual_growth_rate,
    get_data_cell_value
)
from .expconfig import ExperimentConfig
from .dbutils import get_experiment_data
from .models import ChronoModel

class Experiment:

    def __init__(self, barfi_schema: dict, data: pd.DataFrame, sim_name: str):
        self.schema = barfi_schema
        self.data = data
        self.simulation_name = sim_name
        self.results = {}
        self.target_colname = None

    def train_test_split(self, df: pd.DataFrame, filter_dates: List[dt.datetime]):
        split_dates = "-".join([x.strftime('%Y/%m/%d') for x in filter_dates])
        subdf = df.loc[apply_filters(df, [{'Time': {'between': split_dates } }])].dropna().copy(deep = True)
        return subdf

    def extract_variables(self):
        var_details = {}
        for key, val in self.schema.items():
            if val['type'] in ['Dependent Variable', 'Independent Variable']:
                block: Block = val['block']
                colname = block.get_option(name = "column-option")

                if colname not in var_details:
                    if 'from' in val['interfaces']['Modelling Method']:
                        model_method_key = list(val['interfaces']['Modelling Method']['from'].keys())[0]
                        if self.schema[model_method_key]['type'] == "Modelling":
                            # see if we have the prediction method
                            model_method = self.schema[model_method_key]['block'].get_option(name = 'method-option')
                            model_param = self.schema[model_method_key]['block'].get_option(name = 'method-param')
                            var_details[colname] = {
                                "model_method": model_method,
                                "model_parameter": model_param,
                                "type": val['type'].split()[0]
                            }
        self.variables = var_details

    def get_input_blocks(self, schemapart: Dict) -> List[str]:
        inputs = []
        for _, item in schemapart['interfaces'].items():
            if item.get('type') == 'intput':
                input_key = list(item['from'].keys())[0]
                inputs.append(input_key)
        return inputs
    
    def get_experiment_config(self):
        return ExperimentConfig.get_experiment_config(self.schema)
    

    def perform_transformations(self, df, root = None):
        """
            Performs a topological sort on the computation graph,
            to understand in which order the transformations need to 
            be applied and what all transformations, and compute
            the transformations on the provided dataframe
        """
        if root is None:
            for key, val in self.schema.items():
                if val['type'] == 'Dependent Variable':
                    root = val

        block: Block = root['block']
        if root['type'] == 'Independent Variable':
            colname = block.get_option(name = "column-option")
            return df[colname]
        elif root['type'] == 'Constant':
            const_value = block.get_option(name = "value-option")
            return pd.Series(data=const_value, index=df.index)
        elif root['type'] == 'Transformation':
            method = block.get_option(name = "method-option")
            parameter = block.get_option(name = "method-param")

            # first obtain the previous dependent nodes
            inp_blocks = self.get_input_blocks(root)
            x = self.perform_transformations(df, self.schema[inp_blocks[0]])
            return apply_single_transformation(x, method, parameter)
        elif root['type'] in ['Add', 'Subtract', 'Multiply', 'Division']:
            inp_blocks = self.get_input_blocks(root)
            collist = [self.perform_transformations(df, self.schema[i]) for i in inp_blocks]
            return apply_mixer_transformation(collist, root['type'])
        elif root['type'] == 'Modelling':
            pass
        elif root['type'] == 'Merge':
            inp_blocks = self.get_input_blocks(root)
            collist = []
            for i in inp_blocks:
                x = self.perform_transformations(df, self.schema[i])
                if isinstance(x, list):
                    collist += x
                else:
                    collist.append(x)
            return collist
        elif root['type'] == 'Dependent Variable':
            inp_blocks = self.get_input_blocks(root)
            target = block.get_option(name = "column-option")
            output = {
                'target': target,
                'features': [],
                'data': None
            }
            for key in inp_blocks:
                if self.schema[key]['type'] == 'Merge':
                    collist = self.perform_transformations(df, self.schema[key])
                    for i in range(len(collist)):
                        feature_col = "Feature" + str(i+1)
                        output['features'].append(feature_col)
                        df[feature_col] = collist[i]
                    output['data'] = df
                elif self.schema[key]['type'] == 'Modelling':
                    method = self.schema[key]['block'].get_option('method-option')
                    parameter = self.schema[key]['block'].get_option('method-param')
                    output['Model'] = {
                        'method': method,
                        'parameter': parameter
                    }
            return output
        else:
            raise NotImplementedError(f"Invalid node type {root['type']}")
        
    def create_pred_df(self, pred_date: dt.datetime, data_freq: str, variables: str, total_df: pd.DataFrame):
        BACK_WINDOW = 5
        prev_dates = prev_date_list(pred_date, data_freq, n = BACK_WINDOW)        
        collist = [col for col in variables]
        new_data = total_df[collist + ['Time', 'TimeIndex']]
        new_data = new_data.loc[new_data['Time'] <= pred_date].copy(deep = True)
        for d in prev_dates:
            row = {'Time': d, 'TimeIndex': None }
            for col in collist + ['TimeIndex']:
                if col == 'TimeIndex':
                    row[col] = get_data_cell_value(new_data, new_data['Time'] == d, 'TimeIndex')
                elif variables[col]['type'] == 'Dependent':
                    row[col] = get_data_cell_value(new_data, new_data['Time'] == d, col)
                else:
                    method = variables[col].get("model_method")
                    parameter = variables[col].get("model_parameter")
                    if method == "Identity":
                        # look for data present in new_data
                        row[col] = get_data_cell_value(new_data, new_data['Time'] == d, col)
                    elif method == "CAGR":
                        stride, window = [int(x) for x in parameter.split(",")]

                        # calculate the CAGR
                        oldest_val = new_data.iloc[:window][col].mean(skipna=True)
                        ntime = int(new_data.shape[0]/window)
                        newest_val = new_data.iloc[(window * (ntime - 1)):(window * ntime)][col].mean(skipna=True)
                        cagr_rate = ((newest_val / oldest_val)**(1 / ntime) - 1)

                        prev_d = prev_date_list(d, data_freq, n = 1 + int(stride) )[0]
                        row[col] = get_data_cell_value(new_data, new_data['Time'] == prev_d, col) * (1 + cagr_rate) ** (stride / window)
                    elif method == "Growth":
                        offset, growth_rate = [float(x) for x in parameter.split(",")]
                        prev_d = prev_date_list(d, data_freq, n = 1 + int(offset) )[0]
                        row[col] = get_data_cell_value(new_data, new_data['Time'] == prev_d, col) * (1 + convert_annual_growth_rate(growth_rate, data_freq) )**offset
                    elif method == "Experiment Output":
                        prev_exp_df = get_experiment_data(self.simulation_name, int(parameter))
                        row[col] = get_data_cell_value(prev_exp_df, prev_exp_df['Time'] == d, col)
                    else:
                        raise NotImplementedError("Invalid prediction model method")  
            new_data = pd.concat([new_data, pd.DataFrame([row])])
            
        new_data = new_data.reset_index(drop = True)
        last_value = new_data['TimeIndex'].last_valid_index()
        end = new_data.loc[last_value, 'TimeIndex']
        offset = int(end - last_value)
        new_data['TimeIndex'] = new_data['TimeIndex'].fillna(pd.Series(range(offset, new_data.shape[0] + offset )) )
        return new_data.tail(BACK_WINDOW)

                    
    def do_experiment(
            self,  
            train_dates: List[dt.datetime], 
            test_dates: List[dt.datetime],
            pred_dates: List[dt.datetime]
        ):
        # Step 1: Apply the transformations
        output = self.perform_transformations(self.data)
        
        # Step 2: Split into training, testing data
        train_df = self.train_test_split(output['data'], train_dates).dropna().reset_index(drop = True)
        test_df = self.train_test_split(output['data'], test_dates).dropna().reset_index(drop = True)
        features = output['features']
        target = output['target']
        self.target_colname = target
        X_train = train_df[features]
        y_train = train_df[target]
        X_test = test_df[features]
        y_test = test_df[target]

        # Step 3: Fit model and Perform testing
        method = output['Model'].get('method')
        mod = ChronoModel(model_name=method, parameters = output['Model'].get('parameter'))
        mod.fit_model(X_train, y_train)
        error_df = mod.predict_model(X_test, y_test)
        self.results = mod.metrics

        # Step 4: Fit Model on train + test data
        new_train_df = self.train_test_split(output['data'], [train_dates[0], test_dates[1]]).dropna().reset_index(drop = True)
        mod.fit_model(new_train_df[features], new_train_df[target], update_metrics=False)

        # Step 5: Perform the prediction
        self.extract_variables()
        data_freq = guess_data_frequency(self.data['Time'])
        pred_date_list = get_date_list(pred_dates, data_freq)

        total_df = self.data[[var for var in self.variables] + ['Time', 'TimeIndex']].copy(deep = True)    # includes existing projection as well if present 

        for pred_date in pred_date_list:
            pred_df = self.create_pred_df(pred_date, data_freq, self.variables, total_df)  # last row is to be predicted, previous rows may come from existing predicted data / known data
            pred_transform = self.perform_transformations(pred_df)
            predictions = mod.predict_model(pred_transform['data'][pred_transform['features']].dropna().reset_index(drop = True))            
            predval = predictions.iloc[predictions.shape[0] - 1]['Prediction']
            row = pd.DataFrame([ pred_df.to_dict('records')[pred_df.shape[0] - 1] | { pred_transform['target'] : predval } ])
            total_df = pd.concat([
                total_df,
                row[[var for var in self.variables] + ['Time', 'TimeIndex']]
            ])

        # finally filter the total df to only prediction dates
        total_df['Human Time'] = total_df['Time'].dt.strftime('%d %b, %Y')
        final_df = total_df.tail(len(pred_date_list))
        return final_df, new_train_df[features].shape















    
