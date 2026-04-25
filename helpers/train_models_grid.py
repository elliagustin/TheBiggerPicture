import pandas as pd
import OOP.helpers.mssql as ms
import others as o
from sklearn.model_selection import train_test_split
from sklearn.metrics import precision_score
from sklearn.metrics import confusion_matrix, roc_curve, auc
from sklearn.ensemble import RandomForestClassifier
from sklearn.neural_network import MLPClassifier
from catboost import CatBoostClassifier # !pip install numpy==1.23.5 catboost==1.2
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.tree import DecisionTreeClassifier
from sklearn.svm import SVC
import itertools,os,joblib

######################### 1 - Define Parameters
print('\n1.Reading main parameters')
smoothing_strength = [2,3,4,5]
y_horizon = [2,3,4,5]
model_thresholds = [0.7,0.75,0.8]
directions = ["long","short"]
cutoff = pd.Timestamp('2025-07-31 00:00:00') 


######################### 2- Obtaining X with normalized columns when required
print('2. Defining y & X functions')

def get_X():
    X = ms.get_table_from_sql(table_name = 'RSI_1H', table_schema='staging')
    
    #adding hour and week day
    X['Hour'] = X.index.hour *10                # For normalization Purposes
    X['Day_of_Week'] = X.index.dayofweek *10    # Monday=0, Sunday=6
    
    # Agregarle el volumen a X
    _Vol = ms.get_all_table('[staging].[Vw_Vol]').sort_index() /100 
    _Vol = _Vol.fillna(_Vol.mean())
    
    # merge all together
    X = X.merge(_Vol, left_index=True, right_index=True)
    
    # # Adhitions
    # ATR = ms.get_all_table('[dbo].[Vw_ATR14_ForexPairs]').sort_index() 
    
    # X = X.reset_index().merge(
    #     ATR.reset_index(),
    #     on=["Datetime", "Pair"],
    #     how="left"
    # ).set_index("Datetime")
    return X

# new function for y
def get_y(rsi, direction = 'long', smoothing_strength = 2, y_horizon = 5):
    # Data in order
    df = pd.DataFrame({'RSI': rsi})
    
    # Rolling average
    avg = df['RSI'].rolling(smoothing_strength, min_periods=smoothing_strength).mean()
    
    # Build future shifts, require ALL future horizons to exist (Excel-style)
    shifts = pd.concat([avg.shift(-h) for h in range(1, y_horizon+1)], axis=1)

    # Split based on the direction
    if direction == 'long':
        # Get the max & valid rows
        future_max = shifts.max(axis=1)
        valid = avg.notna() & shifts.notna().all(axis=1)
        
        # y = MAX(next y_horizon avgs) > current avg
        y = (future_max > avg).where(valid)
        
        # Drop Na
        out = df.assign(AVG=avg, y=y).dropna(subset=['y'])
    elif direction == 'short':
        # Get the max & valid rows
        future_min = shifts.min(axis=1)        
        valid = avg.notna() & shifts.notna().all(axis=1)
        
        # y = MIN(next y_horizon avgs) > current avg
        y = (future_min < avg).where(valid)
        
        # Drop Na
        out = df.assign(AVG=avg, y=y).dropna(subset=['y'])       
        
    return out['y'].astype(int)  



# ######################### 3 - Defining the list of binary models to evaluate
# print('3.Define models and fine-tuned variations')

# models = [
#     # (CatBoostClassifier(verbose=0, depth=6), "CatBoost (depth=6)")
#     # ,(CatBoostClassifier(verbose=0, depth=8), "CatBoost (depth=8)")
#     # ,(CatBoostClassifier(verbose=0, iterations=500), "CatBoost (500 iterations)")
    
