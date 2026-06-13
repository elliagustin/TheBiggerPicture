

# -*- coding: utf-8 -*-
"""
Test

"""

import pandas as pd
import os
import csv
from datetime import datetime
import joblib
import helpers.oanda as oa
import helpers.mssql as ms
import matplotlib.pyplot as plt
from ta.momentum import RSIIndicator


def load_model(_name, _model_version, _currency):
    """
    Load a machine learning model from disk based on the provided name, version, and currency.

    Parameters:
    _name (str): The name of the model.
    _model_version (str): The version of the model.
    _currency (str): The currency for the model.

    Returns:
    model: The loaded model.
    """
    # Construct the model file path
    _model_file_path = f"models/{_name}_v{_model_version}_{_currency}.pkl"
    #print(f'Running model: {_name}_v{_model_version}_{_currency}')
    
    # Load the model from disk
    model = joblib.load(_model_file_path)
    
    return model




def get_pair_list(industry):
    if industry == 'forex':
        file_location = "C:/Users/BernardoElli/OneDrive/Python/RandomForest/model_rsi/files/derivatives_list.csv"
        pair_list = pd.read_csv(file_location, header=None)
        return pair_list
    elif industry == 'crypto':
        file_location = "C:/Users/BernardoElli/OneDrive/Python/RandomForest/model_rsi/files/crypto_list.csv"
        pair_list = pd.read_csv(file_location, header=None)
        return pair_list
    else:
        return 'No list'
    

def markets_info(market = 'forex'):
# markets_info()
    aux = get_pair_list(market)
    for index, row in aux.iterrows():
        currency = row[0]
        oa.is_forex_market_open(currency)
    
    
def adjust_JPY_pairs(allPairs):
    allPairs = pd.DataFrame(allPairs)
    JPY_columns_list = allPairs.filter(like='JPY', axis=1).filter(regex='^(?!Volume)').columns.values
    # print('Divide JPY columns by 100: ')
    # print(JPY_columns_list)

    for i in allPairs:
        if (i in JPY_columns_list):
            allPairs[i] = allPairs[i]/100
    
    return allPairs

def adjust_volume(allPairs):
    allPairs = pd.DataFrame(allPairs)
    Vol_columns_list = allPairs.filter(like='Volume', axis=1).columns.values
    # print('Divide Volume columns by 6000: ')
    # print(Vol_columns_list)

    for i in allPairs:
        if (i in Vol_columns_list):
            allPairs[i] = allPairs[i]/6000
    
    return allPairs

def ensure_directory_exists(path):
    import os
    if not os.path.exists(path):
        os.makedirs(path)
        


def get_target(model_name):
# get_target('B10.500.35.75')
    folder_location = "C:/Users/BernardoElli/OneDrive/Python/RandomForest/files/summary.csv" 
    summaries = pd.read_csv(folder_location)    
    summary = summaries.loc[summaries['name'] == model_name]
    return summary['TP_points'].item()/100000
        
def get_threshold(model_name):
     folder_location = "C:/Users/BernardoElli/OneDrive/Python/RandomForest/files/summary.csv" 
     summaries = pd.read_csv(folder_location)    
     summary = summaries.loc[summaries['name'] == model_name]
     return summary['confidence'].item()       
 
def get_volume(pair_name):
    
    file_location = "C:/Users/BernardoElli/OneDrive/Python/RandomForest/files/pair_details.csv"
    pair_list = pd.read_csv(file_location)
    lot_size_str = pair_list[pair_list['Name']==pair_name]['LotSize'].iloc[0]
    lot_size_str_cleaned = lot_size_str.strip().replace(',', '')

    # Convert the cleaned string to an integer
    lot_size_int = int(lot_size_str_cleaned)
    return lot_size_int
 
