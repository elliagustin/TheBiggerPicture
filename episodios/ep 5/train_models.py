# libraries
from ta.volatility import AverageTrueRange
import pandas as pd
import numpy as np
from itertools import product
# libraries
from sklearn.model_selection import train_test_split
from ta.trend import EMAIndicator, ADXIndicator, CCIIndicator, MACD, PSARIndicator
from ta.volatility import AverageTrueRange, BollingerBands
from ta.momentum import RSIIndicator, ROCIndicator, StochasticOscillator, williams_r
from ta.volume import OnBalanceVolumeIndicator, money_flow_index, ChaikinMoneyFlowIndicator
import os, joblib
from sklearn.metrics import precision_score, recall_score, f1_score
import pandas as pd
import matplotlib.pyplot as plt
from xgboost import XGBClassifier
import numpy as np


"""# **3 -Funciones**"""
def get_5m_hits(row, bid_5m, ask_5m):
    ep = row["ep"]
    sl = row["sl"]
    tp = row["tp"]

    bid_df = bid_5m.sort_index()
    ask_df = ask_5m.sort_index()

    # 1) First EP using ASK prices
    ep_mask = (ask_df["Low_ask"] <= ep) # & (ep <= ask_df["High_ask"])
    ep_hits = ask_df[ep_mask]

    if ep_hits.empty:
        return pd.DataFrame([{
            "ep_datetime": None,
            "sl_datetime": None,
            "tp_datetime": None,
            "max_after_ep": None,
            "min_after_ep": None
        }])

    ep_datetime = ep_hits.index[0]

    # 2) After EP, evaluate SL/TP using BID prices
    bid_after_ep = bid_df[bid_df.index >= ep_datetime]

    sl_mask = (bid_after_ep["Low_bid"] <= sl) & (sl <= bid_after_ep["High_bid"])
    tp_mask = (bid_after_ep["Low_bid"] <= tp) & (tp <= bid_after_ep["High_bid"])

    sl_hits = bid_after_ep[sl_mask]
    tp_hits = bid_after_ep[tp_mask]

    return pd.DataFrame([{
        "ep_datetime": ep_datetime,
        "sl_datetime": None if sl_hits.empty else sl_hits.index[0],
        "tp_datetime": None if tp_hits.empty else tp_hits.index[0],
        "max_after_ep": bid_after_ep["High_bid"].max(),
        "min_after_ep": bid_after_ep["Low_bid"].min()
    }])

