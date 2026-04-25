
import pandas as pd
from datetime import datetime, timedelta, timezone
import time, os, requests, json
from helpers.mssql import insert_order_audit


def get_environmental_parameters(environment):
    if environment == "live":
        base_url = "https://api-fxtrade.oanda.com"
        credentials_file_name='OandaAccountDetailsLive.bin'
    else: 
        base_url = "https://api-fxpractice.oanda.com"
        credentials_file_name='OandaAccountDetails.bin'
    
    try:
        base_folder = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    except NameError:
        base_folder = os.getcwd()

    credentials_folder = os.path.join(base_folder, 'credentials')
    credentials_path = os.path.join(credentials_folder, credentials_file_name)

    with open(credentials_path, mode='rb') as file:
        fileContent = file.read().decode('utf-8')
        account_id = fileContent[12:32]
        access_token = fileContent[-65:]   
        
    return base_url, credentials_file_name, account_id, access_token

  

def place_market_order(environment, instrument, price ,volume, take_profit, success_confidence, stop_loss = None):
    base_url, credentials_file_name, account_id, access_token = get_environmental_parameters(environment)
    #place_market_order(access_token, account_id, instrument, units, stop_loss, take_profit) 
    endpoint = f'{base_url}/v3/accounts/{account_id}/orders'
    # headers
    headers = {
        "Content-Type": "application/json",
        "Authorization": f'Bearer {access_token}',
        "Accept-Datetime-Format": "RFC3339"
    }
    # order parameters
    if stop_loss == None:
        order_data = {
            "order": {
                "type": "MARKET",
                "instrument": instrument,
                "units": str(volume),
                "timeInForce": "FOK",  # Fill or Kill
                "positionFill": "DEFAULT",
                "takeProfitOnFill": {
                    "price": str(take_profit),
                },
            }
        }
    if stop_loss != None:
        order_data = {
            "order": {
                "type": "MARKET",
                "instrument": instrument,
                "units": str(volume),
                "timeInForce": "FOK",  # Fill or Kill
                "positionFill": "DEFAULT",
                "takeProfitOnFill": {
                    "price": str(take_profit)
                },
                "stopLossOnFill": {
                    "price": str(stop_loss)      
                    }
            }
        } 
        
    # Convert the order data to JSON
    data_json = json.dumps(order_data)
    # Make the API request to place the order
    response = requests.post(endpoint, headers=headers, data=data_json) #, auth=HTTPBasicAuth(access_token, '')
    print(response)
    # Check for errors in the response
    if response.status_code == 201 and volume > 0:
        # of.to_csv_log('trade',instrument, volume, price , take_profit, stop_loss, success_confidence )
        print(f'Buying {instrument} at {price}. Success confidence: {success_confidence} SL: {stop_loss} & TP: {take_profit}')
    elif response.status_code == 201 and volume < 0:
        # of.to_csv_log('trade',instrument, volume ,price , take_profit, stop_loss, success_confidence )
        print(f'Selling {instrument} at {price}. Success confidence: {success_confidence} SL: {stop_loss} & TP: {take_profit}')
    else:
        # of.to_csv_log('trade error',instrument, volume ,price , format(response.status_code), format(response.text)  )
        print(">>> Error placing order. Status code: {}, Response: {}".format(response.status_code, response.text))


def is_forex_market_open(environment, instrument):
# is_forex_market_open('EUR_USD')
    base_url, credentials_file_name, account_id, access_token = get_environmental_parameters(environment)
    endpoint = f'{base_url}/v3/accounts/{account_id}/pricing'
    headers = {'Authorization': f'Bearer {access_token}'}
    params = {'instruments': instrument} 
    
    response = requests.get(endpoint, headers=headers, params=params)
    
    if response.status_code == 200:
        data = json.loads(response.text)
        prices = data.get('prices', [])
        
        if prices:     
            timestamp = pd.to_datetime(prices[0]['time'][:-1]).strftime('%Y-%m-%d %H:%M:%S')
            market_status = prices[0]['status']
            print(f'{instrument} - Market Time: {timestamp}, Market Status: {market_status}')         
            return market_status == 'tradeable'   
        else:
            print('No pricing data available.')  
            return False
    else:
        print(f'Error: {response.status_code}, {response.text}')
        return False
    
def get_ask_price(environment, pair_name): #get_ask_price('BTC_USD')
# OANDA API V20 endpoint for getting pricing information
    base_url, credentials_file_name, account_id, access_token = get_environmental_parameters(environment)
    endpoint = f'{base_url}/v3/accounts/{account_id}/pricing'
    # Set the headers
    headers = {
        "Authorization": f'Bearer {access_token}',
    }
    # Specify the query parameters
    params = {
        "instruments": pair_name,
        "snapshot": "true",
    }
    # Make the API request to get pricing information
    response = requests.get(endpoint, headers=headers, params=params)
    # Check for errors in the response
    if response.status_code == 200:
        data = response.json()
        ask_price = data['prices'][0]['asks'][0]['price']
        # print(f'>>> Ask Price for {pair_name}: {ask_price}')
    else:
        print(f'Error getting ask price. Status code: {response.status_code}, Response: {response.text}')  
    return round(float(ask_price),5)