def get_delta(X, pair_name, success_prob):
  
    model_name_SL0 = 'SL00.200.50.75'
    model_SL0 = load_model(pair_name,model_name_SL0)
    predicted_probabilities_SL0 = model_SL0.predict_proba(X)[:, 1]
    
    model_name_SL1 = 'SL01.200.75.75'
    model_SL1 = load_model(pair_name,model_name_SL1)
    predicted_probabilities_SL1 = model_SL1.predict_proba(X)[:, 1]
    
    model_name_SL2 = 'SL02.200.100.75'
    model_SL2 = load_model(pair_name,model_name_SL2)
    predicted_probabilities_SL2 = model_SL2.predict_proba(X)[:, 1]
    
    model_name_SL3 = 'SL03.200.125.75'
    model_SL3 = load_model(pair_name,model_name_SL3)
    predicted_probabilities_SL3 = model_SL3.predict_proba(X)[:, 1]  
    

    num0, num1, num2, num3 = predicted_probabilities_SL0.item(), predicted_probabilities_SL1.item(), predicted_probabilities_SL2.item(),predicted_probabilities_SL3.item()

    rate1 = (num0 - num1)/25
    rate2 = (num1 - num2)/25
    rate3 = (num2 - num3)/25
    
    print(f'\nSL 50pts:{predicted_probabilities_SL0.item():0.3f}')
    print(f'SL 75pts:{predicted_probabilities_SL1.item()}:{rate1:0.3f}')
    print(f'SL 100pts:{predicted_probabilities_SL2.item()}:{rate2:0.3f}')
    print(f'SL 125pts:{predicted_probabilities_SL3.item()}:{rate3:0.3f}')

    max_rate = max(rate1, rate2, rate3)
    # print(f'max rate:{max_rate:0.3f}')

    if success_prob < num0:
        # print(f'There is more prob of going down {num0} than going up {success_prob}. No trade')
        return 0
    elif max_rate == rate1:
        # print(f'Selecting model SL 75pts. Prob {num1}')
        return get_target(model_name_SL1)
    elif max_rate == rate2:
        # print(f'Selecting model SL 100pts. Prob {num2}')
        return get_target(model_name_SL2)
    else:
        # print(f'Selecting model SL 125pts. Prob {num3}')
        return get_target(model_name_SL3)
    

def get_now():
    import datetime
    
    now_datetime = pd.to_datetime(datetime.datetime.now()).strftime('%Y-%m-%d %H:%M:%S')
    
    return now_datetime


def get_delay():
    import time

    time.sleep(5)
    print('\nRunning in 3')
    time.sleep(1)
    print('Running in 2')
    time.sleep(1)
    print('Running in 1')
    time.sleep(1)
    return print('Running now...')


def get_time_until_next_hour():
    from datetime import datetime
    # Get the current time
    current_time = datetime.now()
    # Calculate the minutes until the next hour
    minutes_until_next_hour = (60 - current_time.minute) % 60
    
    return minutes_until_next_hour


def read_files(file_name):
    folder_path = 'C:\\Users\\BernardoElli\\OneDrive\\Python\\RandomForest\\files\\'
    trade_details = pd.read_csv(f'{folder_path}{file_name}')
    return trade_details

def write_files(file_name, df):
    current_folder = 'C:\\Users\\BernardoElli\\OneDrive\\Python\\RandomForest\\files\\'
    return  df.to_csv(f'{current_folder}{file_name}', index=False) 



def get_utc_and_local_time():
    import datetime
    # Get current UTC time
    utc_now = datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')

    # Get current local time
    local_now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    # Get the current hour without the 59 minutes
    current_time = datetime.datetime.utcnow()
    current_hour = current_time.replace(minute=0, second=0, microsecond=0)

    # Add an extra hour
    next_hour = current_hour + datetime.timedelta(hours=1)
    next_hour_utc = next_hour.strftime('%Y-%m-%d %H:%M:%S')
    # print('Returning: utc_now, local_now, next_hour_utc')

    return utc_now, local_now, next_hour_utc


def to_csv_log(event_type, event_details=None, param1=None, param2=None, param3=None, param4=None, param5=None, 
               param6=None, param7=None, param8=None, param9=None, param10=None):
    
    #  to_csv_log('test', 'test_details', 123)
    
    # Get the current UTC date
    current_utc_date = datetime.utcnow().strftime("%Y-%m-%d")

    # Create the folder if it doesn't exist
    logs_folder = "logs"
    if not os.path.exists(logs_folder):
        os.makedirs(logs_folder)

    # Construct the file path
    file_name = os.path.join(logs_folder, f"Log_{current_utc_date}.csv")

    # Check if the file exists
    file_exists = os.path.exists(file_name)

    # Define headers for the CSV file
    headers = ['UTC Time', 'Event Type', 'Event Details'] + [f'param_{i}' for i in range(1, 11)]

    # Open the CSV file in append mode or create a new one
    with open(file_name, 'a', newline='') as csvfile:
        csv_writer = csv.writer(csvfile)
        
        # Write headers only if the file didn't exist before
        if not file_exists:
            csv_writer.writerow(headers)

        # Get the current UTC time
        current_utc_time = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")

        # Create a row to append to the CSV file
        row = [current_utc_time, event_type, event_details] + [param1, param2, param3, param4, param5, param6, param7, param8, param9, param10]

        # Write the row to the CSV file
        csv_writer.writerow(row)

        #print(f"Row added to {file_name} successfully.")


