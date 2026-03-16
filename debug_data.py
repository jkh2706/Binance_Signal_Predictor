import pandas as pd
from feature_engineering import build_features, ensure_stationarity
from train_xrp_v3 import label_triple_barrier
from data_fetcher import fetch_historical_data

print('Fetching data...')
data = fetch_historical_data('XRPUSDT', interval='15m', start_str='3 years ago UTC', max_retries=1)
print(f'Initial data shape: {data.shape}')

if not data.empty:
    print('Building features...')
    df_feat = build_features(data)
    print(f'After build_features: {df_feat.shape}')
    
    print('Ensuring stationarity...')
    df_stat = ensure_stationarity(df_feat)
    print(f'After ensure_stationarity: {df_stat.shape}')
    
    print('Labeling triple barrier...')
    df_stat['target'] = label_triple_barrier(df_stat)
    print(f'Before dropping -1 targets: {df_stat.shape}')
    
    df_final = df_stat[df_stat['target'] != -1]
    print(f'After dropping -1 targets: {df_final.shape}')
