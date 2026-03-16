import pandas as pd
import sys
sys.path.append('/home/jeong-kihun/.openclaw/workspace/Binance_Signal_Predictor')
from feature_engineering import build_features, ensure_stationarity
from data_fetcher import fetch_historical_data

data = fetch_historical_data('XRPUSDT', interval='15m', start_str='3 years ago UTC', max_retries=1)
print(f'Original data len: {len(data)}')

df = build_features(data)
print(f'After build_features len: {len(df)}')
if len(df) == 0:
    print('Checking which feature caused all NaNs in build_features before dropna...')
    import inspect
    source = inspect.getsource(build_features)
    # We will just manually recreate the steps to find the culprit
    df_test = data.copy()
    
df_stat = ensure_stationarity(df)
print(f'After ensure_stationarity len: {len(df_stat)}')
if len(df_stat) == 0:
    print('Checking ensure_stationarity for NaNs...')
    df_test = df.copy()
    for col in df_test.select_dtypes(include=[float, int]).columns:
        if col == 'target': continue
        try:
            from statsmodels.tsa.stattools import adfuller
            p = adfuller(df_test[col].dropna())[1]
            if p > 0.05:
                df_test[col] = df_test[col].pct_change()
        except:
            df_test[col] = df_test[col].pct_change()
    
    nan_counts = df_test.isna().sum()
    print('NaN counts after pct_change:')
    print(nan_counts[nan_counts > 0].sort_values(ascending=False))
