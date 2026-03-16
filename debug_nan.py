import pandas as pd
from feature_engineering import build_features, ensure_stationarity
from data_fetcher import fetch_historical_data

data = fetch_historical_data('XRPUSDT', interval='15m', start_str='3 years ago UTC', max_retries=1)
print(f'Initial data length: {len(data)}')

df_feat = data.copy()
# I'll just run build_features and see if it returns 0 rows
df_feat = build_features(df_feat)
print(f'After build_features length: {len(df_feat)}')

if len(df_feat) == 0:
    # let's run build_features without dropna
    df_feat = data.copy()
    # paste the inner logic of build_features to debug
    # but actually I can just run it line by line or import and monkey patch
