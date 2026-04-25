# libraries
import helpers.mssql as ms
from sklearn.model_selection import train_test_split
from ta.trend import EMAIndicator
import os, joblib
from sklearn.metrics import precision_score, recall_score, f1_score
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

# classes
class RandomModel:
    def fit(self, X, y):
        pass

    def predict_proba(self, X):
        probs = np.random.rand(len(X))
        return np.column_stack([1 - probs, probs])

# details        
direction = 'long'
print(f"\nRunning trainingModels(). Direction: {direction}")


# 1 - Obtaining X with normalized columns when required
print('1 - Obtaining X. Using normalized columns when required')
X = ms.get_table_from_sql(table_schema = 'landing', table_name='ForexMidH1')


# 2 - Preparacion: CatBoost no necesita normalizacion
X = X[['Close_EURUSD','Open_EURUSD','High_EURUSD','Low_EURUSD','Volume_EURUSD']]
X[['Close_EURUSD','Open_EURUSD','High_EURUSD','Low_EURUSD']] = X[['Close_EURUSD','Open_EURUSD','High_EURUSD','Low_EURUSD']]
X['Hour'] = X.index.hour                 
X['Day_of_Week'] = X.index.dayofweek    # Monday=0
X['Volume_EURUSD'] = X['Volume_EURUSD'] 
X['EMA_9'] = EMAIndicator(close=X['Close_EURUSD'], window=9).ema_indicator()
X['EMA_20'] = EMAIndicator(close=X['Close_EURUSD'], window=20).ema_indicator()
X['EMA_50'] = EMAIndicator(close=X['Close_EURUSD'], window=50).ema_indicator()
X['EMA_100'] = EMAIndicator(close=X['Close_EURUSD'], window=100).ema_indicator()
X['EMA_200'] = EMAIndicator(close=X['Close_EURUSD'], window=200).ema_indicator()
X_ready = X.iloc[200-1:]


# 3 - Defining y
lookahead_hours = 3
target_points = 100
point_size = 0.00001
target_move = target_points * point_size
currency = 'EURUSD'

if direction == "long":
    future_max = (
        X_ready['High_EURUSD']
        .shift(-1)
        .rolling(window=lookahead_hours)
        .max()
        .shift(-(lookahead_hours - 1))
    )
    X_ready['y'] = (future_max >= X_ready['Close_EURUSD'] + target_move).astype(int)

elif direction == "short":
    future_min = (
        X_ready['Low_EURUSD']
        .shift(-1)
        .rolling(window=lookahead_hours)
        .min()
        .shift(-(lookahead_hours - 1))
    )
    X_ready['y'] = (future_min <= X_ready['Close_EURUSD'] - target_move).astype(int)

X_ready = X_ready.iloc[:-lookahead_hours]

# Distribucion balanceada?
X_ready['y'].value_counts(normalize=True)


# 4 - Defining the list of binary models to evaluate
print('2.Define models and fine-tuned variations')
from xgboost import XGBClassifier
np.random.seed(0)
models = [
   (XGBClassifier(n_estimators=500, max_depth=6, learning_rate=0.05, random_state=0), "XGB (500 trees)"),
   (RandomModel(), "Random Model")
]

results = []
thresholds = [0.55, 0.575, 0.6, 0.625, 0.65, 0.675, 0.7, 0.725, 0.75, 0.775, 0.8]

for model, model_name in models:
    print(f'Training {model_name}')

    X_ready = X_ready.sort_index()
    df = X_ready.drop(columns=['y'])
    y = X_ready['y']   

    # Split (time-based)
    x_aux, x_test, y_aux, y_test = train_test_split(df, y, test_size=0.2, shuffle=False)
    x_train, x_val, y_train, y_val = train_test_split(x_aux, y_aux, test_size=0.2, shuffle=False)

    # Train
    model.fit(x_train, y_train)

    # Probabilities
    y_prob_train = model.predict_proba(x_train)[:, 1]
    y_prob_val   = model.predict_proba(x_val)[:, 1]
    y_prob_test  = model.predict_proba(x_test)[:, 1]
    
    for threshold in thresholds:
        # Thresholded predictions
        y_pred_train = (y_prob_train > threshold).astype(int)
        y_pred_val   = (y_prob_val > threshold).astype(int)
        y_pred_test  = (y_prob_test > threshold).astype(int)
        n_trades = y_pred_test.sum()
    
        # Metrics
        row = {
            "model": model_name,
            "threshold":threshold,
            "n_trades":n_trades,
    
            # Class 1 focus (important)
            "val_precision_1": precision_score(y_val, y_pred_val, pos_label=1, zero_division=0),
            "val_recall_1": recall_score(y_val, y_pred_val, pos_label=1),
            "val_f1_1": f1_score(y_val, y_pred_val, pos_label=1),
    
            "test_precision_1": precision_score(y_test, y_pred_test, pos_label=1, zero_division=0),
            "test_recall_1": recall_score(y_test, y_pred_test, pos_label=1),
            "test_f1_1": f1_score(y_test, y_pred_test, pos_label=1),
        }
    
        results.append(row)

    # Save model
    os.makedirs(f"models/{direction}", exist_ok=True)
    filename = f"models/{direction}/{model_name}_{currency}.pkl"
    joblib.dump(model, filename)


results_df = pd.DataFrame(results).sort_values(by="test_f1_1", ascending=False)
results_df
        
        
        
# 5 - plotting
pivot = results_df.pivot(index="threshold", columns="model", values="test_precision_1")
pivot.plot(marker='o')
plt.title("Test - Precision vs Threshold")
plt.ylabel("Precision (class 1)")
plt.grid()
plt.show()      

pivot = results_df.pivot(index="threshold", columns="model", values="test_recall_1")
pivot.plot(marker='o')
plt.title("Test - Recall vs Threshold")
plt.ylabel("Recall (class 1)")
plt.grid()
plt.show()

for model in results_df["model"].unique():
    df = results_df[results_df["model"] == model]
    plt.plot(df["n_trades"], df["test_precision_1"], marker='o', label=model)
plt.xlabel("Test - Number of Trades")
plt.ylabel("Precision")
plt.title("Precision vs Trades")
plt.legend()
plt.grid()
plt.show()

















# from catboost import CatBoostClassifier # !pip install numpy==1.23.5 catboost==1.2
# from sklearn.ensemble import RandomForestClassifier        


   # (CatBoostClassifier(verbose=0, depth=6, random_seed=27), "CatBoost (depth=6)"),
   # (CatBoostClassifier(verbose=0, iterations=500), "CatBoost (500)"),
   # (RandomForestClassifier(n_estimators=500, max_depth=30, random_state=0), "RF (500 trees, max_depth=30)"),