#     (CatBoostClassifier(verbose=0, depth=4, iterations=300, learning_rate=0.05), "CatBoost (depth=4, iter=300, lr=0.05)")
#     ,(CatBoostClassifier(verbose=0, depth=6, iterations=500, learning_rate=0.1),  "CatBoost (depth=6, iter=500, lr=0.1)")
#     ,(CatBoostClassifier(verbose=0, depth=8, iterations=1000, learning_rate=0.05), "CatBoost (depth=8, iter=1000, lr=0.05)")
#     ,(CatBoostClassifier(verbose=0, depth=10, iterations=200, learning_rate=0.2),  "CatBoost (depth=10, iter=200, lr=0.2)")
#     ,(CatBoostClassifier(verbose=0, depth=6, iterations=100, learning_rate=0.03),  "CatBoost (depth=6, iter=100, lr=0.03)")
#     ,(CatBoostClassifier(verbose=0, depth=5, iterations=700, learning_rate=0.07),  "CatBoost (depth=5, iter=700, lr=0.07)")
#     ,(CatBoostClassifier(verbose=0, depth=7, iterations=500, learning_rate=0.15),  "CatBoost (depth=7, iter=500, lr=0.15)")
#     ,(CatBoostClassifier(verbose=0, depth=3, iterations=300, learning_rate=0.1),   "CatBoost (depth=3, iter=300, lr=0.1)")
#     ,(CatBoostClassifier(verbose=0, depth=9, iterations=800, learning_rate=0.05),  "CatBoost (depth=9, iter=800, lr=0.05)")
#     ,(CatBoostClassifier(verbose=0, depth=6, iterations=600, learning_rate=0.08),  "CatBoost (depth=6, iter=600, lr=0.08)")

#     # # Random Forest variations
#     # (RandomForestClassifier(n_estimators=250, max_depth=30, random_state=0), "Random Forest (250 trees, max_depth=30)"),
#     # (RandomForestClassifier(n_estimators=500, max_depth=30, random_state=0), "Random Forest (500 trees, max_depth=30)"),
#     # (RandomForestClassifier(n_estimators=750, max_depth=20, min_samples_split=5, random_state=0), "Random Forest (750 trees, max_depth=20, min_samples_split=5)"),
#     # (RandomForestClassifier(n_estimators=1000, min_samples_leaf=3, random_state=0), "Random Forest (1000 trees, min_samples_leaf=3)"),

#     # # Decision Tree variations
#     # (DecisionTreeClassifier(max_depth=20, min_samples_split=5, random_state=0), "Decision Tree (max_depth=20, min_samples_split=5)"),
#     # (DecisionTreeClassifier(max_depth=30, min_samples_leaf=2, random_state=0), "Decision Tree (max_depth=30, min_samples_leaf=2)"),

#     # # Support Vector Classifier (RBF Kernel) variations
#     # (SVC(kernel="rbf", C=1, gamma="scale", probability=True), "SVC (RBF, C=1)"),
#     # (SVC(kernel="rbf", C=5, gamma="scale", probability=True), "SVC (RBF, C=5)"),
#     # (SVC(kernel="rbf", C=10, gamma="auto", probability=True), "SVC (RBF, C=10, gamma=auto)")

# ]


# ######################### 4.Loop over all currency pairs
# print('4.Loop over all currency pairs')
# # initialize to store results
# results = []

# # Validation
# for direction in directions:
#     #Lopp over the models
#     for model, model_name in models:        
#         print(f'\nModel:{model_name}')
#         for s, yh in itertools.product(smoothing_strength, y_horizon):
#             # Get X
#             X = get_X()
            
#             # Get targets
#             _AUD = get_y(X['AUD'], direction ,s , yh )
#             _EUR = get_y(X['EUR'], direction ,s , yh )
#             _USD = get_y(X['USD'], direction ,s , yh )
#             _CAD = get_y(X['CAD'], direction ,s , yh )
#             _GBP = get_y(X['GBP'], direction ,s , yh )
#             _JPY = get_y(X['JPY'], direction ,s , yh )
#             _NZD = get_y(X['NZD'], direction ,s , yh )
#             _CHF = get_y(X['CHF'], direction ,s , yh )
        
#             # Create targets dict    
#             targets = {'EUR': _EUR,'USD': _USD,'AUD': _AUD,'CAD': _CAD,'GBP': _GBP,'JPY': _JPY,'NZD': _NZD,'CHF': _CHF}
        
#             # Adjust X to match targets
#             X = X.join(_EUR, how='inner')
    
#             for threshold in model_thresholds:        
#                 threshold_precision = 0
#                 threshold_entries = 0
#                 for currency, dataframe in targets.items():
#                     # #for testing
#                     # if currency != 'AUD':
#                     #     continue
                    