def evaluate_5m_sequence(row, df_5m, hits):
    # definitions
    lot_size = 100000  # units per lote

    # result definition
    result = {
        "datetime": row.name,
        "Low_ask": row["Low_ask"],
        "High_ask": row["High_ask"],
        "ep": row["ep"],
        "ep_flag": row["ep_flag"],
        "High_bid": row["High_bid"],
        "Low_bid": row["Low_bid"],
        "sl": row["sl"],
        "tp": row["tp"],

        "open_datetime": pd.NaT,
        "close_status": "cancel trade", # Default value as a string
        "close_price": np.nan,
        "close_delta_points": pd.NA,
        "close_delta_time": pd.NA,
        "max_after_ep": np.nan,
        "min_after_ep": np.nan,
        "y":pd.NA # Initialize y to pd.NA, will be 0 or 1 if trade occurs
    }

    hit = hits.iloc[0]
    ep_datetime = hit["ep_datetime"]
    sl_datetime = hit["sl_datetime"]
    tp_datetime = hit["tp_datetime"]

    # 1. EP was never touched
    if pd.isna(ep_datetime):
        print(f'For {row.name} EP was never touched - IsThereFuture: {row.is_there_future} - DataConsistencyFlag:{row.DataConsistencyFlag}')
        result_df = pd.DataFrame([result]).astype(column_dtypes)
        return result_df

    result["open_datetime"] = ep_datetime
    result["max_after_ep"] = hit["max_after_ep"]
    result["min_after_ep"] = hit["min_after_ep"]

    sl_exists = not pd.isna(sl_datetime)
    tp_exists = not pd.isna(tp_datetime)

    if df_5m.empty:
      print(f'Error | df_5m is empty for {row.name} - IsThereFuture: {row.is_there_future} - DataConsistencyFlag:{row.DataConsistencyFlag}')
      result_df = pd.DataFrame([result]).astype(column_dtypes)
      return result_df


    # 2. EP touched, but neither SL nor TP touched
    if not sl_exists and not tp_exists:
        result["close_status"] = "Timeout"
        result["close_price"] = df_5m.iloc[-1]["Close_bid"]
        result["close_delta_time"] = round(((df_5m.index[-1] - ep_datetime).total_seconds() / 60), 0)
        result["close_delta_points"] = round(((result["close_price"] - result["ep"]) * lot_size), 0)
        if result["close_delta_points"] > 0:
            result["y"] = 1 # Set y to 1 for a TP outcome
        else:
            result["y"] = 0 # Set y to 0 for a non-TP outcome
        result_df = pd.DataFrame([result]).astype(column_dtypes)
        return result_df

    # 3. Only SL touched
    if sl_exists and not tp_exists:
        result["close_status"] = "SL"
        result["close_price"] = row["sl"]
        result["close_delta_time"] = round(((sl_datetime - ep_datetime).total_seconds() / 60), 0)
        result["close_delta_points"] = round(((result["close_price"] - result["ep"]) * lot_size), 0)
        result["y"] = 0 # Set y to 0 for a non-TP outcome
        result_df = pd.DataFrame([result]).astype(column_dtypes)
        return result_df

    # 4. Only TP touched
    if tp_exists and not sl_exists:
        result["close_status"] = "TP"
        result["close_price"] = row["tp"]
        result["close_delta_time"] = round(((tp_datetime - ep_datetime).total_seconds() / 60), 0)
        result["close_delta_points"] = round(((result["close_price"] - result["ep"]) * lot_size), 0)
        result["y"] = 1 # Set y to 1 for a TP outcome
        result_df = pd.DataFrame([result]).astype(column_dtypes)
        return result_df

    # 5. Both touched in the same 5m candle
    if sl_datetime == tp_datetime:
        result["close_status"] = "5m Conflict"
        result["close_delta_time"] = round(((sl_datetime - ep_datetime).total_seconds() / 60), 0)
        # No close_price or close_delta_points if conflict
        result["y"] = pd.NA # Set y to 0 for a non-TP outcome (conflict)
        result_df = pd.DataFrame([result]).astype(column_dtypes)
        return result_df

    # 6. Both touched, first one wins
    if sl_datetime < tp_datetime:
        result["close_status"] = "SL"
        result["close_price"] = row["sl"]
        result["close_delta_time"] = round(((sl_datetime - ep_datetime).total_seconds() / 60), 0)
        result["close_delta_points"] = round(((result["close_price"] - result["ep"]) * lot_size), 0)
        result["y"] = 0 # Set y to 0 for a non-TP outcome
        result_df = pd.DataFrame([result]).astype(column_dtypes)
        return result_df

    # If TP was touched first (implicit else: tp_datetime < sl_datetime)
    result["close_status"] = "TP"
    result["close_price"] = row["tp"]
    result["close_delta_time"] = round(((tp_datetime - ep_datetime).total_seconds() / 60), 0)
    result["close_delta_points"] = round(((result["close_price"] - result["ep"]) * lot_size), 0)
    result["y"] = 1 # Set y to 1 for a TP outcome
    result_df = pd.DataFrame([result]).astype(column_dtypes)
    return result_df