def get_RSI(dataset, n=14):
    rsi_series = RSIIndicator(close=dataset, window=n).rsi()
    return rsi_series.rename(dataset.name if dataset.name else "RSI")



def get_x_and_targets(from_date, to_date = None): 
    
    if to_date is None:
        _EUR = ms.get_data_from_sql('[mid].[Vw_EUR]',from_date).sort_index()
        _USD = ms.get_data_from_sql('[mid].[Vw_USD]',from_date).sort_index()
        _AUD = ms.get_data_from_sql('[mid].[Vw_AUD]',from_date).sort_index()
        _CAD = ms.get_data_from_sql('[mid].[Vw_CAD]',from_date).sort_index()
        _GBP = ms.get_data_from_sql('[mid].[Vw_GBP]',from_date).sort_index()
        _JPY = ms.get_data_from_sql('[mid].[Vw_JPY]',from_date).sort_index()
        _NZD = ms.get_data_from_sql('[mid].[Vw_NZD]',from_date).sort_index()
        _CHF = ms.get_data_from_sql('[mid].[Vw_CHF]',from_date).sort_index()
    else:
        _EUR = ms.get_sql_from_to(from_date, to_date, database = 'tbpStaging',schema_name = 'mid',table_name = 'Vw_EUR').sort_index()
        _USD = ms.get_sql_from_to(from_date, to_date, database = 'tbpStaging',schema_name = 'mid',table_name = 'Vw_USD').sort_index()
        _AUD = ms.get_sql_from_to(from_date, to_date, database = 'tbpStaging',schema_name = 'mid',table_name = 'Vw_AUD').sort_index()
        _CAD = ms.get_sql_from_to(from_date, to_date, database = 'tbpStaging',schema_name = 'mid',table_name = 'Vw_CAD').sort_index()
        _GBP = ms.get_sql_from_to(from_date, to_date, database = 'tbpStaging',schema_name = 'mid',table_name = 'Vw_GBP').sort_index()
        _JPY = ms.get_sql_from_to(from_date, to_date, database = 'tbpStaging',schema_name = 'mid',table_name = 'Vw_JPY').sort_index()
        _NZD = ms.get_sql_from_to(from_date, to_date, database = 'tbpStaging',schema_name = 'mid',table_name = 'Vw_NZD').sort_index()
        _CHF = ms.get_sql_from_to(from_date, to_date, database = 'tbpStaging',schema_name = 'mid',table_name = 'Vw_CHF').sort_index()
    
    
   
    _EUR = _EUR.fillna(_EUR.mean())
    _USD = _USD.fillna(_USD.mean())
    _AUD = _AUD.fillna(_AUD.mean())
    _CAD = _CAD.fillna(_CAD.mean())
    _GBP = _GBP.fillna(_GBP.mean())
    _JPY = _JPY.fillna(_JPY.mean())
    _NZD = _NZD.fillna(_NZD.mean())
    _CHF = _CHF.fillna(_CHF.mean())
    
    # Merging with X
    X = get_RSI(_EUR.iloc[:,0]) 
    for column in _EUR.columns[1:]:
        X = pd.merge(X,get_RSI(_EUR[column]), on='Datetime')
    for column in _USD.columns:
        X = pd.merge(X,get_RSI(_USD[column]), on='Datetime')
    for column in _AUD.columns:
        X = pd.merge(X,get_RSI(_AUD[column]), on='Datetime')
    for column in _CAD.columns:
        X = pd.merge(X,get_RSI(_CAD[column]), on='Datetime')     
    for column in _GBP.columns:
        X = pd.merge(X,get_RSI(_GBP[column]), on='Datetime') 
    for column in _JPY.columns:
        X = pd.merge(X,get_RSI(_JPY[column]), on='Datetime') 
    for column in _NZD.columns:
        X = pd.merge(X,get_RSI(_NZD[column]), on='Datetime')
    for column in _CHF.columns:
        X = pd.merge(X,get_RSI(_CHF[column]), on='Datetime')   
        
    
    targets = {'EUR': _EUR,'USD': _USD,'AUD': _AUD,'CAD': _CAD,'GBP': _GBP,'JPY': _JPY,'NZD': _NZD,'CHF': _CHF}
    
    # limit the amount of columns
    _column_names = ['AUDCAD', 'AUDCHF', 'AUDJPY', 'AUDNZD', 'AUDUSD',    
                    'CADCHF', 'CADJPY', 
                    'CHFJPY', 
                    'EURAUD', 'EURCAD','EURCHF', 'EURGBP', 'EURJPY', 'EURNZD', 'EURUSD',    
                    'GBPAUD', 'GBPCAD', 'GBPCHF', 'GBPJPY', 'GBPNZD', 'GBPUSD', 
                    'NZDCAD', 'NZDCHF', 'NZDJPY', 'NZDUSD',    
                    'USDCAD', 'USDCHF', 'USDJPY']
    
    X = X[_column_names]
    
    #adding hour and week day
    X['Hour'] = X.index.hour
    X['Day_of_Week'] = X.index.dayofweek  # Monday=0, Sunday=6
       
    # Agregarle el volumen a X
    if to_date is None:
        _Vol = ms.get_data_from_sql('[mid].[Vw_Vol]',from_date).sort_index()
    else:
        _Vol = ms.get_sql_from_to(from_date, to_date, database = 'tbpStaging',schema_name = 'mid', table_name = 'Vw_Vol').sort_index()
        
    _Vol = _Vol.fillna(_Vol.mean())
    X = pd.merge(X,_Vol, on='Datetime')
    
    return X.dropna(), targets
 

