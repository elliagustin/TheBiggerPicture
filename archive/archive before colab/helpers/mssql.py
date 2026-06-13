# -*- coding: utf-8 -*-
"""
Created on Fri Jan  5 13:48:26 2024

@author: BernardoElli
"""

from sqlalchemy import create_engine
from datetime import timedelta
import pandas as pd
from sqlalchemy import text
from urllib.parse import quote_plus
import time, os, math

def get_engine(database = 'tbpStaging'):
    server = 'BMDATA-27451'
    # database = 'tbpStaging'
    username = 'sa'
    password = quote_plus('TempP@ss123!')   # ← password URL-encoded
    driver = 'ODBC+Driver+18+for+SQL+Server'

    connection_url = (
        f"mssql+pyodbc://{username}:{password}@{server}/{database}"
        f"?driver={driver}&TrustServerCertificate=yes"
    )

    return create_engine(connection_url)

# _engine = get_engine()



def get_all_table(table, schema ,database = 'tbpStaging'):
    if database == 'tbpStaging':
        _engine = get_engine()
    elif database == 'tbpDW':
        _engine = get_engine(database = 'tbpDW')
        
    df = pd.read_sql('SELECT * FROM '+database+'.'+schema+'.'+table+' ORDER BY 1;', _engine, index_col='Datetime') 
    df = df[~df.index.duplicated()]
    return df


def dataframe_to_SSMS(new_rows, target_table, database, schema, index=True):
    if database == 'tbpStaging':
        _engine = get_engine()
    elif database == 'tbpDW':
        _engine = get_engine(database = 'tbpDW')    
   
    if isinstance(new_rows, pd.Series):
        raise ValueError("Expected a DataFrame, got a Series.")
        
    new_rows.to_sql(target_table, con=_engine, index=index, if_exists='append', schema=schema)
    
# works
# a , b = get_latest_dates()
def get_latest_dates(database, schema_name, table_name):
    _engine = get_engine()
    query = f"SELECT max([Datetime]) AS dt FROM [{database}].[{schema_name}].[{table_name}]"
    
    latest_predicted_date = pd.read_sql(query, _engine)['dt'].iloc[0]
    
    target_date = latest_predicted_date + pd.Timedelta(hours=1)
    latest_predicted_date_plus_less_14 = target_date - pd.Timedelta(hours=14)
    
    return latest_predicted_date_plus_less_14, latest_predicted_date


def get_first_price_datetime(datetime ,database = 'tbpStaging', schema_name='landing', table_name='ForexMidH1'):
    _engine = get_engine()
    query = f'''SELECT min([Datetime]) AS dt FROM [{database}].[{schema_name}].[{table_name}] where Datetime >= '{datetime}' '''
    
    min_date = pd.read_sql(query, _engine)['dt'].iloc[0]
    
    min_date_plus_13 = min_date + pd.Timedelta(hours=13)
    
    # target_date = latest_predicted_date + pd.Timedelta(hours=1)
    # latest_predicted_date_plus_less_14 = target_date - pd.Timedelta(hours=14)
    
    return min_date_plus_13.strftime("%Y-%m-%d %H:%M:%S")


def get_RSI_data_from_to(currency, from_date, to_date = None):
# get_RSI_data_from_to(currency = 'AUD', from_date = '2025-09-26 11:00:00.000')
    _engine = get_engine()
    if to_date == None:
        query = f'''SELECT Datetime, {currency} FROM [tbpStaging].[staging].[RSI_1H] WHERE [Datetime] >= '{from_date}' ORDER BY [Datetime] DESC;'''
        data = pd.read_sql(query, _engine)
    else:
        query = f'''SELECT Datetime, {currency} FROM [tbpStaging].[staging].[RSI_1H] WHERE [Datetime] >= '{from_date}' and  [Datetime] <= '{to_date}'  ORDER BY [Datetime] DESC;'''
        data = pd.read_sql(query, _engine)
        
    data.set_index("Datetime", inplace=True)
    data.sort_index(inplace=True)

    return data