column_dtypes = {
    "datetime": "datetime64[ns]",
    "Low_ask": float,
    "High_ask": float,
    "ep": float,
    "ep_flag": "Int64", # Nullable integer
    "open_datetime": "datetime64[ns]", # Nullable datetime
    "Low_bid": float,
    "High_bid": float,
    "sl": float,
    "tp": float,
    "close_status": str, # Will be set to string
    "close_delta_points": "Int64", # Nullable integer
    "close_delta_time": "Int64", # Nullable integer
    "close_price": float,
    "max_after_ep": float,
    "min_after_ep": float,
    "y": "Int64" # Nullable integer
}

def get_combined_df(params):        
    atr_factor      = params["atr_factor"]
    entrance_factor = params["entrance_factor"]
    risk_factor     = params["risk_factor"]
    reward_factor   = params["reward_factor"]    

    
    target_df = source_ask.copy()
    
    # Rename columns to reflect 'bid' prices
    target_df.columns = [col.replace('_EURUSD', '_ask') for col in target_df.columns]
    
    # Only to be use as f(target)
    target_df['ATR14_50'] = (AverageTrueRange(high=target_df['High_ask'],low=target_df['Low_ask'],close=target_df['Close_ask'],window=14).average_true_range()*atr_factor).round(5)
    
    # print target len before dropping
    # print(f'target_df len: {len(target_df)}')
    
    # borre rows vacias luego de calcular ATR
    target_df = target_df.iloc[14-1:]
    
    # ep
    target_df['entry_offset'] = (target_df['ATR14_50'] * entrance_factor).round(5)
    target_df['ep'] = (target_df['Open_ask'].shift(-1) - target_df['entry_offset']).round(5)
    
    # adding ep_flag
    target_df['ep_flag'] = ((target_df['Low_ask'].shift(-1) <= target_df['ep']) & ( target_df['ep'] <= target_df['High_ask'].shift(-1) )).astype(int)
    target_df.loc[target_df.index[-1], "ep_flag"] = -1
    
    # updating the flag
    target_df["DataConsistencyFlag"] = np.where((target_df["DataConsistencyFlag"] == "5m consistent") & (target_df["DataConsistencyFlag"].shift(-1) == "5m consistent"),"5m consistent","inconsistent")
    
    # sl and TP
    target_df['sl'] = target_df['ep'] - target_df['ATR14_50'] * risk_factor
    target_df['tp'] = target_df['ep'] + target_df['ATR14_50'] * reward_factor
    
    # Orden
    target_df = target_df.drop(['Volume_ask','FilledMethod','WasMissing','ATR14_50','Close_ask'], axis=1)
    target_df.rename(columns={'DataConsistencyFlag': 'DataConsistencyFlag_ask'}, inplace=True)
    column_order = ['Open_ask','entry_offset','ep',  'Low_ask','High_ask', 'ep_flag', 'sl', 'tp', 'DataConsistencyFlag_ask']
    target_df = target_df[column_order]
    
    # sort and show
    target_df.sort_index(inplace=True)
    
    
    
    # traemos los bid prices
    bid_df = source_bid.copy()
    
    # remove some columns
    bid_df = bid_df.drop(['Volume_EURUSD','Open_EURUSD','Close_EURUSD','FilledMethod','WasMissing'], axis=1)
    
    # Rename columns to reflect 'bid' prices
    bid_df.columns = [col.replace('_EURUSD', '_bid') for col in bid_df.columns]
    bid_df.rename(columns={'DataConsistencyFlag': 'DataConsistencyFlag_bid'}, inplace=True)
    
    # print
    bid_df.head(2)
    
    combined_df = target_df.merge(bid_df, left_index=True, right_index=True, how='left', suffixes=('', '_bid'))
    
    # Calculate 'is_there_future' by checking if the next hour's timestamp exists in the index
    index_plus_one_hour = combined_df.index + pd.Timedelta(hours=1)
    combined_df['is_there_future'] = index_plus_one_hour.isin(combined_df.index).astype(int)
    combined_df.tail(2)
    
    # prints
    # print(f"Rows in target_df before the merge {len(target_df)}")
    # print(f"Rows in bid_df before the merge {len(bid_df)}")
    # print(f"Rows in combined_df after the merge {len(combined_df)}")
    
    # Condition 1: If entry point (ep_flag) was not reached
    combined_df.loc[combined_df['ep_flag'] == 0, 'ep_flag_desc'] = "EP_NotHit"
    combined_df.loc[combined_df['ep_flag'] == 1, 'ep_flag_desc'] = "Check_5m"
    
    # Unique consistency
    combined_df['DataConsistencyFlag'] = np.where(
        (combined_df['DataConsistencyFlag_bid'] == '5m consistent') &
        (combined_df['DataConsistencyFlag_ask'] == '5m consistent'),
        '5m consistent',
        'inconsistent'
    )
    
    # Drop individual DataConsistencyFlag columns
    combined_df.drop(columns=['DataConsistencyFlag_bid', 'DataConsistencyFlag_ask'], inplace=True)
    combined_df.head(2)

    return combined_df


