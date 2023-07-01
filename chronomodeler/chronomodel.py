import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression, HuberRegressor
from sklearn.tree import DecisionTreeRegressor
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.neural_network import MLPRegressor
from sklearn.metrics import mean_squared_error, mean_absolute_error

class ChronoModel:

    MODEL_LISTS = [
        "OLS",
        "WLS",
        "Robust Regression",
        "Decision Tree",
        "Random Forest",
        "Gradient Boost",
        "Feedforward NN"
    ]
    metrics = {}

    def __init__(self, model_name: str, parameters = None) -> None:
        assert model_name in self.MODEL_LISTS, "Invalid model name"
        self.model_name = model_name
        self.parameters = parameters

    def fit_model(self, features, target, update_metrics: bool = True):
        if self.model_name == 'OLS':
            self.model = LinearRegression(fit_intercept=True)
        elif self.model_name == 'WLS':
            self.model = LinearRegression(fit_intercept=True)
        elif self.model_name == 'Robust Regression':
            self.model = HuberRegressor()
        elif self.model_name == 'Decision Tree':
            self.model = DecisionTreeRegressor()
        elif self.model_name == 'Random Forest':
            self.model = RandomForestRegressor()
        elif self.model_name == 'Gradient Boost':
            self.model = GradientBoostingRegressor()
        elif self.model_name == 'Feedforward NN':
            self.model = MLPRegressor()
        else:
            raise NotImplementedError()
        if self.parameters == 'ASC':
            self.model.fit(features, target, np.arange(1, target.shape[0] + 1))
        elif self.parameters == 'DESC':
            self.model.fit(features, target, np.arange(1, target.shape[0] + 1)[::-1])
        else:
            self.model.fit(features, target)
        if update_metrics:
            self.metrics['R^2 (Train)'] = self.model.score(features, target)


    def predict_model(self, new_features, targets = None):
        y_pred = self.model.predict(new_features)
        if targets is None:
            return pd.DataFrame({
                'Prediction': np.round(y_pred, 2)
            })
        else:
            self.metrics['R^2 (Test)'] = self.model.score(new_features, targets)
            self.metrics['RMSE'] = np.round(mean_squared_error(targets, y_pred)**0.5, 2)
            self.metrics['MAE'] = np.round(mean_absolute_error(targets, y_pred), 2)

            absolute_error = (targets - y_pred)

            # Calculate percentage error (SMAPE)
            percentage_error  = (2 * absolute_error / (y_pred + targets)) * 100
            self.metrics['SMAPE'] = np.round((np.abs(percentage_error)).mean(), 2)

            df = pd.DataFrame({ 'Prediction': np.round(y_pred, 2), 'True': np.round(targets, 2) })
            df['Error'] = df['True'] - df['Prediction']
            df['SMAPE'] = np.round(percentage_error, 2)
            return df
        