def insert_or_update_RSI_SQL(new_rows, table_name, currency):
#Recibe: y as "new_rows" para una "currency" y lo inserta en "table_name"    
    _engine = get_engine()
    
    for index, value in new_rows.items():       
        # Check if value is NaN
        if math.isnan(value):
            value = None  # Replace NaN with None (NULL) or another suitable value
        
        # Define SQL command using SQLAlchemy's text() function
        sql_command = text("EXEC UpdateOrInsertRSIValue :table_name,:datetime, :currency, :value;")
        
        # Define parameters
        params = {
            "table_name": table_name,   # cambio aquí
            "datetime": index if isinstance(index, pd.Timestamp) else pd.to_datetime(index),
            "currency": currency,
            "value": round(value, 2) if value is not None else None
        }
        
        # Execute SQL command
        with _engine.connect() as connection:
            trans = connection.begin()
            try:
                connection.execute(sql_command.bindparams(**params))
                trans.commit()
            except Exception as e:
                trans.rollback()
                print("An error occurred:", e)

    return   


def get_table_from_sql(table_name, 
                       table_schema='staging', 
                       from_date = '1900-01-01 00:00:00', 
                       to_date= '3000-01-01 00:00:00'):
    _engine = get_engine()
    
    from_date= '1900-01-01 00:00:00'if from_date is None else from_date 
    to_date= '3000-01-01 00:00:00' if to_date is None else to_date 
    
    query = f'''
        SELECT *
        FROM [{table_schema}].[{table_name}]
        WHERE Datetime >= '{from_date}' 
        AND Datetime <= '{to_date}' 
        ORDER BY [Datetime] DESC;
    '''

    df = pd.read_sql(query, _engine, index_col='Datetime')
    df.index = pd.to_datetime(df.index).astype('datetime64[s]')
    return df.sort_index()









def get_data_from_sql(table, calculation_date, direction='>='):
    
    #ms.get_data_from_sql('[staging].[Vw_EUR]',latest_predicted_date_str)
    _engine = get_engine()
    
    if direction == '>=':
        query = f"SELECT * FROM {table} WHERE [Datetime] >= '{calculation_date}' ORDER BY 1;"
    elif direction == '=':
        query = f"SELECT * FROM {table} WHERE [Datetime] = '{calculation_date}' ORDER BY 1;"
    elif direction == '>':
        query = f"SELECT * FROM {table} WHERE [Datetime] > '{calculation_date}' ORDER BY 1;"
    elif direction == '*':
        query = f"SELECT * FROM {table} ORDER BY 1;"
    else:
        print('No query selected')
        
    df = pd.read_sql(query, _engine, index_col='Datetime')
    df = df[~df.index.duplicated()]
    return df

def get_sql_from_to(from_date, to_date, database ,schema_name,table_name):
    # old defualt = database = 'tbpStaging',schema_name = 'staging',table_name= 'ForexMidH1'
    _engine = get_engine()
    
    query = f'''SELECT * FROM [{database}].[{schema_name}].[{table_name}] 
                WHERE [Datetime] >= '{from_date}' 
                AND [Datetime] <= '{to_date}' 
                ORDER BY 1;
            '''
     
    df = pd.read_sql(query, _engine, index_col='Datetime')
    # df = df[~df.index.duplicated()] #########################################
    

    return df


