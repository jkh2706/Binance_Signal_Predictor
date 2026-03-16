import pandas as pd
import sys
import numpy as np
sys.path.append('/home/jeong-kihun/.openclaw/workspace/Binance_Signal_Predictor')

print('Loading local CSV offline...')
df = pd.read_csv('/home/jeong-kihun/.openclaw/workspace/Binance_Signal_Predictor/data_storage/XRPUSDT_15m.csv')
print(f'Original length: {len(df)}')

# Convert keys to match what data_fetcher does
df.columns = [c.lower() for c in df.columns]

from feature_engineering import build_features
import feature_engineering
import inspect

source = inspect.getsource(build_features)
source = source.replace('return df.dropna()', 'return df')
exec(source, feature_engineering.__dict__)

try:
    df_feat = feature_engineering.build_features(df.copy())
    print('build_features ran without dropna')
    counts = df_feat.isna().sum()
    print('NaN counts per column in build_features:')
    print(counts[counts > 0].sort_values(ascending=False).head(20))
    
    from feature_engineering import ensure_stationarity
    source2 = inspect.getsource(ensure_stationarity)
    source2 = source2.replace('return df.dropna()', 'return df')
    exec(source2, feature_engineering.__dict__)
    
    df_stat = feature_engineering.ensure_stationarity(df_feat.copy())
    print('ensure_stationarity ran without dropna')
    counts2 = df_stat.isna().sum()
    print('NaN counts per column in ensure_stationarity:')
    print(counts2[counts2 > len(df_stat) * 0.9])
except Exception as e:
    print('Error:', e)