def get_bid_price(environment, pair_name): # get_bid_price('USD_JPY')
# OANDA API V20 endpoint for getting pricing information
    base_url, credentials_file_name, account_id, access_token = get_environmental_parameters(environment)
    endpoint = f'{base_url}/v3/accounts/{account_id}/pricing'
    # Set the headers
    headers = {"Authorization": f'Bearer {access_token}'}
    # Specify the query parameters
    params = {
        "instruments": pair_name,
        "snapshot": "true"}
    # Make the API request to get pricing information
    response = requests.get(endpoint, headers=headers, params=params)
    # Check for errors in the response
    if response.status_code == 200:
        data = response.json()
        bid_price = data['prices'][0]['bids'][0]['price']
        # print(f'>>> Ask Price for {pair_name}: {ask_price}')
    else:
        print(f'Error getting ask price. Status code: {response.status_code}, Response: {response.text}')  
    return round(float(bid_price),5)

# get_latest_OANDA_date(instrument='AUD_CAD')
def get_latest_OANDA_date(environment, instrument, max_attempts=3, retry_delay=1):
    base_url, credentials_file_name, account_id, access_token = get_environmental_parameters(environment)
    URL = f'{base_url}/v3/instruments/'
    path = f"{URL}{instrument}/candles"
    headers = {"Authorization": f"Bearer {access_token}"}
    params = {
        "granularity": 'H1',
        "price": "A",
        "count": 2  # Get last 2 candles to ensure we have at least one complete
    }
    
    for attempt in range(1, max_attempts + 1):
        try:
            response = requests.get(path, headers=headers, params=params, timeout=10)
            response.raise_for_status()  # Raise exception for HTTP errors
            
            data = response.json()
            
            # Check if response contains candles
            if 'candles' not in data or not data['candles']:
                print(f"Attempt {attempt}: No candles found in response for {instrument}")
                continue
                
            # Convert to DataFrame and filter complete candles
            candles_df = pd.json_normalize(data, record_path='candles')
            complete_candles = candles_df[candles_df['complete'] == True]
            
            if complete_candles.empty:
                print(f"Attempt {attempt}: No complete candles found for {instrument}")
                continue
                
            # Get the latest complete candle
            latest_date = complete_candles['time'].max()
            latest_date_formatted = pd.to_datetime(latest_date).strftime('%Y-%m-%d %H:%M:%S')
            
            if latest_date_formatted:
                # print(f"Successfully retrieved latest date from OANDA: {latest_date_formatted}")
                return latest_date_formatted
                
        except requests.exceptions.RequestException as e:
            print(f"Attempt {attempt}: Request failed for {instrument} - {type(e).__name__}: {e}")
        except KeyError as e:
            print(f"Attempt {attempt}: Key error in response data for {instrument} - {e}")
        except ValueError as e:
            print(f"Attempt {attempt}: JSON decode error for {instrument} - {e}")
        except Exception as e:
            print(f"Attempt {attempt}: Unexpected error for {instrument} - {type(e).__name__}: {e}")
        
        # Wait before retrying (except on last attempt)
        if attempt < max_attempts:
            time.sleep(retry_delay)
    
    print(f"All {max_attempts} attempts failed for {instrument}")
    return None

def close_all_trades(environment):
    base_url, credentials_file_name, account_id, access_token = get_environmental_parameters(environment)
    # OANDA API endpoint for getting open trades
    open_trades_endpoint = f'{base_url}/v3/accounts/{account_id}/openTrades'

    # OANDA API endpoint for closing all open trades
    close_trades_endpoint = f'{base_url}/v3/accounts/{account_id}/trades'

    # Headers with authorization
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }

    # Get a list of all open trades
    response = requests.get(open_trades_endpoint, headers=headers)
    response.raise_for_status()
    open_trades = response.json()["trades"]

    # Close each open trade
    for trade in open_trades:
        trade_id = trade["id"]
        
        # Close the trade
        close_trade_data = {
            "units": "ALL"  # Close all units
        }

        close_trade_endpoint = f"{close_trades_endpoint}/{trade_id}/close"
        close_response = requests.put(close_trade_endpoint, json=close_trade_data, headers=headers)
        close_response.raise_for_status()

        print(f"{environment} | Trade {trade_id} closed.")

    print(f"{environment} | All open trades closed.")

def get_balance(environment):
    base_url, credentials_file_name, account_id, access_token = get_environmental_parameters(environment)
    # OANDA API endpoint for account summary
    summary_endpoint = f"{base_url}/v3/accounts/{account_id}/summary"

    # Headers with authorization
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }

    # Make the request to get account summary
    response = requests.get(summary_endpoint, headers=headers)
    response.raise_for_status()

    # Parse the response to get realized P/L
    summary_data = response.json()["account"]
    balance = summary_data["balance"]
    balance = int(float(balance))
    return balance

