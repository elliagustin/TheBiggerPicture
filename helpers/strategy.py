import joblib
import mssql as ms
import pandas as pd
import os
from metrics import Metrics


class Strategy:
    def __init__(self, smooth_factor, lookahead_period, target_move, entry_pullback):        
        self.target_move = target_move
        self.entry_pullback = entry_pullback
        self.lookahead_period = lookahead_period
        self.smooth_factor = smooth_factor  
    
    def run(self, data, direction, currency, compute_metrics=False):
        # data = self.generate_actuals(data, direction)
        data = self.generate_predictions(data, direction, currency)
        data = self.generate_actuals(data, direction)

        if compute_metrics:
            print('Class Strategy. Run(...compute_metrics=True)') 
            metrics = Metrics(data).compute()
            print(metrics)    
        return data
        
    def generate_actuals(self, data, direction):
        data = data.copy()
        L = self.lookahead_period
        if direction == 'long':
            # MAX of the NEXT L smooth values; require full window → last L rows = NaN
            data['modelKey'] = 1
            
            data["MAX_or_MIN"] = (
                data["smooth"]
                .shift(-1)                                  # start from t+1
                .rolling(window=L, min_periods=L)
                .max()
                .shift(-L + 1)                              # align back to time t
            )    
        
            data["actual"] = (
                data["MAX_or_MIN"].notna() & (data["smooth"] < data["MAX_or_MIN"])
                ).astype("boolean")
            

            
            # data = data[data['MAX_or_MIN'].notna()]

        elif direction == 'short':
            # MAX of the NEXT L smooth values; require full window → last L rows = NaN
            data['modelKey'] = 2
            
            data["MAX_or_MIN"] = (
                data["smooth"]
                .shift(-1)                                  # start from t+1
                .rolling(window=L, min_periods=L)
                .min()
                .shift(-L + 1)                              # align back to time t
            )    

            data["actual"] = (
                data["MAX_or_MIN"].notna() & (data["smooth"] > data["MAX_or_MIN"])
                ).astype("boolean")



        data["label_available"] = data["MAX_or_MIN"].notna()
        # data.loc[~data["label_available"], "actual"] = np.nan
        data.loc[~data["label_available"], "actual"] = pd.NA
            
        return data
    
    
    
    def generate_predictions(self, data, direction, currency, model_name="CatBoost (depth=4)"):    
        
        # 1 Get X
        X = ms.get_table_from_sql('RSI_1H', from_date = data.index.min(), to_date = data.index.max())
        X['Hour'] = X.index.hour * 10
        X['Day_of_Week'] = X.index.dayofweek * 10
        _Vol = ms.get_all_table(database = 'tbpStaging',schema = '[mid]', table='[Vw_Vol]').sort_index() / 100
        _Vol = _Vol.fillna(_Vol.mean())
        X = X.merge(_Vol, left_index=True, right_index=True)
    
        # # 2 Keep only the required time window
        # X = X.loc[data.index.min():data.index.max()]
    
        # 3 Load the correct trained model
        model_path = f"models/{direction}/{model_name}_{currency}.pkl"
        if not os.path.exists(model_path):
            raise FileNotFoundError(f"Model not found: {model_path}")
        model = joblib.load(model_path)
    
        # 4 Predict (class or probability)
        # X["y"] = 0  # dummy filler
        y_pred_proba = model.predict_proba(X)[:, 1]
        y_pred = y_pred_proba # (y_pred_proba >= 0.8).astype(int)
    
        # 5 Add prediction column to your RSI/smooth df
        data = data.copy()
        data["predicted"] = pd.Series(y_pred, index=X.index).reindex(data.index)
        
        return data


   










    