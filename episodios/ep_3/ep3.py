from ta.volatility import AverageTrueRange
import pandas as pd
import numpy as np
import itertools
import time
import random, os
import math

SEED = 27
random.seed(SEED)
np.random.seed(SEED)
os.environ["PYTHONHASHSEED"] = str(SEED)
pair_name = 'EURUSD'


# %% ---------- params ----------
"""Parametros"""
strategy_grid = {
    "lookahead_hours": [3,5 , 7],
    "atr_period": [7, 14, 21],
    "entrance_factor": [0.3,0.4,0.5,0.6,0.7],
    "risk_factor": [0.75,1],
    "reward_factor": [1,1.2],
}

# strategy_grid = {
#     "lookahead_hours": [3,5],
#     "atr_period": [5], #[3,5,7,9],
#     "entrance_factor": [0.2], #[0.2,0.3,0.4,0.5,0.6],
#     "risk_factor": [1],
#     "reward_factor": [1],
# }

# strategy_grid = {
#     "lookahead_hours": [3,5,7,9],
#     "atr_period": [3,5,7,9],
#     "entrance_factor": [0.2], #[0.2,0.3,0.4,0.5,0.6],
#     "risk_factor": [1],
#     "reward_factor": [1],
# }


total_combinations = math.prod(len(v) for v in strategy_grid.values())

# %% ---------- get_source_datasets ----------
def get_source_datasets(pair_name):
    # fix name
    pair_name = pair_name.replace("_", "")

    # 2. Combine the folder path with the file names
    source_ask = pd.read_csv(f'Source_{pair_name}_Ask.csv', index_col='Datetime', parse_dates=True, low_memory=False).drop('is_missing', axis=1)
    source_bid = pd.read_csv(f'Source_{pair_name}_Bid.csv', index_col='Datetime', parse_dates=True, low_memory=False).drop('is_missing', axis=1)
    source_ask5 = pd.read_csv(f'Source_{pair_name}_Ask5.csv', index_col='Datetime', parse_dates=True, low_memory=False).drop('is_missing', axis=1)
    source_bid5 = pd.read_csv(f'Source_{pair_name}_Bid5.csv', index_col='Datetime', parse_dates=True, low_memory=False).drop('is_missing', axis=1)

    # Keep your datetime conversions below as you had them
    source_ask.index = pd.to_datetime(source_ask.index)
    source_bid.index = pd.to_datetime(source_bid.index)
    source_ask5.index = pd.to_datetime(source_ask5.index)
    source_bid5.index = pd.to_datetime(source_bid5.index)

    # add columns
    source_ask[['week', 'yyyyww']] = get_week_fields(source_ask.index)
    source_bid[['week', 'yyyyww']] = get_week_fields(source_bid.index)
    source_ask5[['week', 'yyyyww']] = get_week_fields(source_ask5.index)
    source_bid5[['week', 'yyyyww']] = get_week_fields(source_bid5.index)

    # remove rows of incomplete weeks
    source_ask = source_ask.groupby("yyyyww").filter(lambda x: len(x) == 117)
    source_bid = source_bid.groupby("yyyyww").filter(lambda x: len(x) == 117)
    source_ask5 = source_ask5.groupby("yyyyww").filter(lambda x: len(x) == 1404)
    source_bid5 = source_bid5.groupby("yyyyww").filter(lambda x: len(x) == 1404)
    return source_ask, source_bid, source_ask5, source_bid5

# %% ---------- generar_strategy_grid ----------
def generar_strategy_grid(strategy_grid):
  """Genera un DataFrame con todas las combinaciones posibles

  a partir de un diccionario de parámetros estilo grid.
  """
  keys = strategy_grid.keys()
  values = strategy_grid.values()
  return pd.DataFrame(list(itertools.product(*values)), columns=keys)