def to_points(pair, price):
    if 'JPY' in pair:
        return price * 1000
    else:
        return price * 100000        
   
    
def from_points(pair, price):
    if 'JPY' in pair:
        return price / 1000
    else:
        return price / 100000   
    
    
def plot_rsi_difference_distribution(dataset, dataset_predicted, monthly_mae):
    import numpy as np
    
    # Calculate the difference between predicted RSI and the actual RSI (45-degree line)
    differences = dataset_predicted - dataset
    
    # Create bins for RSI values from 0 to 100
    bins = np.arange(0, 101)
    
    # Calculate the average difference within each bin
    bin_means = []
    for i in range(len(bins) - 1):
        mask = (dataset >= bins[i]) & (dataset < bins[i + 1])
        if np.any(mask):
            bin_means.append(np.mean(differences[mask]))
        else:
            bin_means.append(0)  # If no data points in this bin, set the mean difference to 0
    
    # Plot the bar chart
    plt.bar(bins[:-1], bin_means, width=1, align='edge', color='blue', edgecolor='black')
    
    # Add labels and title
    plt.xlabel("RSI Values")
    plt.ylabel("Average Difference (Predicted RSI - Actual RSI)")
    plt.title("Predicted RSI and 45-degree Line")
    plt.legend([f"Monthly MAE: {monthly_mae}"])
    
    # Show plot
    plt.show()
       
    
