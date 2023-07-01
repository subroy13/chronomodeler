from typing import Dict, List
from barfi import Block
import pandas as pd
import datetime as dt

from chronomodeler.preprocessor import (
    apply_filters, apply_mixer_transformation,
    apply_single_transformation, train_test_split
)
from chronomodeler.chronomodel import ChronoModel


class ExperimentConfig:
    """
        Class for handling barfi block based transformations
    """

    def __init__(self, config: Dict) -> None:
        self.config = config


    def barfi_input_blocks(self, schemapart: Dict) -> List[str]:
        inputs = []
        for _, item in schemapart['interfaces'].items():
            if item.get('type') == 'intput':
                input_key = list(item['from'].keys())[0]
                inputs.append(input_key)
        return inputs
    
    def get_target_variable(self):
        for key in self.config:
            if self.config[key]['type'] == 'Dependent Variable':
                return key, self.config[key]['column']

    def get_root(self):
        root, _ = self.get_target_variable()
        return root
    
    def get_nodeconfig(self, nodekey):
        return self.config[nodekey]
    
    def get_final_model(self):
        root = self.get_root()
        nodeconfig = self.get_nodeconfig(root)
        return {
            'method': nodeconfig.get('method'),
            'parameter': nodeconfig.get('parameter')
        }


    @classmethod
    def from_barfi_blocks(cls, barfi_schema: Dict):
        output = {}
        for key, val in barfi_schema.items():
            block: Block = val['block']
            if val['type'] == 'Transformation':
                block_params = {
                    "method": block.get_option("method-option"),
                    "parameter": block.get_option("method-param")
                }
            elif val['type'] == 'Modelling':
                params = block.get_option("method-param").split(",")
                try:
                    params = [float(param) for param in params]
                except Exception as e:
                    params = []
                block_params = {
                    "method": block.get_option("method-option"),
                    "parameter": params
                }
            elif val['type'] in ['Dependent Variable', 'Independent Variable']:
                block_params = {
                    "column": block.get_option("column-option")
                }
            elif val['type'] == 'Constant':
                block_params = {
                    "value": block.get_option("value-option")
                }
            else:
                block_params = {}
            item = {
                'type': val['type'],
                'dependencies': cls.barfi_input_blocks(val)
            } | block_params
            output[key] = item

        return cls(config = output)
    

    def extract_barfi_display_node_options(self, nodeconfig: Dict):
        if nodeconfig['type'] == 'Transformation':
            return [
                ['display-option', 'Apply Transformation'], 
                ['method-option', nodeconfig.get('method')],
                ['method-param', nodeconfig.get('parameter') ]
            ]
        elif nodeconfig['type'] == 'Modelling':
            return [
                ['display-option', 'Modelling Method'],
                ['method-option', nodeconfig.get('method')],
                ['method-param', ','.join(nodeconfig.get('parameter', []))]
            ]
        elif nodeconfig['type'] in ['Independent Variable', 'Dependent Variable']:
            return [
                ['display-option', nodeconfig['type']],
                ['column-option', nodeconfig.gert('column')]
            ]
        elif nodeconfig['type'] == 'Constant':
            return [
                ['display-option', nodeconfig['type']],
                ['value-option', nodeconfig.gert('value')]
            ]
        else:
            return []
        

    def get_current_barfi_node_interface(self, node, origin = None, output = True):
        if node['type'] == 'Transformation':
            return ('Output 1' if output else 'Input 1')
        elif node['type'] in ['Modelling', 'Constant']:
            if output:
                return 'Output 1' if node['type'] == 'Modelling' else 'Output'
            else:
                raise ValueError(f"{node['type']} block does not have a input")
        elif node['type'] == 'Independent Variable':
            return 'Output' if output else 'Modelling Method'
        elif node['type'] == 'Dependent Variable':
            if output:
                raise ValueError("Dependent Variable can only have inputs")
            else:
                return 'Merge Input' if origin['type'] == 'Merge' else 'Modelling Method'
        elif node['type'] in ['Add', 'Merge', 'Subtract', 'Multiply', 'Division']:
            if output:
                return 'Output 1'
            else:
                # check for last input
                interfaces = node['interfaces']
                last_inp = sorted([row[0] for row in interfaces if 'Input' in row[1]], reverse=True)
                if len(last_inp) == 0:
                    return 'Input 1'
                else:
                    return f"Input { int(last_inp[0][6:]) + 1 }"
        else:
            raise NotImplementedError("Unsupported block")


    def extract_barfi_display(self):
        """
            Creates the barfi display schema based on the config
            - Generates an x, y <- coordinate, placements and scaling.
        """

        # extract the nodes
        node_id_mapper = {}
        counter = 1
        for key in self.config:
            nodeconfig = self.config[key]
            node = {
                'type': nodeconfig['type'],
                'id': f"node_{counter}",
                'name': key,
                'options': self.extract_barfi_display_node_options(nodeconfig),
                'state': {},
                'interfaces': [],
                'position': {
                    'x': 0, 'y': 0
                },
                'width': 200,
                'twoColumn': False,
                'customClasses': ''
            }
            node_id_mapper[key] = node
            counter += 10

        # extract the edges
        counter = 1
        edgelist = []
        for key in self.config:
            endnode = node_id_mapper[key]   # end node
            dependencies = self.barfi_input_blocks(self.config[key])
            for dep in dependencies:
                startnode = node_id_mapper[dep]  # start node

                end_node_input = self.get_current_barfi_node_interface(endnode, startnode, output=False)
                end_node_input_id = f"ni_{counter + 1}"
                node_id_mapper[key]['interfaces'].append(
                    [end_node_input, { "id": end_node_input_id, "value": None }]
                )
                
                start_node_output = self.get_current_barfi_node_interface(startnode)
                start_node_output_id = f"ni_{counter + 2}"
                node_id_mapper[dep]['interfaces'].append(
                    [start_node_output, { "id": start_node_output_id, "value": None }]
                )

                edge = {
                    'id': str(counter),
                    'from': start_node_output_id,
                    'to': end_node_input_id
                }
                edgelist.append(edge)
                counter += 1

        return {
            'nodes': [node_id_mapper[key] for key in node_id_mapper],
            'connections': edgelist,
            'panning': { 'x': 0, 'y': 0 },
            'scaling': 1
        }



