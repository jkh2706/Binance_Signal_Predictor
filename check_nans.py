import pandas as pd
import numpy as np
import feature_engineering
import inspect

# Read data exactly like data_sync
df = pd.read_csv('/home/jeong-kihun/.openclaw/workspace/Binance_Signal_Predictor/data_storage/XRPUSDT_15m.csv')
if 'Open time' in df.columns:
    df.rename(columns={'Open time': 'open time'}, inplace=True)
df.columns = [c.lower() for c in df.columns]
# ensure no dupes
df = df.loc[:, ~df.columns.duplicated()]

print(f'Original data length: {len(df)}')

# Hack the build_features to NOT dropna
source = inspect.getsource(feature_engineering.build_features)
source = source.replace('return df.dropna()', 'return df')
exec(source, feature_engineering.__dict__)

df_feat = feature_engineering.build_features(df)
nans = df_feat.isna().sum()
print('--- NaN Counts from build_features ---')
bad_cols = nans[nans > len(df_feat) * 0.5]
print(bad_cols)

# Hack ensure_stationarity
source2 = inspect.getsource(feature_engineering.ensure_stationarity)
source2 = source2.replace('return df.dropna()', 'return df')
exec(source2, feature_engineering.__dict__)

df_stat = feature_engineering.ensure_stationarity(df_feat.dropna())
nans2 = df_stat.isna().sum()
print('--- NaN Counts from ensure_stationarity ---')
bad_cols2 = nans2[nans2 > len(df_stat) * 0.5]
print(bad_cols2)