def get_table(environment, price):     
    from helpers.others import get_utc_and_local_time, adjust_JPY_pairs, adjust_volume
    
    try:
        base_folder = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    except NameError:
        base_folder = os.getcwd()
        
        
    start_time = time.time()
    utc_time, local_time, _ = get_utc_and_local_time()    
    print(f'\n---> Starting process: get_updated_table() - UTC:{utc_time} (LT:{local_time}) ')
    # read instruments list
    instruments_folder = f'{base_folder}\\files'   
    
    
    instruments_file_name = 'derivatives_list.csv'
    instrument_list = pd.read_csv(f'{instruments_folder}/{instruments_file_name}',header=None).values.flatten().tolist()
    # latest_sql_date = ms.get_latest_sql_date('ForexAskH1_Stg')
    current_utc_datetime = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')
    current_utc_datetime = pd.to_datetime(current_utc_datetime)
    from_date = current_utc_datetime - timedelta(hours=1)
    from_date = from_date.strftime('%Y-%m-%dT%H:%M:%SZ')
    
    # initializing variables
    new_rows = pd.DataFrame()
    
    # main run
    print('> Fetching new data from OANDA.')
    for instrument in instrument_list:
        
        # get latest-candle date
        latest_candle = get_candle_from_to(environment= environment, 
                                           instrument=instrument, 
                                           granularity='H1',
                                           from_date=from_date,
                                           price_type= price)
        
        # normalize json to pandas
        new_pair_name = latest_candle["instrument"][:3] + latest_candle["instrument"][-3:]
        new_pair = pd.json_normalize(latest_candle, record_path= 'candles')
          
        new_pair = new_pair.drop(['complete'], axis=1)
    
        # poner tiempo en el formato correcto
        new_pair['time'] = new_pair['time'].apply(lambda x: pd.to_datetime(x).strftime('%Y-%m-%d %H:%M:%S'))
    
        # cambiar el ordern de las columnas
        new_order_columns = ['time','ask.o', 'ask.h', 'ask.l', 'ask.c', 'volume']
        new_pair = new_pair[new_order_columns]
    
        # cambiar el nombre de las columnas.
        new_column_names = ['Datetime','Open_'+new_pair_name, 'High_'+new_pair_name, 'Low_'+new_pair_name, 'Close_'+new_pair_name, 'Volume_'+new_pair_name]
        new_pair.columns = new_column_names
    
        # poner el tiempo como indice
        new_pair.set_index('Datetime', inplace=True)
    
        # concat
        new_rows = pd.concat([new_rows, new_pair], axis=1)
        
    
    # prepare the data
    new_rows.index = pd.to_datetime(new_rows.index).astype('datetime64[s]')
    new_rows.sort_index()
    
    # concatenat new row and sql
    updated_table = new_rows.sort_index()
    print(f'> {new_rows.shape[0]} new candle/s capture from OANDA')
    
    # fill empty spaces with avg
    updated_table = updated_table.astype(float)
    updated_table = updated_table.fillna(updated_table.mean())
    
    # normalize JPY and adjust volume
    updated_table = adjust_JPY_pairs(updated_table)
    updated_table = adjust_volume(updated_table)
    
    end_time = time.time()
    elapsed_time = end_time - start_time
    print(f"<--- Process finished: get_updated_table() - Elapsed time: {round(elapsed_time)} seconds.\n")
    return updated_table, new_rows

def get_spread_points(environment, pair_name):
    base_url, credentials_file_name, account_id, access_token = get_environmental_parameters(environment)
    # OANDA API endpoint for getting pricing information
    endpoint = f'{base_url}/v3/accounts/{account_id}/pricing'
    # Set the headers
    headers = {
        "Authorization": f'Bearer {access_token}',
    }
    # Specify the query parameters
    params = {
        "instruments": pair_name,
        "snapshot": "true",
    }
    # Make the API request to get pricing information
    response = requests.get(endpoint, headers=headers, params=params)
    
    if response.status_code == 200:
        data = response.json()
        ask_price = float(data['prices'][0]['asks'][0]['price'])
        bid_price = float(data['prices'][0]['bids'][0]['price'])
        spread = ask_price - bid_price
        if 'JPY' in pair_name:
            spread_points = int(round(spread, 5) * 1000)
        else:
            spread_points = int(round(spread, 5) * 100000)
        return spread_points
    else:
        print(f'Error getting prices. Status code: {response.status_code}, Response: {response.text}')
        return None

def get_recent_candles(environment, instrument, price, count=14):
    base_url, credentials_file_name, account_id, access_token = get_environmental_parameters(environment)
    # get_recent_candles('AUD_CAD', 2)
    URL =  f'{base_url}/v3/instruments/{instrument}/candles'
    headers = {"Authorization": "Bearer " + access_token}
    params = {
        "granularity": 'H1',
        "count": count,
        "price": price
    }
    response = requests.get(URL, headers=headers, params=params)
    if response.status_code == 200:
        return response.json()
    else:
        print(f'Error {response.status_code}: {response.text}')
        return None

