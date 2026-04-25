# from validator import Validator 
import pandas as pd

# data is from one unique currency

class Model_Backtester:
    def __init__(self, data, strategy, direction, model_only, currency):
        self.data = data
        self.strategy = strategy
        self.direction = direction
        self.model_only = model_only
        self.currency = currency
        
    def run(self):
        # get smooth rsi
        if self.data.shape[0] < self.strategy.smooth_factor:
            print(f'Error | RSI table has {self.data.shape[0]} rows. Smooth operation factor {self.strategy.smooth_factor} is not possible')
            empty = pd.DataFrame(columns=["rsi", "smooth", "predicted", "actual"])
            empty.index = pd.to_datetime(empty.index)
            empty.index.name = "Datetime"
            return empty
        
        # get the smooth data
        smooth_rsi = self._smooth_data(self.data.copy())       
        
        # get results from strategy
        results = self.strategy.run(smooth_rsi, self.direction, self.currency)      
        return  results    

    def _smooth_data(self, data):
        data = data.copy()
        data = data.sort_values(by="Datetime") 
        data['smooth'] = data['rsi'].rolling(self.strategy.smooth_factor, min_periods=1).mean()
        blank_rows = self.strategy.smooth_factor - 1
        data = data[blank_rows:]
        return data
    
    
    
    

# class Strategy_Backtester:
#     def __init__(self, data, strategy, direction, model_only):
#         self.data = data
#         self.strategy = strategy
#         self.direction = direction
#         # self.validator = Validator() # for when we need 5 tf candles
#         self.model_only = model_only
        
#     def backtest_strategy(self, model_df):
#         df = model_df.copy()
       
#         for i in range(len(df) - self.strategy.lookahead_period):
#             if df.iloc[i]["signal"] == 1:  # only trade on signal = 1
#                 entry_price = df.iloc[i]["smooth"]
#                 tp = entry_price + self.strategy.target_move
#                 sl = entry_price - self.strategy.entry_pullback
#                 # placeholder outcome logic
#                 df.iloc[i, df.columns.get_loc("actual")] = 1  # assume win for now
        
#         return df,tp,sl
    
    
