# get_latest_sql_date('tbpStaging','landing','ForexAskH1')
def get_latest_sql_date(database ,schema_name,table_name):
    _engine = get_engine()
    max_date = pd.read_sql(f'''SELECT max(Datetime) FROM [{database}].[{schema_name}].[{table_name}] WHERE
                            [Volume_AUDCAD] IS NOT NULL AND
                            [Volume_AUDCHF] IS NOT NULL AND
                            [Volume_AUDJPY] IS NOT NULL AND
                            [Volume_AUDNZD] IS NOT NULL AND
                            [Volume_AUDUSD] IS NOT NULL AND
                            [Volume_CADCHF] IS NOT NULL AND
                            [Volume_CADJPY] IS NOT NULL AND
                            [Volume_CHFJPY] IS NOT NULL AND
                            [Volume_EURAUD] IS NOT NULL AND
                            [Volume_EURCAD] IS NOT NULL AND
                            [Volume_EURCHF] IS NOT NULL AND
                            [Volume_EURGBP] IS NOT NULL AND
                            [Volume_EURJPY] IS NOT NULL AND
                            [Volume_EURNZD] IS NOT NULL AND
                            [Volume_EURUSD] IS NOT NULL AND
                            [Volume_GBPAUD] IS NOT NULL AND
                            [Volume_GBPCAD] IS NOT NULL AND
                            [Volume_GBPCHF] IS NOT NULL AND
                            [Volume_GBPJPY] IS NOT NULL AND
                            [Volume_GBPNZD] IS NOT NULL AND
                            [Volume_GBPUSD] IS NOT NULL AND
                            [Volume_NZDCAD] IS NOT NULL AND
                            [Volume_NZDCHF] IS NOT NULL AND
                            [Volume_NZDJPY] IS NOT NULL AND
                            [Volume_NZDUSD] IS NOT NULL AND
                            [Volume_USDCAD] IS NOT NULL AND
                            [Volume_USDCHF] IS NOT NULL AND
                            [Volume_USDJPY] IS NOT NULL
                           ''', _engine) 
    
    latest_sql_date = max_date.iloc[0,0].strftime('%Y-%m-%d %H:%M:%S')
    # print(f"Successfully retrieved latest date from SSMS : {latest_sql_date}")
    return latest_sql_date

def is_sql_updated(database , schema_name ,table_name ):
    from helpers.oanda import get_latest_OANDA_date
    
    latest_sql_date = get_latest_sql_date(database=database,
                                          schema_name=schema_name,
                                          table_name = table_name)
    
    latest_OANDA_date = get_latest_OANDA_date(environment='demo', instrument = 'AUD_CAD')
    is_sql_updated = latest_sql_date == latest_OANDA_date
    if is_sql_updated:
        print(f"SSMS is updated. SSMS = OANDA = {latest_sql_date}")
    else:
        print("SSMS < OANDA. SSMS is NOT updated")
    return is_sql_updated

def get_latest_batchId(schema_name, table_name):    
    _engine = get_engine()
    latest_batchId = pd.read_sql(f'SELECT max(BatchId) FROM [{schema_name}].[{table_name}]', _engine) 
    
    result = latest_batchId.iloc[0, 0]
    return 1 if result is None else result 


def insert_new_rows_to_SQL(new_rows, table_name, schema_name = 'landing'):
    _engine = get_engine()
    new_rows.to_sql(table_name, con=_engine, index=True, if_exists='append', schema = schema_name)
    return 

        
###############################################################################
###############################################################################

def delete_sql_from_to(from_date , database ,schema_name ,table_name , to_date = None):
    _engine = get_engine(database = database)

    from_date = '1900-01-01 00:00:00' if from_date is None else from_date
    to_date = '3000-01-01 00:00:00' if to_date is None else to_date
    
    query = text(f"""
        DELETE FROM [{database}].[{schema_name}].[{table_name}]
        WHERE [Datetime] >= '{from_date}'
        AND [Datetime] <= '{to_date}'
    """)
    # print(query)
    with _engine.connect() as conn:
        conn.execute(query)
        conn.commit()
        
    if to_date == '3000-01-01 00:00:00':
        print(f"Rows from {from_date} deleted from {schema_name}.{table_name}")  
    else:
        print(f"Rows from {from_date} to {to_date} deleted from {schema_name}.{table_name}")  
    
    


