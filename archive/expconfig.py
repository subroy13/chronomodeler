from typing import Dict, List, Tuple
from barfi import Block


class ExperimentConfig:

    @staticmethod
    def get_input_blocks(schemapart: Dict) -> List[str]:
        inputs = []
        for _, item in schemapart['interfaces'].items():
            if item.get('type') == 'intput':
                input_key = list(item['from'].keys())[0]
                inputs.append(input_key)
        return inputs


    @staticmethod
    def get_experiment_config(barfi_schema: Dict):
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
            else:
                block_params = {}
            item = {
                'type': val['type'],
                'dependencies': ExperimentConfig.get_input_blocks(val)
            } | block_params
            output[key] = item
        return output
    
    
    @staticmethod
    def get_dependent_variable_from_config(conf: Dict):
        for key in conf:
            if conf[key]['type'] == 'Dependent Variable':
                return conf[key]['column']
        
        