#                     # obtengo y
#                     y = targets[currency] # currency = 'AUD'
                    
#                     #order
#                     X.sort_index()
#                     y.sort_index()
                    
#                     # Cutoff
#                     X = X[X.index < cutoff]
#                     y = y[y.index < cutoff]
                
#                     # Split the data
#                     x_aux, x_test, y_aux, y_test = train_test_split(X, y, test_size=0.2, random_state=0, shuffle=True)
#                     x_train, x_val, y_train, y_val = train_test_split(x_aux, y_aux, test_size=0.1/0.8, random_state=0, shuffle=True)
                    
#                     # Get the weeks amount
#                     weeks = x_val.index.to_series().dt.isocalendar().week.nunique()
                    
#                     # Fit the model
#                     model.fit(x_train, y_train)
                    
                    
#                     # y_pred = model.predict(X_test)
#                     y_val_proba = model.predict_proba(x_val)[:, 1]
#                     y_val_pred = (y_val_proba >= threshold).astype(int)  
                      
#                     #precision calculation
#                     precision = precision_score(y_val, y_val_pred, zero_division=0)
                    
#                     # other calculations
#                     entries = sum(y_val_pred)
#                     # threshold_precision = threshold_precision + ( precision * entries)
#                     # threshold_entries = threshold_entries + entries
                    
#                     # Define class ratio
#                     positive_ratio = y.mean()
                   
#                     # Store results
#                     results.append({
#                         "Direction":direction,
#                         "Smoothing Strength": s,
#                         "Y Horizon": yh,
#                         "Model": model_name,
#                         "model_threshold":threshold,
#                         "currency":currency,
#                         "Class 1 Ratio": f"{positive_ratio:.2%}",
#                         "Entries": sum(y_val_pred),
#                         "Precision": f"{precision:.2%}"
#                     })
#                     print(f'{direction}, Model: {model_name},SS: {s}, YH: {yh}, model_threshold: {threshold}, currency: {currency}, Class 1 Ratio: {positive_ratio:.2%}, Entries: {sum(y_val_pred)}, Precision: {precision:.2%}')
                    
# df_results = pd.DataFrame(results)
# print(df_results)  # Shows the last added row

# df_results.to_csv()


######################### 6.Evaluating selected models/parameters against test dataset
print('6.Test - Evaluating selected models/parameters against Test Dataset')


save_models_to_disk = True

selected_params = [
   # (CatBoostClassifier(verbose=0, depth=4, iterations=300, learning_rate=0.05), "CatBoost (depth=4)", 'long',2,2,0.75),
   # (CatBoostClassifier(verbose=0, depth=4, iterations=300, learning_rate=0.05), "CatBoost (depth=4)", 'long',3,2,0.75),
   # (CatBoostClassifier(verbose=0, depth=4, iterations=300, learning_rate=0.05), "CatBoost (depth=4)", 'long',4,2,0.75),
   # (CatBoostClassifier(verbose=0, depth=4, iterations=300, learning_rate=0.05), "CatBoost (depth=4)", 'long',5,2,0.75),
   
   # (CatBoostClassifier(verbose=0, depth=4, iterations=300, learning_rate=0.05), "CatBoost (depth=4)", 'long',2,3,0.75),
   # (CatBoostClassifier(verbose=0, depth=4, iterations=300, learning_rate=0.05), "CatBoost (depth=4)", 'long',3,3,0.75),
   # (CatBoostClassifier(verbose=0, depth=4, iterations=300, learning_rate=0.05), "CatBoost (depth=4)", 'long',4,3,0.75),
   # (CatBoostClassifier(verbose=0, depth=4, iterations=300, learning_rate=0.05), "CatBoost (depth=4)", 'long',5,3,0.75),
   
   # (CatBoostClassifier(verbose=0, depth=4, iterations=300, learning_rate=0.05), "CatBoost (depth=4)", 'long',2,4,0.75),
   # (CatBoostClassifier(verbose=0, depth=4, iterations=300, learning_rate=0.05), "CatBoost (depth=4)", 'long',3,4,0.75),
   # (CatBoostClassifier(verbose=0, depth=4, iterations=300, learning_rate=0.05), "CatBoost (depth=4)", 'long',4,4,0.75),
   # (CatBoostClassifier(verbose=0, depth=4, iterations=300, learning_rate=0.05), "CatBoost (depth=4)", 'long',5,4,0.75),
   
    (CatBoostClassifier(verbose=0, depth=4, iterations=300, learning_rate=0.05), "CatBoost (depth=4)", 'long',2,5,0.75),
    (CatBoostClassifier(verbose=0, depth=4, iterations=300, learning_rate=0.05), "CatBoost (depth=4)", 'short',2,5,0.75),
   # (CatBoostClassifier(verbose=0, depth=4, iterations=300, learning_rate=0.05), "CatBoost (depth=4)", 'long',3,5,0.75),
   # (CatBoostClassifier(verbose=0, depth=4, iterations=300, learning_rate=0.05), "CatBoost (depth=4)", 'long',4,5,0.75),
   # (CatBoostClassifier(verbose=0, depth=4, iterations=300, learning_rate=0.05), "CatBoost (depth=4)", 'long',5,5,0.75),
    ]