def get_trade_profit(environment, trade_id):
    base_url, credentials_file_name, account_id, access_token = get_environmental_parameters(environment)
    endpoint = f'{base_url}/v3/accounts/{account_id}/trades/{trade_id}'
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }

    response = requests.get(endpoint, headers=headers)

    if response.status_code == 200:
        data = response.json()
        trade = data.get("trade", {})
        # Check if the trade is closed (closedTime will be present if closed)
        if trade['state'] == 'CLOSED':
            realized_pl = float(trade.get("realizedPL", 0))
            return realized_pl
        else:
            return None  # Trade still open
    else:
        print(f"Error retrieving trade {trade_id}. Status code: {response.status_code}, Response: {response.text}")
        return None

def get_candle_at(environment, instrument, candle_datetime, price_type, granularity = 'H1' ):
  # get_candle_at('demo','AUD_USD',pd.to_datetime('2026-02-26 05:00:00.000').strftime('%Y-%m-%dT%H:%M:%SZ'),'B') 
    base_url, credentials_file_name, account_id, access_token = get_environmental_parameters(environment)
    
    dt_from = pd.to_datetime(candle_datetime)
    # dt_to   = dt_from + timedelta(hours=1)

    URL = f'{base_url}/v3/instruments/'
    path = f"{URL}{instrument}/candles"
    headers = {"Authorization": "Bearer " + access_token}

    params = {
        "granularity": granularity
        ,"price": price_type
        ,"from": dt_from.strftime('%Y-%m-%dT%H:%M:%SZ')
        # ,"to":   dt_to.strftime('%Y-%m-%dT%H:%M:%SZ')
    }

    response = requests.get(path, headers=headers, params=params)
    data = response.json()

    if data.get("candles"):
        return data["candles"][0]
    else:
        return None
    

def get_bid_ask(environment, instrument, delta_hours, price_type):

    """
    Returns bid and ask prices for the previous full hour candle.
    Example: now=10:01 → returns prices at 09:00:00
    """

    # 1. Current UTC time
    now_utc = datetime.now(timezone.utc)

    # 2. Truncate to current hour, then go back one hour
    calculated_time = now_utc.replace(minute=0, second=0, microsecond=0) - timedelta(hours=delta_hours)
    candle_time = calculated_time.strftime('%Y-%m-%dT%H:%M:%SZ')

    # 3. Fetch BID and ASK candles
    bid_candle = get_candle_at(
        environment = environment,
        instrument=instrument,
        candle_datetime=candle_time,
        price_type='B',
        granularity='H1'
    )

    ask_candle = get_candle_at(
        environment = environment,
        instrument=instrument,
        candle_datetime=candle_time,
        price_type='A',
        granularity='H1'
    )

    if bid_candle is None or ask_candle is None:
        return {
            "time": candle_time,
            "bid_close": float(0),
            "ask_close": float(0),
        }

    return {
        "time": candle_time,
        "bid_close": float(bid_candle["bid"][f'{price_type}']),
        "ask_close": float(ask_candle["ask"][f'{price_type}']),
    }



    
def place_entry_order_with_offset(environment, instrument, volume, 
                                  offset_points,  threshold, tp_points, sl_points, tag, 
                                  contrarian_direction_flag = False):
    base_url, credentials_file_name, account_id, access_token = get_environmental_parameters(environment)
    endpoint = f'{base_url}/v3/accounts/{account_id}/orders'
    headers = {
        "Content-Type": "application/json",
        "Authorization": f'Bearer {access_token}',
        "Accept-Datetime-Format": "RFC3339"
    }

    volume = -volume if contrarian_direction_flag else volume
    points_multiplier = 0.001 if 'JPY' in instrument else 0.00001    
    is_buy = volume > 0
    prices = get_bid_ask(environment, instrument, price_type = 'o', delta_hours = 0)  
    print(f'Entry_price calculated using {prices}')
    if is_buy:
        entry_price = prices["ask_close"] - offset_points * points_multiplier
        # exit_price = prices["bid_close"]    
        tp_price = entry_price + points_multiplier * tp_points
        sl_price = entry_price - points_multiplier * sl_points
    else:  # sell
        entry_price = prices["bid_close"] + offset_points * points_multiplier
        # exit_price = prices["ask_close"]        
        tp_price = entry_price - points_multiplier * tp_points
        sl_price = entry_price + points_multiplier * sl_points
        
    expiry_time = (
                datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)
            ).isoformat().replace('+00:00', 'Z')
    
    def fmt(price, instrument):
        return f"{price:.3f}" if "JPY" in instrument else f"{price:.5f}"
    
    entry_price = fmt(entry_price, instrument)
    tp_price    = fmt(tp_price, instrument)
    sl_price    = fmt(sl_price, instrument)
    comment     = f"({offset_points}-{tp_points}-{sl_points}-{threshold})"
    
    order_data = {
        "order": {
            "type": "LIMIT",
            "instrument": instrument,
            "units": str(volume),
            "price": entry_price,
            "timeInForce": "GTD",
            "gtdTime": expiry_time,
            "positionFill": "DEFAULT",
            "clientExtensions": {
              "tag": tag,
              "comment": comment
            },
            "takeProfitOnFill": {
                "price": tp_price
            },
            "stopLossOnFill": {
                "price": sl_price      
                }
            
        }
    }

    
    response = requests.post(endpoint, headers=headers, data=json.dumps(order_data))
    response_json = response.json()
    http_status_desc = response.reason

    
    order_id = None
    if "orderCreateTransaction" in response_json:
        order_id = response_json["orderCreateTransaction"].get("id")
    
    # Audit insert
    insert_order_audit(
        environment=environment,
        instrument=instrument,
        tag=tag,
        http_status=response.status_code,
        http_status_desc = http_status_desc,
        order_id=order_id,
        request_payload=order_data,
        response_payload=response_json
    )
    
    if response.status_code == 201 and order_id:
        print(f"Order ID: {order_id} |  LIMIT order placed: {'BUY' if is_buy else 'SELL'} {instrument} at {entry_price} | Strategy: {tag} - {comment} | Volume: {volume}")
        
        return order_id
    else:
        print(f"Order ID: {order_id} | Order failed. Status: {response.status_code}")
        return None
        