# %% ---------- Definitions ----------
Definitions = {
    "n_rows": "Total trades evaluated (includes EP never touched)",
    "n_na": "Trades with no valid outcome (EP not touched, or SL/TP hit in same 5m candle)",
    "n_0and1": "Trades with a valid outcome (SL, TP, or Timeout)",
    "n_0": "Losing trades (y=0)",
    "n_1": "Winning trades (y=1)",

    "pct_1": "Win rate (%) over valid trades",
    "total_entries": "Trades where EP was touched (includes 5m Conflict)",
    "entries_per_week": "total_entries / number of weeks in the dataset",
    "avg_pct_pm": "Average monthly win rate (%) over valid trades",

    "std_pct_pm": "Standard deviation of monthly win rate (%) — stability of pct_1 over time",
    "avg_sl_points": "Average distance EP to SL in points (valid trades)",

    "avg_tp_points": "Average distance EP to TP in points (valid trades)",
    "avg_spread_points": "Average spread (High_ask - High_bid) in points (valid trades)",
    "n_SL": "Trades closed by stop loss",

    "n_TP": "Trades closed by take profit",
    "n_Timeout": "Trades closed by lookahead window ending (no SL/TP hit)",
    "n_conflict": "Trades where SL and TP were hit in the same 5m candle (ambiguous)",
    "n_cancel": "Trades where EP was never touched",
    "total_points": "Net points gained/lost across all valid trades",
    "avg_points": "Average points per trade (expectancy)",
    "std_points": "Standard deviation of points per trade (volatility of results)",
    "avg_win": "Average points on winning trades only",
    "avg_loss": "Average points on losing trades only",
    "profit_factor": "Sum of winning points / abs(sum of losing points). >1 = net profitable",
    "sharpe_like": "avg_points / std_points — return per unit of volatility (unannualized)",
    "max_drawdown": "Worst peak-to-trough drop in cumulative points, in time order",
    "avg_close_time_min": "Average minutes until trade closes (SL/TP/Timeout)",
    "median_close_time_min": "Median minutes until trade closes",
    "avg_MFE_points": "Avg max favorable excursion — how far price moved in your favor before close",
    "avg_MAE_points": "Avg max adverse excursion — how far price moved against you before close",
}