def get_analysis(dataset, dataset_predicted, currency, stage, model_name, model_version, n_estimators,dataset_size): 

    from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
    from sklearn.metrics import explained_variance_score
    import numpy as np
    import matplotlib.pyplot as plt
    


    ##########
    
    print(f'Stage: {stage}')
    # Assuming y_true and y_pred are your actual and predicted values, respectively
    mae = mean_absolute_error(dataset, dataset_predicted)
    print(f"{currency} - Mean Absolute Error (MAE) :", round(mae, 2))
    
    # Assuming y_true and y_pred are your actual and predicted values, respectively
    monthly_mae = round(mae * 120 * 52 / 12)
    print(f"{currency} - Monthly Mean Absolute Error : {monthly_mae}")  
    
    # Assuming y_true and y_pred are your actual and predicted values, respectively
    mse = mean_squared_error(dataset, dataset_predicted)
    print(f"{currency} - Mean Squared Error (MSE):", round(mse, 2))
    
    # Assuming y_true and y_pred are your actual and predicted values, respectively
    r2 = r2_score(dataset, dataset_predicted)
    print(f"{currency} - R-squared (R^2):", round(r2, 2))

    # Calculate Explained Variance Score
    dataset_series = dataset.squeeze()
    dataset_predicted_series = dataset_predicted.squeeze()
    explained_variance = explained_variance_score(dataset_series, dataset_predicted_series)
    print(f"{currency} - Explained Variance Score: {explained_variance:.2f}")
        
    results_df = pd.Series({
        'Model Name': model_name,
        'Version': model_version,
        'Currency': currency,
        'Stage': stage,
        'MAE': mae,
        'Weekly MAE': monthly_mae,
        'MSE': mse,
        'R2': r2,
        'Explained Variance': explained_variance
    })

    # Plotting the scatter plot with small point size
    plt.scatter(dataset, dataset_predicted, s=10, label='Data points')
    
    # Adding a trend line
    z = np.polyfit(dataset, dataset_predicted, 1)
    p = np.poly1d(z)
    plt.plot(dataset, p(dataset), "r--", label='Trend line')
    
    # Adding a 45-degree line in black
    plt.plot(dataset, dataset, 'k-', label='45-degree line')
    
    # Adding labels and title
    plt.xlabel("Actual RSI")
    plt.ylabel("Predicted RSI")
    plt.title(f"{currency} - {stage} - Monthly MEA : {monthly_mae}")
    
    # Adding legend with n_estimators and dataset_size
    plt.legend(title=f"n_estimators: {n_estimators}\nDataset size: {dataset_size}")

    # Show plot
    plt.show()
    
    plot_rsi_difference_distribution(dataset, dataset_predicted, monthly_mae)
        
    return results_df


def get_x_and_targets_full():
    _EUR = ms.get_all_table('[mid].[Vw_EUR]').sort_index()
    _USD = ms.get_all_table('[mid].[Vw_USD]').sort_index()
    _AUD = ms.get_all_table('[mid].[Vw_AUD]').sort_index()
    _CAD = ms.get_all_table('[mid].[Vw_CAD]').sort_index()
    _GBP = ms.get_all_table('[mid].[Vw_GBP]').sort_index()
    _JPY = ms.get_all_table('[mid].[Vw_JPY]').sort_index()
    _NZD = ms.get_all_table('[mid].[Vw_NZD]').sort_index()
    _CHF = ms.get_all_table('[mid].[Vw_CHF]').sort_index()
    
    
    _EUR = _EUR.fillna(_EUR.mean())
    _USD = _USD.fillna(_USD.mean())
    _AUD = _AUD.fillna(_AUD.mean())
    _CAD = _CAD.fillna(_CAD.mean())
    _GBP = _GBP.fillna(_GBP.mean())
    _JPY = _JPY.fillna(_JPY.mean())
    _NZD = _NZD.fillna(_NZD.mean())
    _CHF = _CHF.fillna(_CHF.mean())
    
    targets = {
        'EUR': _EUR,
        'USD': _USD,
        'AUD': _AUD,
        'CAD': _CAD,
        'GBP': _GBP,
        'JPY': _JPY,
        'NZD': _NZD,
        'CHF': _CHF
    }
    
    # Merging with X
    X = get_RSI(_EUR.iloc[:,0]) 
    for column in _EUR.columns[1:]:
        X = pd.merge(X,get_RSI(_EUR[column]), on='Datetime')
    for column in _USD.columns:
        X = pd.merge(X,get_RSI(_USD[column]), on='Datetime')
    for column in _AUD.columns:
        X = pd.merge(X,get_RSI(_AUD[column]), on='Datetime')
    for column in _CAD.columns:
        X = pd.merge(X,get_RSI(_CAD[column]), on='Datetime')     
    for column in _GBP.columns:
        X = pd.merge(X,get_RSI(_GBP[column]), on='Datetime') 
    for column in _JPY.columns:
        X = pd.merge(X,get_RSI(_JPY[column]), on='Datetime') 
    for column in _NZD.columns:
        X = pd.merge(X,get_RSI(_NZD[column]), on='Datetime')
    for column in _CHF.columns:
        X = pd.merge(X,get_RSI(_CHF[column]), on='Datetime')       
    
    # limit the amount of columns
    column_names = ['AUDCAD', 'AUDCHF', 'AUDJPY', 'AUDNZD', 'AUDUSD',    
                    'CADCHF', 'CADJPY', 
                    'CHFJPY', 
                    'EURAUD', 'EURCAD','EURCHF', 'EURGBP', 'EURJPY', 'EURNZD', 'EURUSD',    
                    'GBPAUD', 'GBPCAD', 'GBPCHF', 'GBPJPY', 'GBPNZD', 'GBPUSD', 
                    'NZDCAD', 'NZDCHF', 'NZDJPY', 'NZDUSD',    
                    'USDCAD', 'USDCHF', 'USDJPY']
    
    X = X[column_names]
    
    # adding hour and week day
    X['Hour'] = X.index.hour
    X['Day_of_Week'] = X.index.dayofweek  # Monday=0, Sunday=6
    
    # Agregarle el volumen a X
    _Vol = ms.get_all_table('[mid].[Vw_Vol]').sort_index()
    _Vol = _Vol.fillna(_Vol.mean())
    X = pd.merge(X,_Vol, on='Datetime')
    return X, targets


