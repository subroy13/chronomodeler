
config = {
    "Dependent Variable-1": {
        "type": "Dependent Variable", 
        "dependencies": ["Modelling-1", "Merge-1"], 
        "column": "Revenue"
    }, 
    "Independent Variable-1": {
        "type": "Independent Variable", 
        "dependencies": [], 
        "column": "TimeIndex"
    }, 
    "Merge-1": {"type": "Merge", "dependencies": ["Independent Variable-1", "Transformation-1"]}, "Modelling-1": {"type": "Modelling", "dependencies": [], "method": "OLS", "parameter": []}, "Transformation-1": {"type": "Transformation", "dependencies": ["Independent Variable-1"], "method": "Power", "parameter": 3}}