# %% ---------- column_dtypes ----------
column_dtypes = {
    "datetime": "datetime64[ns]",
    "Low_ask": float,
    "High_ask": float,
    "ep": float,
    # "ep_flag": "Int64", # Nullable integer
    "open_datetime": "datetime64[ns]", # Nullable datetime
    "open_delta_points": "Int64", # Nullable integer
    "open_delta_time": "Int64", # Nullable integer    
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

# %% ---------- build_hourly_candidates ----------
def build_hourly_candidates(params, source_ask, source_bid):
    # params
    atr_period      = int(params["atr_period"])
    entrance_factor = params["entrance_factor"]
    risk_factor     = params["risk_factor"]
    reward_factor   = params["reward_factor"]

    # small data prep
    target_df = source_ask.copy()
    target_df.columns = [col.replace('_EURUSD', '_ask') for col in target_df.columns]

    # add ATR
    target_df['ATR'] = (
        target_df
        .groupby('yyyyww', group_keys=False)
        .apply(
            lambda x: AverageTrueRange(
                high=x['High_ask'],
                low=x['Low_ask'],
                close=x['Close_ask'],
                window=atr_period
            ).average_true_range(),
            include_groups=False
        )
    ).round(5)
    target_df['ATR_available'] = target_df['ATR'] > 0

    # ep
    target_df['entry_offset'] = (target_df['ATR'] * entrance_factor).round(5)
    target_df['ep'] = (target_df['Open_ask'].shift(-1) - target_df['entry_offset']).round(5)

    # adding ep_flag
    target_df['ep_flag'] = (
        (target_df['Low_ask'].shift(-1) <= target_df['ep']) &
        (target_df['ep'] <= target_df['High_ask'].shift(-1) )
        ).astype(int)
    target_df.loc[target_df.index[-1], "ep_flag"] = -1

    # updating the flag
    target_df["DataConsistencyFlag"] = np.where(
        (target_df["DataConsistencyFlag"] == "5m consistent")
        & (target_df["DataConsistencyFlag"].shift(-1) == "5m consistent"),
        "5m consistent",
        "inconsistent",
    )

    # sl and TP
    target_df['sl'] = target_df['ep'] - target_df['ATR'] * risk_factor
    target_df['tp'] = target_df['ep'] + target_df['ATR'] * reward_factor

    # Condition 1: If entry point (ep_flag) was not reached
    target_df.loc[target_df['ep_flag'] == 0, 'ep_flag_desc'] = "EP_NotHit"
    target_df.loc[target_df['ep_flag'] == 1, 'ep_flag_desc'] = "Check_5m"

    # Orden
    # target_df = target_df.drop(['Volume_ask','FilledMethod','WasMissing','ATR14_50','Close_ask','ep_flag'], axis=1)
    target_df = target_df.drop(['FilledMethod','WasMissing','ATR','ep_flag'], axis=1)
    target_df.rename(columns={'DataConsistencyFlag': 'DataConsistencyFlag_ask'}, inplace=True)
    column_order = ['Open_ask','entry_offset','ep', 'Low_ask','High_ask','Close_ask','Volume_ask', 'sl', 'tp', 'ep_flag_desc','DataConsistencyFlag_ask','ATR_available']
    target_df = target_df[column_order]

    # sort and show
    target_df.sort_index(inplace=True)

    # traemos los bid prices
    bid_df = source_bid.copy()
    bid_df = bid_df.drop(['Volume_EURUSD','Open_EURUSD','Close_EURUSD','FilledMethod','WasMissing'], axis=1)
    bid_df.columns = [col.replace('_EURUSD', '_bid') for col in bid_df.columns]
    bid_df.rename(columns={'DataConsistencyFlag': 'DataConsistencyFlag_bid'}, inplace=True)

    #merge
    combined_df = target_df.merge(bid_df, left_index=True, right_index=True, how='left', suffixes=('', '_bid'))

    # # prints
    # print('\nMerge')
    # print(f"target_df: {len(target_df)} | bid_df: {len(bid_df)} | combined_df (after merge): {len(combined_df)}")

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

    # changing the order of columns
    first_cols = ["week", "yyyyww"]
    combined_df = combined_df[first_cols + combined_df.columns.difference(first_cols, sort=False).tolist()]
    return combined_df

# %% ---------- filter_and_report ----------
def filter_and_report(df, flag_col, drop_flag_col=False, flag_value=True):

    filtered = df[df[flag_col] == flag_value].copy()
    if drop_flag_col:
        filtered = filtered.drop(columns=[flag_col])

    return filtered

def filter_and_report_old(df, df_name, flag_col, week_col='yyyyww', drop_flag_col=False, flag_value=True):
    # n_before = len(df)
    # weeks_no_before = df[week_col].nunique()

    filtered = df[df[flag_col] == flag_value].copy()
    if drop_flag_col:
        filtered = filtered.drop(columns=[flag_col])

    # n_after = len(filtered)
    # weeks_no_after = filtered[week_col].nunique()

    # print(f'\nFiltering based on {flag_col} == {flag_value}')
    # print(f"df: {df_name} | rows before: {n_before} | rows after: {n_after} | filtered: {n_before - n_after}")
    # print(f"df: {df_name} | weeks before: {weeks_no_before} | weeks before: {weeks_no_after} | match: {weeks_no_before == weeks_no_after}")
    # print(f"df: {df_name} | avg before: {n_before // weeks_no_before} rem {n_before % weeks_no_before} | avg after: {n_after // weeks_no_after} rem {n_after % weeks_no_after} | Delta: {n_before // weeks_no_before - n_after // weeks_no_after}")
    return filtered

# %% ---------- get_5m_hits ----------
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
        "max_after_ep_datetime": bid_after_ep["High_bid"].idxmax(),
        "min_after_ep": bid_after_ep["Low_bid"].min(),
        "min_after_ep_datetime": bid_after_ep["Low_bid"].idxmin()
    }])