def update_sql_from_to(database ,schema_name, table_name, from_date, to_date = None ):
    from helpers.oanda import get_candle_from_to
    
    print('\n>>>Running update_sql_from_to()')
    print(f'Updating {schema_name}.{table_name} from {from_date} to {to_date}')
    
    # initializing variables
    price_type = table_name[5:-2].lower()
    new_rows = pd.DataFrame()        
    try:
        base_folder = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    except NameError:
        base_folder = os.getcwd()

    instruments_folder = os.path.join(base_folder, 'files')
    instruments_file_name = 'derivatives_list.csv'
    credentials_path = os.path.join(instruments_folder, instruments_file_name)
    instrument_list = pd.read_csv(f'{credentials_path}',header=None).values.flatten().tolist()    
          
    
    #convert dates to pandas datetime
    from_date = pd.to_datetime(from_date)
    if to_date is None:
        from helpers.others import get_utc_and_local_time
        to_date ,_, _ = get_utc_and_local_time()
    to_date = pd.to_datetime(to_date)
        
    # remove current records of exist
    delete_sql_from_to(from_date = from_date, 
                       to_date= to_date,
                       database = database,
                       schema_name = schema_name,
                       table_name = table_name
                       )
    
    # instrument = 'AUD_CAD'
    for instrument in instrument_list:
        # initializing variables
        instrument_name = instrument[:3] + instrument[-3:]
        all_json = []
        
        # test
        # if instrument not in ['AUD_CAD', 'AUD_CHF']:
        #     break
        # print(f'{instrument}')
        
        # reset
        from_date_pd = pd.to_datetime(from_date)
        to_date_pd   = pd.to_datetime(to_date)
    
        step = timedelta(days=30)        
        while from_date_pd < to_date_pd:
            next_date = min(from_date_pd + step, to_date_pd)
            start_str = from_date_pd.strftime('%Y-%m-%dT%H:%M:%SZ')
            end_str   = next_date.strftime('%Y-%m-%dT%H:%M:%SZ')
    
    
            print(f'Getting {instrument} from {start_str} to {end_str}')
            
            # instrument, from_date, price , to_date = None , granularity = 'H1'
            data = get_candle_from_to( environment = 'demo',
                                        instrument = instrument, 
                                         from_date = start_str, 
                                         to_date = end_str, 
                                         price_type = price_type[:1].upper()
                                         )
               
            time.sleep(0.5)
            
            all_json.append(data)         
            from_date_pd = next_date
    
        # normalize all json from a pair        
        candles_df = pd.json_normalize(all_json,record_path='candles')
    
        # filtro las velas no completas
        candles_df = candles_df[candles_df['complete']==True]                
        candles_df = candles_df.drop(['complete'], axis=1)
    
        # poner tiempo en el formato correcto
        candles_df['time'] = candles_df['time'].apply(lambda x: pd.to_datetime(x).strftime('%Y-%m-%d %H:%M:%S'))
            
        # cambiar el orden de las columnas
        new_order_columns = ['time',f'{price_type}.o', f'{price_type}.h', f'{price_type}.l', f'{price_type}.c', 'volume']
        candles_df = candles_df[new_order_columns]
            
        # cambiar el nombre de las columnas.
        new_column_names = ['Datetime','Open_'+instrument_name, 'High_'+instrument_name, 'Low_'+instrument_name, 'Close_'+instrument_name, 'Volume_'+instrument_name]
        candles_df.columns = new_column_names
        
        # poner el tiempo como indice
        candles_df.set_index('Datetime', inplace=True)
        
        # concatenar
        new_rows = pd.concat([new_rows, candles_df], axis=1)      
                                
    
    # sort the data
    new_rows.sort_index()
    
    # update SQL
    new_rows['BatchId'] = get_latest_batchId(schema_name,table_name)+1
    
    # insert
    insert_new_rows_to_SQL(new_rows, table_name,schema_name)
    






    


# delete_row_single_datetime('2025-04-17 23:00:00.000')
def delete_sql_single_datetime(cutoff_date, database ,schema_name ,table_name):
    _engine = get_engine()
    query = text(f"""
        DELETE FROM [{database}].[{schema_name}].[{table_name}]
        WHERE [Datetime] = :cutoff_date
    """)
    with _engine.connect() as conn:
        conn.execute(query, {"cutoff_date": cutoff_date})
        conn.commit()
    print(f"Rows equal to {cutoff_date} deleted from {database}.{schema_name}.{table_name}")
    
    