# place_entry_order_with_offset(environment = 'demo', instrument = 'EUR_USD', volume = 1000, 
#                                   offset_points = 300,  threshold = 0.99 , 
#                                   tp_points = 270, sl_points = 270, tag = 'test_remove', 
#                                   contrarian_direction_flag = False)




def get_open_trades(environment):
    base_url, credentials_file_name, account_id, access_token = get_environmental_parameters(environment)
    endpoint = f'{base_url}/v3/accounts/{account_id}/openTrades'
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }

    response = requests.get(endpoint, headers=headers)
    
    if response.status_code == 200:
        trades = response.json().get("trades", [])
        details = []

        for trade in trades:
            detail = {
                "instrument": trade.get("instrument"),
                "units": trade.get("currentUnits"),
                "price": trade.get("price"),
                "open_time": trade.get("openTime"),
                "trade_id": trade.get("id")
            }
            details.append(detail)

        return pd.DataFrame(details)
    else:
        print(f"Error retrieving open trades. Status code: {response.status_code}, Response: {response.text}")
        return pd.DataFrame()

def get_open_trades_with_created_time(environment):
    base_url, credentials_file_name, account_id, access_token = get_environmental_parameters(environment)
    trades_endpoint = f'{base_url}/v3/accounts/{account_id}/openTrades'
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }

    response = requests.get(trades_endpoint, headers=headers)
    if response.status_code != 200:
        print(f"Error: {response.status_code}, {response.text}")
        return pd.DataFrame()

    trades = response.json().get("trades", [])
    results = []

    for trade in trades:
        trade_id = trade.get("id")
        instrument = trade.get("instrument")
        units = trade.get("currentUnits")
        open_time = trade.get("openTime")
        order_id = trade.get("tradeOpenedByOrderID")  # 💡 This is key
        unrealizedPL = trade.get("unrealizedPL") 
        trade_price = trade.get("price") 
        
        create_time = None
        if order_id:
            order_endpoint = f'{base_url}/v3/accounts/{account_id}/orders/{order_id}'
            order_response = requests.get(order_endpoint, headers=headers)
            if order_response.status_code == 200:
                create_time = order_response.json().get("order", {}).get("createTime")
            else:
                print(f"Failed to fetch order {order_id}")

        results.append({
            "trade_id": trade_id,
            "instrument": instrument,
            "units": units,
            "create_time": create_time,
            "open_time": open_time,
            "unrealizedPL": unrealizedPL,
            "trade_price":trade_price
        })

    return pd.DataFrame(results)




def get_trade_fill_price(environment, trade_id):
    base_url, credentials_file_name, account_id, access_token = get_environmental_parameters(environment)
    endpoint =f'{base_url}/v3/accounts/{account_id}/trades/{trade_id}'
    headers = {"Authorization": f"Bearer {access_token}"}
    response = requests.get(endpoint, headers=headers, timeout=15)
    response.raise_for_status()
    data = response.json()
    return float(data["trade"]["price"])

def close_trade_id(environment, trade_id):
    base_url, credentials_file_name, account_id, access_token = get_environmental_parameters(environment)
    endpoint = f'{base_url}/v3/accounts/{account_id}/trades/{trade_id}/close'
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }
    payload = {"units": "ALL"}

    response = requests.put(endpoint, headers=headers, data=json.dumps(payload))
    if response.ok:
        print(f"Trade {trade_id} closed.")
        return response.json()
    else:
        print(f">>> Error closing trade {trade_id}. Status: {response.status_code} | {response.text}")
        return None