"""# **2 - Parametros**"""
# # target params
# atr_factor      = 0.5       # ATR14_alterado = ATR14 * atr_factor
# entrance_factor = 0.9       # ep = open_price(+1h) - ATR14_alterado * entrance_factor 
# risk_factor     = 1         # sl = ep - ATR14_50 * risk_factor
# reward_factor   = 1         # tp = ep + ATR14_50 * reward_factor

grid = {
    "lookahead_hours": [5],
    "atr_factor":      [0.3, 0.4, 0.5],
    "entrance_factor": [0.3, 0.4, 0.5, 1.0],
    "risk_factor":     [1],
    "reward_factor":   [1, 1.1, 1.2],
}

params_grid = pd.DataFrame(
    product(*grid.values()),
    columns=grid.keys()
)

params_grid.head()






"""The `column_dtypes` dictionary ensures that all result dataframes have a consistent schema, resolving the `FutureWarning` during concatenation. Now we will modify the `evaluate_5m_sequence` function and the main loop to use these types.
# **4 - Datasets**
"""
source_ask = pd.read_csv('Source_EURUSD_Ask.csv', index_col='Datetime', parse_dates=True, low_memory=False).drop('is_missing', axis=1)
source_bid = pd.read_csv('Source_EURUSD_Bid.csv', index_col='Datetime', parse_dates=True, low_memory=False).drop('is_missing', axis=1)
source_ask5 = pd.read_csv('Source_EURUSD_Ask_5m.csv', index_col='Datetime', parse_dates=True, low_memory=False).drop('is_missing', axis=1)
source_bid5 = pd.read_csv('Source_EURUSD_Bid_5m.csv', index_col='Datetime', parse_dates=True, low_memory=False).drop('is_missing', axis=1)

source_ask.index = pd.to_datetime(source_ask.index)
source_bid.index = pd.to_datetime(source_bid.index)
source_ask5.index = pd.to_datetime(source_ask5.index)
source_bid5.index = pd.to_datetime(source_bid5.index)