def update_sql_single_datetime(cutoff_date, database ,schema_name ,table_name):
    # cutoff_date = '2021-12-05 19:00'
    from helpers.oanda import get_candle_at
    
    print(f'\nUpdating {schema_name}.{table_name} datetime {cutoff_date}')
    
    # initializing variables
    price_type = table_name[5:-4].upper()
    price_type_API = table_name[5:-2].lower()
    cutoff_date_pd = pd.to_datetime(cutoff_date)   
    
    
    new_rows = pd.DataFrame()        
    try:
        base_folder = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    except NameError:
        base_folder = os.getcwd()
 
    instruments_folder = os.path.join(base_folder, 'files')
    instruments_file_name = 'derivatives_list.csv'
    credentials_path = os.path.join(instruments_folder, instruments_file_name)
    instrument_list = pd.read_csv(f'{credentials_path}',header=None).values.flatten().tolist()
    
    # remove current records of exist
    delete_sql_single_datetime(cutoff_date = cutoff_date,
                                    database = database,
                                    schema_name = schema_name,
                                    table_name=table_name
                                    )
    
    time.sleep(1) 
    for instrument in instrument_list:
        # instrument = 'AUD_CAD' # cutoff_date = '2021-12-05 12:00'
        instrument_name = instrument[:3] + instrument[-3:]
        all_json = []
        
        cutoff_date_str = cutoff_date_pd.strftime('%Y-%m-%dT%H:%M:%SZ') 
        
        print(f'Getting {instrument} candle of {cutoff_date_str}')        
        data = get_candle_at(environment = 'demo',
                                instrument = instrument,
                                candle_datetime = cutoff_date_str,
                                # to_table = table_name,
                                price_type = price_type)
        
        
        if data is None:
            print(f'The candle is coming empty for {instrument}: {cutoff_date_str}')
            break
        time.sleep(0.5)            
        all_json.append(data)              
    
        # normalize all json from a pair
        candles_df = pd.json_normalize(all_json) #,record_path='candles')
    
        # filtro las velas no completas
        candles_df = candles_df[candles_df['complete']==True]                
        candles_df = candles_df.drop(['complete'], axis=1)
    
        # poner tiempo en el formato correcto
        candles_df['time'] = candles_df['time'].apply(lambda x: pd.to_datetime(x).strftime('%Y-%m-%d %H:%M:%S'))
            
        # cambiar el orden de las columnas
        new_order_columns = ['time',f'{price_type_API}.o', f'{price_type_API}.h', f'{price_type_API}.l', f'{price_type_API}.c', 'volume']
        candles_df = candles_df[new_order_columns]
            
        # cambiar el nombre de las columnas.
        new_column_names = ['Datetime','Open_'+instrument_name, 'High_'+instrument_name, 'Low_'+instrument_name, 'Close_'+instrument_name, 'Volume_'+instrument_name]
        candles_df.columns = new_column_names
        
        # poner el tiempo como indice
        candles_df.set_index('Datetime', inplace=True)
        
        # concatenar
        new_rows = pd.concat([new_rows, candles_df], axis=1)      
                                
    
    # sort the data
    new_rows.sort_index()
    
    # update SQL
    new_rows['BatchId'] = get_latest_batchId(schema_name,table_name)+1
    
    # insert
    insert_new_rows_to_SQL(new_rows, table_name,schema_name)
    
    
    
def delete_sql_after_or_equal_date(cutoff_date, database ,schema_name, table_name):
    _engine = get_engine()
    query = text(f"""
        DELETE FROM [{database}].[{schema_name}].[{table_name}]
        WHERE [Datetime] >= :cutoff_date
    """)
    with _engine.connect() as conn:
        conn.execute(query, {"cutoff_date": cutoff_date})
        conn.commit()
    print(f"Rows after or equalt to {cutoff_date} deleted from {schema_name}.{table_name}")


