# -*- coding: utf-8 -*-
"""
Created on Mon May 25 09:01:08 2026

@author: BernardoElli_P
"""
from sqlalchemy import create_engine
from datetime import timedelta
import pandas as pd
from sqlalchemy import text
from urllib.parse import quote_plus
import time, os

def get_latest_batchId(schema_name, table_name):    
    _engine = get_engine()
    latest_batchId = pd.read_sql(f'SELECT max(BatchId) FROM [{schema_name}].[{table_name}]', _engine) 
    
    result = latest_batchId.iloc[0, 0]
    return 1 if result is None else result 

def insert_new_rows_to_SQL(new_rows, table_name, schema_name = 'landing'):
    _engine = get_engine()
    new_rows.to_sql(table_name, con=_engine, index=True, if_exists='append', schema = schema_name)
    return 

def get_engine(database = 'tbpStaging'):
    # _engine = get_engine()
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

def delete_sql_from_to(from_date, database, schema_name, table_name, to_date=None):
    _engine = get_engine(database=database)

    from_date = '1900-01-01 00:00:00' if from_date is None else from_date
    to_date = '3000-01-01 00:00:00' if to_date is None else to_date

    query = text(f"""
        DELETE FROM [{database}].[{schema_name}].[{table_name}]
        WHERE [Datetime] >= '{from_date}'
        AND [Datetime] <= '{to_date}'
    """)

    with _engine.connect() as conn:
        result = conn.execute(query)
        rows_deleted = result.rowcount
        conn.commit()

    if to_date == '3000-01-01 00:00:00':
        print(f"{rows_deleted} rows deleted from {schema_name}.{table_name} | from {from_date} deleted ")
    else:
        print(f"{rows_deleted} rows deleted from {schema_name}.{table_name} | from {from_date} to {to_date}")

def get_candle_from_to(    environment,     instrument,    from_date,    price_type,    granularity, to_date=None):
    from helpers.oanda import get_environmental_parameters    
    import requests
    base_url, credentials_file_name, account_id, access_token = get_environmental_parameters(environment)
    URL = f'{base_url}/v3/instruments/'
    path = f"{URL}{instrument}/candles"
    headers = {"Authorization": "Bearer " + access_token}

    params = {
        "granularity": granularity,
        "price": price_type,
        "from": from_date
    }

    if to_date is not None:
        params["to"] = to_date

    # retry up to 5 times
    for _ in range(5):
        response = requests.get(path, headers=headers, params=params)
        # print(f'params: {params}')
        # empty response → retry
        if not response.text:
            print('Empty response → retry')
            time.sleep(1)
            continue

        try:
            # print(f'response.json(): {response.json()} -------- DELETE')
            return response.json()
        except ValueError:
            # not valid JSON → retry
            time.sleep(1)
            continue

    # after 3 failed attempts
    return None

def update_sql_from_to(database ,schema_name, table_name, granularity, from_date, to_date = None, step_days = 15):    
    
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
    
    for instrument in instrument_list:
        # initializing variables
        instrument_name = instrument[:3] + instrument[-3:]
        all_json = []
        
        # # instrument = 'EUR_USD'
        # if instrument not in ['EUR_USD']:
        #     continue
        print(f'{instrument}')
        
        # reset
        from_date_pd = pd.to_datetime(from_date)
        to_date_pd   = pd.to_datetime(to_date)+timedelta(hours=1)  
        step = timedelta(days=step_days)      
        
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
                                         price_type = price_type[:1].upper(),
                                         granularity = granularity
                                         )
               
            time.sleep(1)            
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
    print(f'Inserting {len(new_rows)} in {schema_name}.{table_name}.')
    insert_new_rows_to_SQL(new_rows, table_name,schema_name)
    

# from_date = "2021-07-29 00:00:00"
# to_date = "2026-05-07 18:00:00"
## main
from_date = "2021-07-29 00:00:00"
to_date = "2023-01-01 00:00:00"
database='tbpStaging'
schema_name='landing'
granularity = "H1"
table_name=f'ForexBid{granularity}'
update_sql_from_to(database =database,
                   schema_name = schema_name, 
                   table_name = table_name, 
                   from_date = from_date, 
                   to_date = to_date, 
                   granularity = granularity, 
                   step_days = 15)



####################################################### tests
# --2021-07-29 21:40:00

from_date = "2024-05-20 16:55:00" 
to_date = "2024-05-20 17:55:00"


instrument = 'EUR_USD'
start_str = pd.Timestamp(from_date).strftime('%Y-%m-%dT%H:%M:%SZ')
end_str   = (pd.Timestamp(to_date)+timedelta(hours=1)).strftime('%Y-%m-%dT%H:%M:%SZ')
candle = get_candle_from_to( environment = 'demo',
                            instrument = instrument, 
                             from_date = start_str, 
                             to_date = end_str, 
                             price_type = 'A',
                             granularity = 'M5'
                             )
               
candle_df = pd.json_normalize(candle,record_path='candles')