"""# **9 - Magic**"""
modeling_results = []
for _, params in params_grid.iterrows(): 
    print(f'Calculating modeling_results for: {params}\n')      
    lookahead_hours = params["lookahead_hours"]    
    combined_df = get_combined_df(params)
    results = []    
    combined_df_reduced = combined_df.copy() # combined_df_reduced = combined_df['2025-08-01 06:00:00':'2025-08-01 08:00:00'].copy()
    
    for idx, row in combined_df_reduced.iterrows():
        # print(f"Processing row: {idx}")
        if row["is_there_future"] == 0:
            continue
    
        result = {
            "datetime": row.name,
            "Low_ask": row["Low_ask"],
            "High_ask": row["High_ask"],
            "ep": row["ep"],
            "ep_flag": row["ep_flag"],
            "High_bid": row["High_bid"],
            "Low_bid": row["Low_bid"],
            "sl": row["sl"],
            "tp": row["tp"],
    
            "open_datetime": pd.NaT, # Use pd.NaT for nullable datetime
            "close_status": None, # Will be set to string
            "close_price": np.nan, # Use np.nan for nullable float
            "close_delta_time": pd.NA, # Use pd.NA for nullable integer
            "close_delta_points": pd.NA, # Use pd.NA for nullable integer
            "max_after_ep": np.nan, # Use np.nan for nullable float
            "min_after_ep": np.nan, # Use np.nan for nullable float
            "y": pd.NA # Use pd.NA for nullable integer
        }
    
        H1_state = row["ep_flag_desc"]
    
        if H1_state == "EP_NotHit":
            result["close_status"] = "EP Not Hit"
            # Ensure the DataFrame is created with correct dtypes
            result_df = pd.DataFrame([result]).astype(column_dtypes)
    
        elif H1_state in ["Check_5m"]:
            dt_from = pd.to_datetime(row.name) + pd.Timedelta(hours=1)
            dt_to   = dt_from + pd.Timedelta(hours=lookahead_hours + 1)
    
            bid_5m_reduced = (
                source_bid5.loc[
                    (source_bid5.index >= dt_from) &
                    (source_bid5.index < dt_to),
                    ['High_EURUSD', 'Low_EURUSD','Close_EURUSD']
                ]
                .rename(columns={
                    'High_EURUSD': 'High_bid',
                    'Low_EURUSD': 'Low_bid',
                    'Close_EURUSD': 'Close_bid'
                })
            )
            if bid_5m_reduced.empty:
                print(f'For {row.name} bid_5m is empty from {dt_from} to {dt_to} - IsThereFuture: {row.is_there_future} - DataConsistencyFlag:{row.DataConsistencyFlag}')
    
            ask_5m_reduced = (
                source_ask5.loc[
                    (source_ask5.index >= dt_from) &
                    (source_ask5.index < dt_to),
                    ['High_EURUSD', 'Low_EURUSD']
                ]
                .rename(columns={
                    'High_EURUSD': 'High_ask',
                    'Low_EURUSD': 'Low_ask'
                })
            )
            if ask_5m_reduced.empty:
                print(f'For {row.name} bid_5m is empty from {dt_from} to {dt_to} - IsThereFuture: {row.is_there_future} - DataConsistencyFlag:{row.DataConsistencyFlag}')
    
            hits = get_5m_hits(row, bid_5m_reduced, ask_5m_reduced)
            result_df = evaluate_5m_sequence(row, bid_5m_reduced, hits)
        else:
            print("ERROR")
            result["close_status"] = "ERROR"
            # Ensure the DataFrame is created with correct dtypes
            result_df = pd.DataFrame([result]).astype(column_dtypes)
    
        # if the specific result_df is empty
        if result_df.empty:
            print(
                f"For {row.name} result_df coming from evaluate_5m_sequence() is empty - IsThereFuture: {row.is_there_future} - DataConsistencyFlag: {row.DataConsistencyFlag}"
            )
        else:
            results.append(result_df)
        # for end
        
    # concat all results
    trade_results_df = pd.concat(results, ignore_index=True)
    
    # completing modeling_results
    counts = trade_results_df["y"].value_counts(dropna=False)
    valid_y = trade_results_df[
        (trade_results_df["y"] == 1) | (trade_results_df["y"] == 0)
    ]
    pct_1 = round(valid_y["y"].mean() * 100,1)

    modeling_results.append({"params": params,
                            "n_rows": len(trade_results_df),
                             "n_na" : counts.get(pd.NA, 0),
                             "n_0and1"  : counts.get(0, 0) + counts.get(1, 0),
                             "n_0"  : counts.get(0, 0),
                             "n_1"  : counts.get(1, 0),
                             "pct_1": pct_1
                             })


# modeling_results_df = pd.DataFrame(modeling_results)
# modeling_results_df.to_csv('modeling_results_df.csv')
# modeling_results_expanded_df = modeling_results_df.drop(columns="params").join(
#     modeling_results_df["params"].apply(pd.Series)
# )

