import sys, os
sys.path.append(os.path.join(os.getcwd(), 'helpers'))
from strategy import Strategy
from backtester import Model_Backtester
from itertools import product
import mssql as ms
from datetime import timedelta
import pandas as pd
import numpy as np
import time
from helpers.audit import execute_with_audit
        
class SmoothMind_GridRunner:
    def __init__(self, param_grid, currency_name, from_date = None, to_date = None, model_only = True ):
        self.param_grid = param_grid
        self.currency_name = currency_name
        self.from_date = from_date
        self.to_date = to_date
        self.model_only = model_only  

    def run(self): 
        start_time = time.time()
        weeks_date_list = self.calculate_week_dates()
        
        if not weeks_date_list:
            return
        
        results = []
        
        #new
        _, latest_rsi_dt = ms.get_latest_dates(database = 'tbpStaging', schema_name='staging', table_name='RSI_1H')

        for from_week_start, to_week_start in weeks_date_list:
           
            rsi_data = ms.get_RSI_data_from_to(
                currency= self.currency_name, from_date = from_week_start, to_date= to_week_start)       
            rsi_data.rename(columns={self.currency_name: "rsi"}, inplace=True)
                        
                   
            for direction in ['long', 'short']: #                         
                for params in self._expand_grid(self.param_grid):
                    print(f'{self.currency_name} | From {from_week_start} to {to_week_start} | {direction.upper()} ')
                    # print(f"Params: {params}")
                    strategy = Strategy(**params)
                    tester = Model_Backtester(rsi_data, strategy, direction, self.model_only, self.currency_name)
                    df = tester.run()
                    # df = execute_with_audit(
                    #         process_name="populate_actuals_and_predictions",
                    #         func=lambda: tester.run(),
                    #         log_environment="dwh",
                    #         subprocess_name=f"{self.currency_name}_{direction}"
                    #     )
                    
                    if df is None or getattr(df, "empty", True):
                        # si no hay data, no intentes mask ni append
                        continue
                    
                    #new
                    safe_cutoff_dt = latest_rsi_dt - pd.Timedelta(hours=params["lookahead_period"])
                    mask_past = df.index <= safe_cutoff_dt
                    df.loc[mask_past & df["actual"].isna(), "predicted"] = np.nan

                    results.append(df)
                    
        
        final_df = pd.concat(results).sort_index()
        end_time = time.time()
        print(f"{self.currency_name} | Execution time: {end_time - start_time:.2f} seconds")        
        print('------')
        
        
        
        return final_df
    
    def _expand_grid(self, grid):
        keys, values = zip(*grid.items())
        return [dict(zip(keys, v)) for v in product(*values)]

    def calculate_week_dates(self):
        """
        Returns a list of (week_start, week_end) as STRINGS:
        'YYYY-MM-DD HH:MM:SS'
        """
           
        dates_grid = []      
        
        # --- align to Sunday ---
        days_to_sunday = (self.from_date.weekday() + 1) % 7
        week_start = self.from_date - timedelta(days=days_to_sunday)
    
        # --- generate weekly windows ---
        while week_start <= self.to_date:
            # inicio exacto de semana (domingo 00:00:00.000)
            week_start = week_start.replace(hour=0, minute=0, second=0, microsecond=0)
            
            # fin exacto de semana (sábado 23:59:59.999)
            week_end = week_start + timedelta(days=6, hours=23, minutes=59, seconds=59)
            
            start_str = week_start.strftime("%Y-%m-%d %H:%M:%S") #+ ".000"
            end_str   = week_end.strftime("%Y-%m-%d %H:%M:%S") #+ ".999"

    
            dates_grid.append((start_str, end_str))
            week_start += timedelta(weeks=1)
    
        return dates_grid


####################################################################### test






# param_grid = {
#     "smooth_factor":[2],
#     "lookahead_period":[5],
#     "target_move":[10],
#     "entry_pullback":[10]    
# }

# runner = SmoothMind_GridRunner(param_grid = param_grid,                  
#                     currency_name = 'AUD', 
#                     from_date = '2025-11-21 11:00:00.000', 
#                     to_date = '2025-11-25 11:00:00.000',           
#                     model_only=True)

# outcome = runner.run()


# dates_grid = runner.calculate_week_dates()


# ms.get_RSI_data_from_to(currency_name, from_date = from_week_start, to_date= to_week_start) 


# rsi_data = runner.get_RSI()
# strategy = Strategy(smooth_factor=2,lookahead_period=5,target_move=10,entry_pullback=10)

# tester = Backtester(rsi_data, strategy, 'long', True)
# df = tester.run()

