def perform_transformations(expconf: ExperimentConfig, df, root = None):
    """
        Performs a topological sort on the computation graph,
        to understand in which order the transformations need to 
        be applied and what all transformations, and compute
        the transformations on the provided dataframe
    """
    root = root if root is not None else expconf.get_root()
    nodeconfig = expconf.get_nodeconfig(root)
    if nodeconfig['type'] == 'Independent Variable':
        return df[nodeconfig.get('column')]
    elif nodeconfig['type'] == 'Constant':
        return pd.Series(data = nodeconfig.get('value'), index=df.index)
    elif nodeconfig['type'] == 'Transformation':
        # first obtain the previous dependent nodes
        inp_block = nodeconfig.get('dependencies', [])[0]
        x = perform_transformations(expconf, df, inp_block)
        return apply_single_transformation(x, nodeconfig.get('method'), nodeconfig.get('parameter'))
    elif nodeconfig['type'] in ['Add', 'Subtract', 'Multiply', 'Division']:
        inp_blocks = nodeconfig.get('dependencies', [])
        collist = [perform_transformations(expconf, df, col) for col in inp_blocks]
        return apply_mixer_transformation(collist, root['type'])
    elif nodeconfig['type'] == 'Modelling':
        pass 
    elif nodeconfig['type'] == 'Merge':
        inp_blocks = nodeconfig.get('dependencies', [])
        collist = []
        for col in inp_blocks:
            x = perform_transformations(df, col)
            if isinstance(x, list):
                # for nested merge blocks
                collist += x
            else:
                collist.append(x)
            return collist
    elif root['type'] == 'Dependent Variable':
        inp_blocks = nodeconfig.get('dependencies', [])
        output = {
            'target': nodeconfig.get('column'),
            'features': [],
            'data': None
        }
        for key in inp_blocks:
            inpnodeconfig = expconf.get_nodeconfig(key)
            if inpnodeconfig['type'] == "Merge":
                collist = perform_transformations(expconf, df, key)
                for i in range(len(collist)):
                    feature_col = f"Feature {i+1}"
                    output['features'].append(feature_col)
                    df[feature_col] = collist[i]
                output['data'] = df
        return output
    else:
        raise NotImplementedError(f"Invalid node type {root['type']}")
    



def run_experiment(
        expconf: ExperimentConfig, 
        df: pd.DataFrame,
        train_dates: List[dt.datetime], 
        test_dates: List[dt.datetime],
        pred_dates: List[dt.datetime]
    ):
    # Step 1: Apply the transformations
    output = perform_transformations(expconf, df)

    # Step 2: Split into training, testing data
    train_df = train_test_split(output['data'], train_dates).dropna().reset_index(drop = True)
    test_df = train_test_split(output['data'], test_dates).dropna().reset_index(drop = True)
    features = output['features']
    target = output['target']
    X_train = train_df[features]
    y_train = train_df[target]
    X_test = test_df[features]
    y_test = test_df[target]

    # Step 3: Fit model and Perform testing
    method = output['Model'].get('method')
    mod = ChronoModel(model_name=method, parameters = output['Model'].get('parameter'))
    mod.fit_model(X_train, y_train)
    error_df = mod.predict_model(X_test, y_test)
    fit_results = mod.metrics

    # Step 4: Fit Model on train + test data
    new_train_df = self.train_test_split(output['data'], [train_dates[0], test_dates[1]]).dropna().reset_index(drop = True)
    mod.fit_model(new_train_df[features], new_train_df[target], update_metrics=False)
    