# Start metrics
test_precision = 0
test_entries = 0
test_results = []

for model, model_name, direction,s, yh, model_threshold in selected_params:
    # Get X
    X = get_X()
    
    # Get targets
    _AUD = get_y(X['AUD'], direction,s , yh )
    _EUR = get_y(X['EUR'], direction,s , yh )
    _USD = get_y(X['USD'], direction,s , yh )
    _CAD = get_y(X['CAD'], direction,s , yh )
    _GBP = get_y(X['GBP'], direction,s , yh )
    _JPY = get_y(X['JPY'], direction,s , yh )
    _NZD = get_y(X['NZD'], direction,s , yh )
    _CHF = get_y(X['CHF'], direction,s , yh )

    # Create targets dict    
    targets = {'EUR': _EUR,'USD': _USD,'AUD': _AUD,'CAD': _CAD,'GBP': _GBP,'JPY': _JPY,'NZD': _NZD,'CHF': _CHF}

    # Adjust X to match targets
    # X = X.join(_EUR, how='inner')
    X = X.loc[_EUR.index.min():_EUR.index.max()]
    
    # Loop over currencies
    for currency, dataframe in targets.items(): 
        # #for testing
        # if currency != 'AUD':
        #     continue
        
        # Get y
        y = targets[currency]
        
        # Order them
        X.sort_index()
        y.sort_index()
        
        # Cutoff
        X = X[X.index < cutoff]
        y = y[y.index < cutoff]
    
        # Split 
        x_aux, x_test, y_aux, y_test = train_test_split(X, y, test_size=0.2, random_state=0, shuffle=True)
        x_train, x_val, y_train, y_val = train_test_split(x_aux, y_aux, test_size=0.1/0.8, random_state=0, shuffle=True)
         
        # Train the model
        model.fit(x_train, y_train)
        
        
        if save_models_to_disk:          
            # Ensure a folder exists
            os.makedirs("models", exist_ok=True)
            
            # Construct a unique filename
            filename = f"models/{direction}/{model_name}_{currency}.pkl"
            
            # Save model
            joblib.dump(model, filename)

            # print
            print(f'{filename} saved.')        
        
        
        # Get test_pred
        y_test_proba = model.predict_proba(x_test)[:, 1]
        y_test_pred = (y_test_proba >= model_threshold).astype(int)  
      
        #precision calculation
        test_precision = precision_score(y_test, y_test_pred, zero_division=0)
        
        # other calculations
        test_entries = sum(y_test_pred)       
    
        # Define class ratio
        test_positive_ratio = y.mean()
        
        # Store results
        test_results.append({
            "Direction": direction,
            "Smoothing Strength": s,
            "Y Horizon": yh,
            "Model": model_name,
            "model_threshold":model_threshold,
            "currency":currency,
            "Class 1 Ratio": f"{test_positive_ratio:.2%}",
            "Entries": test_entries,            
            "Precision": f"{test_precision:.2%}"
        })
        print(f'{direction}, Model: {model_name},SS: {s}, YH: {yh}, model_threshold: {model_threshold}, currency: {currency}, Class 1 Ratio: {test_positive_ratio:.2%}, Entries: {test_entries}, Precision: {test_precision:.2%}')


df_test_results = pd.DataFrame(test_results)
print(f'\n{df_test_results}') 