# update_sql_table() 
def update_sql_table(database, schema_name, table_name):     
    
    print('\n>>> Runing ms.update_sql_table()')
    if is_sql_updated(database = database, schema_name = schema_name, table_name = table_name):
        from helpers.others import get_utc_and_local_time
        utc_time, local_time, _ = get_utc_and_local_time()
        print(f'{table_name} is updated. No further actions are taken.')  
    else: 
        print(f'Updating {table_name}...')
        # initializing variables
        price_type = table_name[5:-2].lower()
        price_type_letter = table_name[5:-4].upper()
        new_rows = pd.DataFrame()        
        try:
            base_folder = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        except NameError:
            base_folder = os.getcwd()
         
        instruments_folder = os.path.join(base_folder, 'files')
        instruments_file_name = 'derivatives_list.csv'
        credentials_path = os.path.join(instruments_folder, instruments_file_name)
        instrument_list = pd.read_csv(f'{credentials_path}',header=None).values.flatten().tolist()
        
        latest_sql_date = get_latest_sql_date(database = database,
                                              schema_name=schema_name, 
                                              table_name = table_name)        
      
        
        latest_sql_date = pd.to_datetime(latest_sql_date)
        

        from_date = (latest_sql_date + timedelta(hours=-2)).floor('s')        
        from_date_str_sql = from_date.strftime('%Y-%m-%d %H:%M:%S')      # for SQL DELETE
        from_date_str_api = from_date.strftime('%Y-%m-%dT%H:%M:%SZ')     # for OANDA API        
        delete_sql_after_or_equal_date(cutoff_date = from_date_str_sql, 
                                       database = database,
                                       schema_name = schema_name,
                                       table_name= table_name )
            
        max_attempts = 3
        retry_delay = 3
        
        #  instrument = 'AUD_CAD'
        from helpers.oanda import get_candle_from_to
        from helpers.others import get_utc_and_local_time 
        for instrument in instrument_list:
            for attempt in range(1, max_attempts + 1):
                try:
                    latest_candle = get_candle_from_to(environment = 'demo',
                                                          instrument=instrument, 
                                                          from_date=from_date_str_api,
                                                          price_type = price_type_letter)
                    
                    
                    if not latest_candle or 'candles' not in latest_candle:
                        raise ValueError("Invalid response")
                    
                    candles_df = pd.json_normalize(latest_candle, record_path='candles')
                    
                    # Check for any null values in the entire DataFrame
                    if candles_df.isnull().any().any():
                        print(f"Attempt {attempt}: Null values found in {instrument}")
                        if attempt < max_attempts:
                            time.sleep(retry_delay)
                            continue
                        else:
                            print(f"Max attempts reached for {instrument}, skipping...")
                            break
                    
                    # If no null values, process the data
                    new_pair_name = latest_candle["instrument"][:3] + latest_candle["instrument"][-3:]
                    print(f"Successfully processed {instrument} on attempt {attempt}")
                    
                    new_pair = pd.json_normalize(latest_candle, record_path= 'candles')
                
                    # filtro las velas no completas
                    new_pair = new_pair[new_pair['complete']==True]  
                        
                    new_pair = new_pair.drop(['complete'], axis=1)
                
                    # poner tiempo en el formato correcto
                    new_pair['time'] = new_pair['time'].apply(lambda x: pd.to_datetime(x).strftime('%Y-%m-%d %H:%M:%S'))
                
                    # cambiar el orden de las columnas                    
                    new_order_columns = ['time',f'{price_type}.o', f'{price_type}.h', f'{price_type}.l', f'{price_type}.c', 'volume']
                    new_pair = new_pair[new_order_columns]
                
                    # cambiar el nombre de las columnas.
                    new_column_names = ['Datetime','Open_'+new_pair_name, 'High_'+new_pair_name, 'Low_'+new_pair_name, 'Close_'+new_pair_name, 'Volume_'+new_pair_name]
                    new_pair.columns = new_column_names
                
                    # poner el tiempo como indice
                    new_pair.set_index('Datetime', inplace=True)
                
                    # concatenar
                    new_rows = pd.concat([new_rows, new_pair], axis=1)
                    
                    break  # Exit the retry loop
                    
                except Exception as e:
                    print(f"Attempt {attempt}: Error with {instrument} - {e}")
                    if attempt < max_attempts:
                        time.sleep(retry_delay)
                    else:
                        print(f"Failed to process {instrument} after {max_attempts} attempts")
                
        # prepare the data
        new_rows.index = pd.to_datetime(new_rows.index).astype('datetime64[s]')
        new_rows = new_rows.sort_index()
        
        # normalize + deduplicate index BEFORE insert
        new_rows = new_rows[~new_rows.index.duplicated(keep='last')]
        
        # update SQL
        new_rows['BatchId'] = get_latest_batchId(schema_name,table_name)+1
        
        new_rows.index.name = "Datetime"  # critical
        insert_new_rows_to_SQL(new_rows, table_name,schema_name)
        
        utc_time, local_time, _ = get_utc_and_local_time()
        print(f'{len(new_rows)} new row/s inserted into table {schema_name}.{table_name}') 
        # of.to_csv_log('SQL', 'New Rows', f'{table_name}', f'{new_rows.shape[0]} new rows inserted' )