def update_SL_TP(environment, trade_id, SL, TP):
    base_url, credentials_file_name, account_id, access_token = get_environmental_parameters(environment)
    endpoint = f'{base_url}/v3/accounts/{account_id}/trades/{trade_id}/orders'
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }
    payload = {
        "takeProfit": {"price": str(TP)},
        "stopLoss": {"price": str(SL)}
    }

    response = requests.put(endpoint, headers=headers, data=json.dumps(payload))
    if response.ok:
        print(f"Trade {trade_id} updated. SL={SL}, TP={TP}")
        return response.json()
    else:
        print(f">>> Error updating trade {trade_id}. Status: {response.status_code} | {response.text}")
        return None

def get_all_open_trade_ids(environment):
    base_url, credentials_file_name, account_id, access_token = get_environmental_parameters(environment)
    endpoint = f'{base_url}/v3/accounts/{account_id}/openTrades'
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }

    response = requests.get(endpoint, headers=headers)
    
    if response.status_code == 200:
        trades = response.json().get("trades", [])
        results = []
        for trade in trades:
            sl = trade.get("stopLossOrder")
            tp = trade.get("takeProfitOrder")

            if sl is None or tp is None:  # only include trades missing SL or TP
                units = float(trade.get("currentUnits", 0))
                direction = "long" if units > 0 else ("short" if units < 0 else "flat")
                results.append({
                    "trade_id": trade.get("id"),
                    "pair": trade.get("instrument"),
                    "direction": direction
                })
        return results
    else:
        print(f">>> Error retrieving open trades. Status: {response.status_code}, {response.text}")
        return []

def round_price(instrument, price):
    if "JPY" in instrument:
        return round(price, 3)
    else:
        return round(price, 5)

# def gestionar_trade(environment, direction, pair_name, trade_id):   
#     from helpers.mssql import get_last_ATR
    
#     atr = get_last_ATR(pair_name)
#     if atr is None:
#         print(f">>> ATR not found for {pair_name}. Skipping trade {trade_id}")
#         return
#     else:
#         print(f'1/5 - Get Last ATR: {atr}')
    
     
#     trade_fill_price = get_trade_fill_price(environment, trade_id)
#     print(f'2/5 - Get Order Price: {trade_fill_price}')
    
     
#     if direction == 'long':
#         SL = round_price(pair_name, trade_fill_price - atr)
#         TP = round_price(pair_name, trade_fill_price + 2*atr)
#     else:
#         SL = round_price(pair_name,trade_fill_price + atr)
#         TP = round_price(pair_name,trade_fill_price - 2*atr)
#     print(f'3/5 - Calculate SL:{SL} and TP:{TP}')    
    
#     if direction == 'long':
#         current_price = get_ask_price(environment, pair_name)
#     else:
#         current_price = get_bid_price(environment, pair_name)
#     print(f'4/5 - Get Current Price{current_price}')
    
    
#     if direction == 'long':        
#         in_range = SL < current_price < TP
#         print(f'5/5 - {trade_id} in range?: {in_range}')
#         if in_range:
#             print(f'LONG trade: {current_price} is between SL={SL} and TP={TP}')
#             update_SL_TP(environment,trade_id, SL, TP)
#         else:
#             print(f'LONG trade: {current_price} outside SL–TP. Closing {trade_id}...')
#             close_trade_id(environment,trade_id)    
#     elif direction == 'short':        
#         in_range = TP < current_price < SL
#         print(f'5/5 - {trade_id} in range?: {in_range}')
#         if in_range:
#             print(f'SHORT trade: {current_price} is between TP={TP} and SL={SL}')
#             update_SL_TP(environment,trade_id, SL, TP)
#         else:
#             print(f'SHORT trade: {current_price} outside TP–SL. Closing {trade_id}...')
#             close_trade_id(environment,trade_id)
            
def get_order_and_trade_status(environment, order_id):
    base_url, credentials_file_name, account_id, access_token = get_environmental_parameters(environment)
    endpoint = f'{base_url}/v3/accounts/{account_id}/orders/{order_id}'
    headers = {"Authorization": f"Bearer {access_token}"}
    response = requests.get(endpoint, headers=headers)

    if response.status_code != 200:
        print(f"Error {response.status_code}: {response.text}")
        return None

    data = response.json().get("order", {})

    order_status = data.get("state")   # OANDA calls it 'state'
    trade_id = data.get("tradeOpenedID") or data.get("tradeReducedID") or data.get("tradeClosedID")
    trade_status = None
    profit = None

    if trade_id:  # check trade details only if trade exists
        trade_endpoint = f'{base_url}/v3/accounts/{account_id}/trades/{trade_id}'
        trade_resp = requests.get(trade_endpoint, headers=headers)
        if trade_resp.status_code == 200:
            trade_status = trade_resp.json().get("trade", {}).get("state")
            trade = trade_resp.json().get("trade", {})
            profit = trade.get("realizedPL") or trade.get("unrealizedPL")
            profit = float(profit) if profit is not None else None


    return {
        "order_id": order_id,
        "order_status": order_status,
        "trade_id": trade_id,
        "trade_status": trade_status,
        "profit":profit
    }            