def get_X_temp(table_name):
    #1 - Obtaining X with normalized columns when required
    X = ms.get_data_from_sql(f'{table_name}', None, '*')

    #adding hour and week day
    X['Hour'] = X.index.hour *10                # For normalization Purposes
    X['Day_of_Week'] = X.index.dayofweek *10    # Monday=0, Sunday=6

    # Agregarle el volumen a X
    if table_name == 'RSI_1H':
        _Vol = ms.get_all_table('[mid].[Vw_Vol]').sort_index() /100 # For normalization Purposes
    elif table_name == 'RSI_1H_Temp':
        _Vol = ms.get_all_table('[mid].[Vw_Vol_Temp]').sort_index() /100 # For normalization Purposes
        
    _Vol = _Vol.fillna(_Vol.mean())        
    # merge all together
    X = X.merge(_Vol, left_index=True, right_index=True)
    
    return X



# print('\n>>> Running rsi.populate_RSI()')
# calculation_date, latest_RSI_date = ms.get_latest_dates()
# _ , latest_candle_date = ms.get_latest_dates(schema_name = 'landing',table_name ='ForexMidH1')
# print(f'populate_RSI() - latest_candle_date > latest_RSI_date? - {latest_candle_date} > {latest_RSI_date}?')
# print(f'{latest_candle_date > latest_RSI_date}')            
# latest_candle_date > latest_RSI_date


# from_date = '2025-12-08 01:00'
# to_date = '2025-12-08 01:00'
# calculate_week_dates(from_date, to_date)

def calculate_week_dates(from_date, to_date=None):
    """
    Returns a list of (week_start, week_end) as STRINGS:
    'YYYY-MM-DD HH:MM:SS.mmm'
    """
    import pandas as pd

    dates_grid = []

    # normalize inputs to Timestamp
    from_ts = pd.to_datetime(from_date)
    to_ts = pd.to_datetime(to_date) if to_date is not None else None

    # resolve to_date if None
    if to_ts is None:
        _, max_dt = ms.get_latest_dates(
            schema_name='staging',
            table_name='RSI_1H'
        )
        to_ts = pd.to_datetime(max_dt)

    # align to Sunday
    days_to_sunday = (from_ts.weekday() + 1) % 7
    week_start = from_ts - pd.Timedelta(days=days_to_sunday)

    # generate weekly windows
    while week_start <= to_ts:
        # Sunday 00:00:00.000
        week_start = week_start.normalize()

        # Saturday 23:59:59.999
        week_end = week_start + pd.Timedelta(days=6, hours=23, minutes=59, seconds=59)
        
        
        start_str = week_start.strftime("%Y-%m-%d %H:%M:%S") 
        calculated_date_str = ms.get_first_price_datetime(start_str)
        end_str   = week_end.strftime("%Y-%m-%d %H:%M:%S") 
        
        dates_grid.append((start_str, calculated_date_str, end_str))
        week_start += pd.Timedelta(weeks=1)


    return dates_grid


