# def insert_or_update_sql_table_old(df, table_name, currency, column):
#     _engine = get_engine()
#     df = (
#         df
#         .dropna(subset=[f'{column}'])
#         .reset_index()
#         .rename(columns={
#             'index': 'Datetime',
#             f'{column}': 'Value',
#             'modelKey': 'ModelKey'
#         })
#     )

#     df['Value'] = df['Value']


#     merge_sql = f"""
#     MERGE {table_name} AS tgt
#     USING (VALUES (:Datetime, :ModelKey, :Value)) 
#           AS src (Datetime, ModelKey, Value)
#         ON tgt.Datetime = src.Datetime
#        AND tgt.ModelKey = src.ModelKey
#     WHEN MATCHED THEN
#         UPDATE SET {currency} = src.Value
#     WHEN NOT MATCHED THEN
#         INSERT (Datetime, ModelKey, {currency})
#         VALUES (src.Datetime, src.ModelKey, src.Value);
#     """

#     with _engine.begin() as conn:
#         for _, row in df.iterrows():
#             conn.execute(
#                 text(merge_sql),
#                 {
#                     "Datetime": row["Datetime"],
#                     "ModelKey": row["ModelKey"],
#                     "Value": row["Value"]
#                 }
#             )

def insert_or_update_sql_table(df, table_name, currency, column):

    _engine = get_engine()

    df = (
        df
        .dropna(subset=[f'{column}'])
        .reset_index()
        .rename(columns={
            'index': 'Datetime',
            f'{column}': 'Value',
            'modelKey': 'ModelKey'
        })
    )

    rows = df[['Datetime', 'ModelKey', 'Value']].to_dict(orient="records")

    merge_sql = f"""
    MERGE {table_name} AS tgt
    USING (VALUES (:Datetime, :ModelKey, :Value))
          AS src (Datetime, ModelKey, Value)
    ON tgt.Datetime = src.Datetime
    AND tgt.ModelKey = src.ModelKey
    WHEN MATCHED THEN
        UPDATE SET {currency} = src.Value
    WHEN NOT MATCHED THEN
        INSERT (Datetime, ModelKey, {currency})
        VALUES (src.Datetime, src.ModelKey, src.Value);
    """

    with _engine.begin() as conn:
        conn.execute(text(merge_sql), rows)
    