def get_candle_from(environment, instrument, from_date, price_type):
    base_url, credentials_file_name, account_id, access_token = get_environmental_parameters(environment)
    # get_candle_from('BTC_USD', '2024-06-21T00:00:00Z')
    # get_candle_from('AUD_CAD', pd.to_datetime('2025-12-01 00:00:00.000').strftime('%Y-%m-%dT%H:%M:%SZ'))
    URL =  f'{base_url}/v3/instruments/'
    path = f"{URL}{instrument}/candles"
    headers ={"Authorization":"Bearer "+ access_token}
    params = {
        "granularity": 'H1',
        "price": price_type,
        "from": from_date
    }
    response = requests.get(path, headers=headers, params=params)
    latest_candle = response.json()
    return latest_candle



#     return latest_candle
def get_candle_from_to(
    environment, 
    instrument,
    from_date,
    price_type,
    to_date=None,
    granularity='H1'
):
    base_url, credentials_file_name, account_id, access_token = get_environmental_parameters(environment)
    URL = f'{base_url}/v3/instruments/'
    path = f"{URL}{instrument}/candles"
    headers = {"Authorization": "Bearer " + access_token}

    # print(f'pirce type: {price_type} -------- DELETE')
    params = {
        "granularity": granularity,
        "price": price_type,
        "from": from_date
    }

    if to_date is not None:
        params["to"] = to_date

    # retry up to 3 times
    for _ in range(5):
        response = requests.get(path, headers=headers, params=params)

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
  
def minutes_to_granularity(minutes):
    mapping = {1:'M1',5:'M5',10:'M10',15:'M15',30:'M30',60:'H1',240:'H4'}
    if minutes not in mapping:
        raise ValueError(f'Unsupported candle size: {minutes} minutes')
    return mapping[minutes]

def get_candle(environment, instrument, candle_datetime, candle_duration_minutes, side):
    """
    Fetches ONE candle from OANDA given:
    - instrument (e.g. 'AUD_CAD')
    - candle_datetime (string or datetime)
    - candle_duration_minutes (e.g. 10, 30, 60)
    - side: 'ASK', 'BID', or 'MID'
    
    Returns candle dict or None.
    """
    base_url, credentials_file_name, account_id, access_token = get_environmental_parameters(environment)
    granularity = minutes_to_granularity(candle_duration_minutes)

    dt_from = pd.to_datetime(candle_datetime)
    dt_to   = dt_from + pd.Timedelta(minutes=candle_duration_minutes) 

    URL = f'{base_url}/v3/instruments/'
    path = f"{URL}{instrument}/candles"
    headers = {"Authorization": "Bearer " + access_token}

    params = {
        "granularity": granularity,
        "price": side[0].upper(),  # A / B / M
        "from": dt_from.strftime('%Y-%m-%dT%H:%M:%SZ'),
        "to":   dt_to.strftime('%Y-%m-%dT%H:%M:%SZ')
    }
    # print(params)

    response = requests.get(path, headers=headers, params=params)
    data = response.json()

    candles = data.get("candles", [])
    return candles[0] if candles else None
       
def get_pending_orders(environment):
    base_url, credentials_file_name, account_id, access_token = get_environmental_parameters(environment)
    endpoint = f'{base_url}/v3/accounts/{account_id}/pendingOrders'
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }

    response = requests.get(endpoint, headers=headers)
    response.raise_for_status()

    orders = response.json().get("orders", [])
    details = []

    for order in orders:
        details.append({
            "id": order.get("id"),          # ✅ KEEP THIS
            "instrument": order.get("instrument"),
            "units": order.get("units"),
            "price": order.get("price"),
            "type": order.get("type"),
            "time": order.get("createTime"),
            "gtdTime": order.get("gtdTime", None),
        })

    return pd.DataFrame(details)
            
def cancel_all_pending_orders(environment):
    base_url, credentials_file_name, account_id, access_token = get_environmental_parameters(environment)
    df = get_pending_orders(environment)

    if df.empty:
        print("> No pending orders to cancel.")
        return

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }

    for _, row in df.iterrows():
        order_id = row["order_id"] if "order_id" in row else row["id"]

        cancel_endpoint = (
            f'{base_url}/v3/accounts/'
            f"{account_id}/orders/{order_id}/cancel"
        )

        resp = requests.put(cancel_endpoint, headers=headers)
        if resp.ok:
            print(f"🗑️ Pending order {order_id} cancelled.")
        else:
            print(f">>> Failed to cancel order {order_id}: {resp.text}")

def close_trades_after_hours(environment, max_hours):    
    # Closes all open trades that have been open for >= max_hours.
    # Uses existing helpers and naming from oanda.py
    
    df = get_open_trades_with_created_time(environment)
    
    if df.empty:
        print("> No open trades found.")
        return
    
    now_utc = datetime.now(timezone.utc)
    
    for _, row in df.iterrows():
        trade_id   = row["trade_id"]
        open_time  = row["open_time"]
    
        if open_time is None:
            continue
    
        open_time_dt = datetime.fromisoformat(open_time.replace("Z", "+00:00"))
        hours_open = (now_utc - open_time_dt).total_seconds() / 3600
    
        if hours_open >= max_hours:
            print(f"> Closing trade {trade_id} | Open for {hours_open:.2f} hours")
            close_trade_id(environment,trade_id)
            