# %% ---------- evaluate_5m_sequence ----------
def evaluate_5m_sequence(row, df_5m, hits): 
    # definitions
    lot_size = 100000  # units per lote

    # result definition
    result = {
        "datetime": row.name,
        "Open_ask":row["Open_ask"],
        "Low_ask": row["Low_ask"],
        "High_ask": row["High_ask"],
        "Close_ask":row["Close_ask"],
        "Volume_ask":row["Volume_ask"],
        "DataConsistencyFlag": row["DataConsistencyFlag"],
        "ep": row["ep"],
        "High_bid": row["High_bid"],
        "Low_bid": row["Low_bid"],
        "sl": row["sl"],
        "tp": row["tp"],

        "open_datetime": pd.NaT,
        "open_delta_time": pd.NA,
        "close_status": "cancel trade", # Default value as a string
        "close_price": np.nan,
        "close_delta_points": pd.NA,
        "close_delta_time": pd.NA,
        "max_after_ep": np.nan,
        "max_after_ep_datetime": pd.NaT,

        "min_after_ep": np.nan,
        "min_after_ep_datetime": pd.NaT,

        "y":pd.NA # Initialize y to pd.NA, will be 0 or 1 if trade occurs
    }

    hit = hits.iloc[0]
    ep_datetime = hit["ep_datetime"]
    sl_datetime = hit["sl_datetime"]
    tp_datetime = hit["tp_datetime"]
    result["open_delta_time"] = round(((ep_datetime - (row.name + pd.Timedelta(hours=1))).total_seconds() / 60), 0)
    
    # 1. EP was never touched
    if pd.isna(ep_datetime):
        print(f'For {row.name} EP was never touched - DataConsistencyFlag:{row.DataConsistencyFlag}')
        result_df = result
        return result_df

    result["open_datetime"] = ep_datetime
    
    result["max_after_ep"] = hit["max_after_ep"]
    result["min_after_ep"] = hit["min_after_ep"]
    result["max_after_ep_datetime"] = hit["max_after_ep_datetime"]
    result["min_after_ep_datetime"] = hit["min_after_ep_datetime"]

    sl_exists = not pd.isna(sl_datetime)
    tp_exists = not pd.isna(tp_datetime)

    if df_5m.empty:
      print(f'Error | df_5m is empty for {row.name} - DataConsistencyFlag:{row.DataConsistencyFlag}')
      result_df = result
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
        result_df = result
        return result_df

    # 3. Only SL touched
    if sl_exists and not tp_exists:
        result["close_status"] = "SL"
        result["close_price"] = row["sl"]
        result["close_delta_time"] = round(((sl_datetime - ep_datetime).total_seconds() / 60), 0)
        result["close_delta_points"] = round(((result["close_price"] - result["ep"]) * lot_size), 0)
        result["y"] = 0 # Set y to 0 for a non-TP outcome
        result_df = result
        return result_df

    # 4. Only TP touched
    if tp_exists and not sl_exists:
        result["close_status"] = "TP"
        result["close_price"] = row["tp"]
        result["close_delta_time"] = round(((tp_datetime - ep_datetime).total_seconds() / 60), 0)
        result["close_delta_points"] = round(((result["close_price"] - result["ep"]) * lot_size), 0)
        result["y"] = 1 # Set y to 1 for a TP outcome
        result_df = result
        return result_df

    # 5. Both touched in the same 5m candle
    if sl_datetime == tp_datetime:
        result["close_status"] = "5m Conflict"
        result["close_delta_time"] = round(((sl_datetime - ep_datetime).total_seconds() / 60), 0)
        # No close_price or close_delta_points if conflict
        result["y"] = pd.NA # Set y to 0 for a non-TP outcome (conflict)
        result_df = result
        return result_df

    # 6. Both touched, first one wins
    if sl_datetime < tp_datetime:
        result["close_status"] = "SL"
        result["close_price"] = row["sl"]
        result["close_delta_time"] = round(((sl_datetime - ep_datetime).total_seconds() / 60), 0)
        result["close_delta_points"] = round(((result["close_price"] - result["ep"]) * lot_size), 0)
        result["y"] = 0 # Set y to 0 for a non-TP outcome
        result_df = result
        return result_df

    # If TP was touched first (implicit else: tp_datetime < sl_datetime)
    result["close_status"] = "TP"
    result["close_price"] = row["tp"]
    result["close_delta_time"] = round(((tp_datetime - ep_datetime).total_seconds() / 60), 0)
    result["close_delta_points"] = round(((result["close_price"] - result["ep"]) * lot_size), 0)
    
        
    result["y"] = 1 # Set y to 1 for a TP outcome
    # result_df = result
    return result