def delete_backtest_results(
    entry_offset,
    take_profit,
    stop_loss,
    threshold,
    start_dt,
    end_dt,
    database='tbpDW',
    schema='dwh',
    table='Fact_BacktestingResults'
):
    _engine = get_engine()
    
    query = text(f"""
        DELETE FROM [{database}].[{schema}].[{table}]
        WHERE EntryOffset   = :entry_offset
          AND TakeProfit    = :take_profit
          AND StopLoss      = :stop_loss
          AND Threshold     = :threshold
          AND OrderDateTime >= :start_dt
          AND OrderDateTime <  :end_dt
    """)

    params = {
        "entry_offset": entry_offset,
        "take_profit": take_profit,
        "stop_loss": stop_loss,
        "threshold": threshold,
        "start_dt": start_dt,
        "end_dt": end_dt,
    }

    with _engine.begin() as conn:
        result = conn.execute(query, params)

    print(
        f"Deleted {result.rowcount} rows from {schema}.{table} "
        f"(EO={entry_offset}, TP={take_profit}, SL={stop_loss}, TH={threshold}, "
        f"from {start_dt} to {end_dt})"
    )    
    
    

def get_spread_from_sql(pair_name, datetime):
    """
    Returns spread in POINTS at a given datetime using SSMS H1 Ask/Bid tables.
    Returns None if data is missing.
    """
    dt = pd.to_datetime(datetime)
    pair_col = pair_name.replace('_', '')

    # --- ASK ---
    df_ask = get_sql_from_to(
        from_date = dt.strftime('%Y-%m-%d %H:%M:%S'),
        to_date   = dt.strftime('%Y-%m-%d %H:%M:%S'),
        database  = 'tbpStaging',
        schema_name = 'landing',
        table_name = 'ForexAskH1'
    )

    # --- BID ---
    df_bid = get_sql_from_to(
        from_date = dt.strftime('%Y-%m-%d %H:%M:%S'),
        to_date   = dt.strftime('%Y-%m-%d %H:%M:%S'),
        database  = 'tbpStaging',
        schema_name = 'landing',
        table_name = 'ForexBidH1'
    )

    if df_ask.empty or df_bid.empty:
        print(f'The DataFrame is comming empty from SSMS | {datetime}')
        return None

    ask = df_ask.iloc[0].get(f'Close_{pair_col}')
    bid = df_bid.iloc[0].get(f'Close_{pair_col}')

    if pd.isna(ask) or pd.isna(bid):
        print(f'The DataFrame is comming empty for {pair_name} from SSMS | {datetime}')
        return None

    spread_price = abs(float(ask) - float(bid))

    return spread_price
    # # --- convert to points (same logic as backtester) ---
    # if 'JPY' in pair_name:
    #     return spread_price * 1000
    # else:
    #     return spread_price * 100000
    

def insert_order_audit(environment,
                       instrument,
                       tag,
                       http_status,
                       http_status_desc,
                       order_id,
                       request_payload,
                       response_payload):
    import json
    from datetime import datetime, UTC
    
    _engine = get_engine(database = 'tbpStaging')    
    utc_now = datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S.%f")
    
    insert_sql = text("""
        INSERT INTO tbpStaging.audit.OrderAudit
        (
            Environment,
            Instrument,
            Tag,
            HttpStatusCode,
            HttpStatusDesc,
            OrderID,
            RequestPayload,
            ResponsePayload,
            RequestedAtUTC
        )
        VALUES
        (
            :Environment,
            :Instrument,
            :Tag,
            :HttpStatusCode,
            :HttpStatusDesc,
            :OrderID,
            :RequestPayload,
            :ResponsePayload,
            :RequestedAtUTC
        )
    """)


    params = {
        "Environment": environment,
        "Instrument": instrument,
        "Tag": tag,
        "HttpStatusCode": http_status,
        "HttpStatusDesc": http_status_desc,
        "OrderID": order_id,
        "RequestPayload": json.dumps(request_payload),
        "ResponsePayload": json.dumps(response_payload),
        "RequestedAtUTC": utc_now
    }

    with _engine.begin() as conn:
        conn.execute(insert_sql, params)


def get_last_transaction_id(environment):

    _engine = get_engine(database = 'tbpStaging')
    
    query = text("""
        SELECT ISNULL(MAX(TransactionID), 0) AS MaxID
        FROM [audit].[OandaTransactions]
        WHERE Environment = :environment
    """)

    df = pd.read_sql(query, _engine, params={"environment": environment})
    return int(df.iloc[0]["MaxID"])














