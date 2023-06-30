
config = {
  "Dependent Variable-1": {
    "type": "Dependent Variable",
    "dependencies": [
      "Modelling-1",
      "Merge-1"
    ],
    "column": "COGS (Finance team)"
  },
  "Independent Variable-1": {
    "type": "Independent Variable",
    "dependencies": [],
    "column": "TimeIndex"
  },
  "Modelling-1": {
    "type": "Modelling",
    "dependencies": [],
    "method": "OLS",
    "parameter": []
  },
  "Merge-1": {
    "type": "Merge",
    "dependencies": [
      "Independent Variable-1"
    ]
  }
}