def quote_to_aud_factor(quote_ccy, dt):
    from helpers.others import get_forex_pairs_list
    from helpers.mssql import get_data_from_sql 
    _pair_names = get_forex_pairs_list()
   
    if quote_ccy == 'AUD':
        return 1.0

    aud_quote = f'AUD_{quote_ccy}'
    quote_aud = f'{quote_ccy}_AUD'

    df = get_data_from_sql(
        table='[landing].[ForexMidH1]',
        calculation_date=dt,
        direction='='
    )

    if aud_quote in _pair_names:
        mid = float(df[f'Close_{aud_quote.replace("_","")}'].iloc[0])
        return 1 / mid

    elif quote_aud in _pair_names:
        mid = float(df[f'Close_{quote_aud.replace("_","")}'].iloc[0])
        return mid

    else:
        raise ValueError(f'No AUD cross for {quote_ccy}')

def get_quote_home_conversion_factor(
    order_currency,
    timestamp_utc
):
    base_ccy, quote_ccy = order_currency.split('_')

    dt = pd.to_datetime(timestamp_utc).round('h').strftime('%Y-%m-%d %H:%M:%S')

    try:
        return round(quote_to_aud_factor(quote_ccy, dt), 7)

    except Exception as e:
        print(f'order_currency = {order_currency}')
        print(f'timestamp_utc = {timestamp_utc}')
        print(f'Error: {e}')
        return 0


def get_all_orders(environment, count=500, state="ALL"):
    base_url, credentials_file_name, account_id, access_token = get_environmental_parameters(environment)

    endpoint = f'{base_url}/v3/accounts/{account_id}/orders'

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }

    params = {
        "count": count,
        "state": state   # OPEN, FILLED, CANCELLED, ALL
    }

    response = requests.get(endpoint, headers=headers, params=params)
    response.raise_for_status()

    orders = response.json().get("orders", [])

    if not orders:
        return pd.DataFrame()

    df = pd.json_normalize(orders)
    df = df.rename(columns=lambda c: c.replace('.', '_'))

    return df


def get_trade_details(environment, trade_id):
    base_url, _, account_id, access_token = get_environmental_parameters(environment)

    endpoint = f'{base_url}/v3/accounts/{account_id}/trades/{trade_id}'
    headers = {"Authorization": f"Bearer {access_token}"}

    response = requests.get(endpoint, headers=headers)
    response.raise_for_status()

    trade = response.json().get("trade", {})

    # if not trade:
    #     return pd.DataFrame()

    # df = pd.json_normalize(trade)
    # df = df.rename(columns=lambda c: c.replace('.', '_'))

    return trade        
            

def get_all_transactions(environment):
    base_url, credentials_file_name, account_id, access_token = get_environmental_parameters(environment)    
  
    url = f'{base_url}/v3/accounts/{account_id}/transactions?count=1'
    headers = {"Authorization": f"Bearer {access_token}"}

    r = requests.get(url, headers=headers)
    r.raise_for_status()

    pages = r.json().get("pages", [])
    all_transactions = []

    for page_url in pages:
        r_page = requests.get(page_url, headers=headers)
        r_page.raise_for_status()
        all_transactions.extend(r_page.json().get("transactions", []))

    return all_transactions


def get_new_transactions(environment, since_id):
    base_url, credentials_file_name, account_id, access_token = get_environmental_parameters(environment)

    url = f"{base_url}/v3/accounts/{account_id}/transactions/sinceid?id={since_id}"
    headers = {"Authorization": f"Bearer {access_token}"}

    r = requests.get(url, headers=headers)
    r.raise_for_status()
    return r.json().get("transactions", [])


def get_transaction(environment, transaction_id):
    base_url, _, account_id, access_token = get_environmental_parameters(environment)

    url = f"{base_url}/v3/accounts/{account_id}/transactions/{transaction_id}"
    headers = {"Authorization": f"Bearer {access_token}"}

    r = requests.get(url, headers=headers)
    r.raise_for_status()
    return r.json()


def is_forex_weekly_close_time():
    """
    Returns True if current time corresponds to
    Friday 17:00 New York time (within a safe window).
    """
    import pytz
    utc_now = datetime.now(timezone.utc)

    ny_tz = pytz.timezone("America/New_York")
    ny_now = utc_now.astimezone(ny_tz)

    # Friday check
    if ny_now.weekday() != 4:  # 4 = Friday
        return False

    # 16:55 – 17:05 NY safety window
    if (ny_now.hour == 16 and ny_now.minute >= 50) or \
       (ny_now.hour == 17 and ny_now.minute <= 00):
        return True

    return False


def close_open_trades_EOW():
    if is_forex_weekly_close_time():
        for env in ['live','demo']:
            close_all_trades(env)
    else:
        print('Forex Market Is Not At Closing Window')