######### Only converting to modeling_EURUSD_ask.csv the selected key comb
"""# **10 - Modeling Dataset**"""


# preparing trade_results_df
trade_results_df.index = pd.to_datetime(trade_results_df['datetime'])
trade_results_df = trade_results_df.drop(['datetime'], axis=1)
trade_results_df = trade_results_df.rename_axis('Datetime')

# merging to get y
modeling_ask = source_ask.copy()
modeling_ask = modeling_ask.merge(trade_results_df[['y']], left_index=True, right_index=True, how="inner")
modeling_ask = modeling_ask[modeling_ask['y'].notna()] # remove nan (no active trade)
modeling_ask['y'] = modeling_ask['y'].astype('Int64')

# cleaning inconsist data
modeling_ask = modeling_ask[modeling_ask['DataConsistencyFlag'] == '5m consistent']

# Make a copy
X = modeling_ask.copy()

# Date related features
X['Hour'] = X.index.hour
X['Day_of_Week'] = X.index.dayofweek

# Ema Features
X['EMA_9'] = EMAIndicator(close=X['Close_EURUSD'], window=9).ema_indicator()
X['EMA_20'] = EMAIndicator(close=X['Close_EURUSD'], window=20).ema_indicator()
X['EMA_50'] = EMAIndicator(close=X['Close_EURUSD'], window=50).ema_indicator()
X['EMA_100'] = EMAIndicator(close=X['Close_EURUSD'], window=100).ema_indicator()
X['EMA_200'] = EMAIndicator(close=X['Close_EURUSD'], window=200).ema_indicator()
X['MFI_14'] = money_flow_index(high=X['High_EURUSD'], low=X['Low_EURUSD'], close=X['Close_EURUSD'], volume=X['Volume_EURUSD'], window=14)
X['CMF'] = ChaikinMoneyFlowIndicator(high=X['High_EURUSD'], low=X['Low_EURUSD'], close=X['Close_EURUSD'], volume=X['Volume_EURUSD'], window=20).chaikin_money_flow()

# Remove rows with null values
X_ready = X.iloc[200-1:].copy()

#check
X_ready.head(2)




np.random.seed(27)
models = [
   (XGBClassifier(n_estimators=500,
                  max_depth=6,
                  learning_rate=0.05,
                  random_state=0), "XGB (500 trees)")
]


# thresholds = [0.55, 0.575, 0.6, 0.625, 0.65, 0.675, 0.7, 0.725, 0.75, 0.775, 0.8]
thresholds = np.arange(0.1, 0.91, 0.025).round(3).tolist()

results = [] # Clear the results list before running the training loop
for model, model_name in models:
    print(f'Training {model_name}')

    X_ready = X_ready.sort_index()
    # Drop 'y' and the problematic object-type columns
    df = X_ready.drop(columns=['y', 'FilledMethod', 'DataConsistencyFlag'])
    y = X_ready['y']

    # Split (time-based)
    x_train, x_val, y_train, y_val = train_test_split(df, y, test_size=0.2, shuffle=False)

    # Train
    model.fit(x_train, y_train)

    # Probabilities
    y_prob_train = model.predict_proba(x_train)[:, 1]
    y_prob_val   = model.predict_proba(x_val)[:, 1]

    for threshold in thresholds:
        # Thresholded predictions
        y_pred_train = (y_prob_train > threshold).astype(int)
        y_pred_val   = (y_prob_val > threshold).astype(int)
        n_trades_val = y_pred_val.sum()

        # Metrics
        row = {
            "model": model_name,
            "threshold":threshold,
            "n_trades_val":n_trades_val,

            # Class 1 focus (important)
            "val_precision_1": precision_score(y_val, y_pred_val, pos_label=1, zero_division=0),
            "val_recall_1": recall_score(y_val, y_pred_val, pos_label=1),
            "val_f1_1": f1_score(y_val, y_pred_val, pos_label=1)
        }

        results.append(row)