# %% ---------- get_week_fields ----------
def get_week_fields(datetime_values):
    # Custom trading week logic:
    # - Weeks start on Sunday.
    # - YYYY comes from Week_Start.year.
    # - Week 1 starts on the first Sunday AFTER Jan 1 of that Week_Start.year.
    # - This avoids week 0 and keeps Jan 1 out of Week 1.
    # - Returns week and YYYYWW using the same logic.

    dates = pd.to_datetime(datetime_values)

    if isinstance(dates, pd.Series):
        result = pd.DataFrame(index=datetime_values.index)
        dates_series = dates
    elif isinstance(dates, pd.DatetimeIndex):
        result = pd.DataFrame(index=datetime_values)
        dates_series = pd.Series(dates, index=datetime_values)
    else:
        date = pd.to_datetime(datetime_values)

        week_start = date.to_period("W-SAT").start_time
        year = week_start.year

        jan1 = pd.Timestamp(year=year, month=1, day=1)
        days_to_sunday = (6 - jan1.weekday()) % 7

        if days_to_sunday == 0:
            days_to_sunday = 7

        first_sunday = jan1 + pd.Timedelta(days=days_to_sunday)

        week = ((week_start - first_sunday).days // 7) + 1
        yyyyww = f"{year}{week:02d}"

        return week, yyyyww

    week_start = dates_series.dt.to_period("W-SAT").dt.start_time
    year = week_start.dt.year

    jan1 = pd.to_datetime(year.astype(str) + "-01-01")
    days_to_sunday = (6 - jan1.dt.weekday) % 7
    days_to_sunday = days_to_sunday.mask(days_to_sunday == 0, 7)

    first_sunday = jan1 + pd.to_timedelta(days_to_sunday, unit="D")

    week = ((week_start - first_sunday).dt.days // 7) + 1

    result["week"] = week.astype(int)
    result["YYYYWW"] = year.astype(str) + result["week"].astype(str).str.zfill(2)

    return result

# %% ---------- summarize_trade_results ----------
def summarize_trade_results(trade_results_df, params, n_weeks):    
    # n
    valid = trade_results_df[trade_results_df['y'].isin([0, 1])]
    n_valid = len(valid)    

    # pct_1
    pct_1 = round(valid['y'].mean() * 100, 1) if n_valid else np.nan    
    pct_pm = valid.groupby(valid.index.to_period('M'))['y'].mean() * 100
    pct_pm_avg = round(pct_pm.mean(), 1) if len(pct_pm) else np.nan
    pct_pm_std = round(pct_pm.std(), 1) if len(pct_pm) > 1 else np.nan
    
    # entries
    entries = len(trade_results_df)
    entries_per_week_series = valid.groupby(valid.index.to_period("W")).size()
    entries_per_week_avg = round(entries_per_week_series.mean(), 2) if n_weeks else np.nan
    entries_per_week_std = round(entries_per_week_series.std(), 2) if n_weeks else np.nan

    # points
    points_avg = round(valid['close_delta_points'].mean(),2)
    points_std = round(valid['close_delta_points'].std(),2)
    points_per_week_series = valid.groupby(valid.index.to_period("W"))["close_delta_points"].sum()
    points_per_week_avg = round(points_per_week_series.mean(), 2) if n_weeks else np.nan
    points_per_week_std = round(points_per_week_series.std(), 2) if n_weeks else np.nan
    
    # extras
    spread_points = (valid['High_ask'] - valid['High_bid']) * 100000 
    
    # for next stage
    status_counts = trade_results_df['close_status'].value_counts(dropna=False)
    sl_points = (valid.loc[valid["close_status"] == "SL", "close_delta_points"])
    tp_points = (valid.loc[valid["close_status"] == "TP", "close_delta_points"])      
    wins = valid.loc[valid['y'] == 1, 'close_delta_points']
    losses = valid.loc[valid['y'] == 0, 'close_delta_points']
    winners = trade_results_df[trade_results_df['y'] == 1]
    losers = trade_results_df[trade_results_df['y'] == 0]
    
    return {
        "params": params,
                
        # n
        "n_na": int(trade_results_df['y'].isna().sum()),        
        "n_0": int((valid['y'] == 0).sum()),
        "n_1": int((valid['y'] == 1).sum()),
        "n_01": n_valid,
        "n_total": entries,

        # pct
        "pct_1": pct_1, 
        "pct_pm_avg": pct_pm_avg,
        "pct_pm_std": pct_pm_std,
        
        #entries
        "entries_total": entries,       
        "entries_per_week_avg":entries_per_week_avg,
        "entries_per_week_std":entries_per_week_std,
        
        #points
        "points_avg": points_avg,
        "points_std": points_std,            
        "points_per_week_avg": points_per_week_avg,
        "points_per_week_std": points_per_week_std,
        
        # extras
        "spread_points_avg": round(spread_points.mean(), 1) if n_valid else np.nan,    
        "open_delta_time_avg": round(valid['open_delta_time'].mean(), 1) if n_valid else np.nan,
        "close_delta_time_avg": round(valid['close_delta_time'].mean(), 1) if n_valid else np.nan,          
                            
        # for next stage   
        #points
        "avg_sl_points": round(sl_points.mean(), 1) if n_valid else np.nan,
        "avg_tp_points": round(tp_points.mean(), 1) if n_valid else np.nan,        
        # extras
        "n_SL": int(status_counts.get("SL", 0)),
        "n_TP": int(status_counts.get("TP", 0)),        
        "n_Timeout": int(status_counts.get("Timeout", 0)),                
        "avg_win": round(wins.mean(), 2) if len(wins) else np.nan,
        "avg_loss": round(losses.mean(), 2) if len(losses) else np.nan,        
        #advance
        "avg_MFE_win": round(winners['max_delta_points'].mean(), 2) if len(winners) else np.nan,
        "avg_MFE_loss": round(losers['max_delta_points'].mean(), 2) if len(losers) else np.nan,
        "avg_MAE_win": round(winners['min_delta_points'].mean(), 2) if len(winners) else np.nan,
        "avg_MAE_loss": round(losers['min_delta_points'].mean(), 2) if len(losers) else np.nan,
        
        
    }

# %% ---------- simulate_5m_trades ----------
def simulate_5m_trades(trade_list, source_ask5, source_bid5, lookahead_hours, verbosity = False):
    results = []
    lot_size = 100000

    # for idx, row in trade_list.head(3).iterrows(): #.head(1)
    for idx, row in trade_list.iterrows(): 
        dt_from = pd.to_datetime(row.name) + pd.Timedelta(hours=1)
        dt_to = dt_from + pd.Timedelta(hours=lookahead_hours)
        
        
        # print(f'from:{dt_from} - to:{dt_to}')

        bid_5m_reduced = (
            source_bid5.loc[dt_from : dt_to - pd.Timedelta(minutes=5),
                ['High_EURUSD', 'Low_EURUSD', 'Close_EURUSD']
            ]
            .rename(columns={
                'High_EURUSD': 'High_bid',
                'Low_EURUSD': 'Low_bid',
                'Close_EURUSD': 'Close_bid'
            })
        )
        # if bid_5m_reduced.empty:
        #     # print(f'For {row.name} bid_5m is empty from {dt_from} to {dt_to} - DataConsistencyFlag:{row.DataConsistencyFlag}')
        #     continue

        ask_5m_reduced = (
            source_ask5.loc[dt_from : dt_to - pd.Timedelta(minutes=5),
                ['High_EURUSD', 'Low_EURUSD']
            ]
            .rename(columns={
                'High_EURUSD': 'High_ask',
                'Low_EURUSD': 'Low_ask'
            })
        )
        # if ask_5m_reduced.empty:
        #     # print(f'For {row.name} ask_5m is empty from {dt_from} to {dt_to} - DataConsistencyFlag:{row.DataConsistencyFlag}')
        #     continue

        hits = get_5m_hits(row, bid_5m_reduced, ask_5m_reduced)

        # if verbosity:
        #     print(f'Hits from: {dt_from} to {dt_to} (not included)')
        #     print(f'{hits}')

        result = evaluate_5m_sequence(row=row, df_5m = bid_5m_reduced, hits = hits) 
        
        # add open_delta_points
        open_delta_points = round(row.entry_offset * lot_size, 0) #(row.entry_offset*lot_size).round(0)
        result["open_delta_points"] = open_delta_points

        # if not result_df:
        #     print(f"For {row.name} result coming from evaluate_5m_sequence() is empty - DataConsistencyFlag: {row.DataConsistencyFlag}")
        # else:
        #     results.append(result)
        results.append(result)    
            

    # concat
    results_df = pd.DataFrame(results).astype(column_dtypes)

    # max and min time and points
    results_df['max_delta_points'] = ((results_df['max_after_ep'] - results_df['ep']) * lot_size).round(0)
    results_df['min_delta_points'] = ((results_df['min_after_ep'] - results_df['ep']) * lot_size).round(0)
    results_df['max_delta_time'] = ((results_df['max_after_ep_datetime'] - results_df['open_datetime']).dt.total_seconds() / 60).round(0)
    results_df['min_delta_time'] = ((results_df['min_after_ep_datetime'] - results_df['open_datetime']).dt.total_seconds() / 60).round(0)
    results_df['open_delta_points'] = ((results_df['max_after_ep'] - results_df['ep']) * lot_size).round(0)

    # drop Unneded columns
    results_df = results_df.drop(columns=['max_after_ep','min_after_ep','max_after_ep_datetime','min_after_ep_datetime','open_datetime','close_price'])  

    return results_df.set_index('datetime')



# %% ---------- run ----------
"""# **4 - Importo Datasets**"""

source_ask, source_bid, source_ask5, source_bid5 = get_source_datasets(pair_name)

"""# **5 - Calculo Y's**"""

# obtengo strategy_params_grid
strategy_params_grid = generar_strategy_grid(strategy_grid)

# inicializo
param_results = []
iteration_mins_acum = 0
# iteramos param_grid
for idx, params in strategy_params_grid.iterrows():
    start_time = time.perf_counter()
    atr_period      = int(params['atr_period'])
    entrance_factor = params['entrance_factor']         # ep = open_price(+1h) - ATR * entrance_factor
    risk_factor     = params['risk_factor']             # sl = ep - ATR * risk_factor
    reward_factor   = params['reward_factor']           # tp = ep + ATR * reward_factor
    lookahead_hours = int(params["lookahead_hours"])
    progress = round(((idx+1)/total_combinations)*100,2)
    print(f"Iter {(idx+1):03d}/{total_combinations:03d} | Lookahead: {lookahead_hours}h | ATR Per: {atr_period:<3} | Ent Fac: {entrance_factor:<4} | Risk: {risk_factor:<4} | Reward: {reward_factor:<4} | Progress: {progress}%")

    # Add: 'ep_flag_desc','ATR_available' & Filter Rows:  'ATR_available' == True
    hourly_candidates = build_hourly_candidates(params, source_ask, source_bid)
    hourly_candidates = filter_and_report(hourly_candidates, 'ATR_available', drop_flag_col=True)

    # Add: 'has_lookahead' & filter 'has_lookahead' == True
    hourly_candidates['has_lookahead'] = (
        hourly_candidates
        .groupby('yyyyww', group_keys=False)
        .apply(
            lambda x: pd.Series(
                [True] * (len(x) - lookahead_hours) + [False] * lookahead_hours,
                index=x.index,
            ),
            include_groups=False,
        )
    )
    hourly_candidates = filter_and_report(hourly_candidates, 'has_lookahead', drop_flag_col=True)

    # 1. Pre-crear columnas vacías en el maestro
    hourly_candidates[[ 'open_delta_points', 'open_delta_time','max_delta_points', 'min_delta_points', 'max_delta_time', 'min_delta_time']] = None 
    
    # 2. Filtrar subconjunto y simular
    subset = hourly_candidates[hourly_candidates['ep_flag_desc'] == "Check_5m"]
    trade_results = simulate_5m_trades(subset, source_ask5, source_bid5, lookahead_hours)
    
    # 3. Asignación limpia usando .values para evitar el choque de índices
    if not trade_results.empty:
        hourly_candidates.loc[subset.index, trade_results.columns] = trade_results.values

    # completing modeling_results
    param_results.append(summarize_trade_results(trade_results_df = trade_results, 
                                                 params = params, 
                                                 n_weeks = hourly_candidates['yyyyww'].nunique()
                                                 )
                        )

    # merging to get y    
    param_backtest = hourly_candidates.copy()
    param_nulls = param_backtest[param_backtest['y'].isna()]
    param_backtest['y'] = param_backtest['y'].astype('Int64')     

    # time calc
    iteration_mins = (time.perf_counter() - start_time) / 60
    iteration_mins_acum = iteration_mins_acum + iteration_mins
    print(f"Iter {idx + 1:03d}/{total_combinations:03d} >> Iter ended | Took {iteration_mins:.2f} minutes | Total acumulated time {iteration_mins_acum:.2f} minutes")
    
    # # to csv
    params_for_csv_name = f'lh{lookahead_hours}_atr{atr_period}_ef{entrance_factor}_rf{risk_factor}_rwf{reward_factor}' #modeling_EURUSD_ask
    param_backtest.to_csv(f'{idx}_param_backtest_{params_for_csv_name}.csv')
    print(f'Iter {idx + 1:03d}/{total_combinations:03d} >> File saved | File name "param_backtest_{params_for_csv_name}.csv"\n') 



# param_backtest_df = pd.DataFrame(param_backtest)
param_results_df = pd.DataFrame(param_results)

# 1. Convertir la columna de Series en un DataFrame expandido
params_expanded = pd.DataFrame(param_results_df['params'].tolist())
# 2. Unir el nuevo DataFrame con el original (eliminando la columna 'params' anterior)
param_results_df = pd.concat([param_results_df.drop(columns=['params']), params_expanded], axis=1)

from datetime import datetime
param_results_df.to_csv(f'param_results_run_{datetime.now().strftime("%Y%m%d")}.csv')





