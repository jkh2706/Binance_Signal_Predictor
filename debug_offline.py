import pandas as pd
import sys
import numpy as np
sys.path.append('/home/jeong-kihun/.openclaw/workspace/Binance_Signal_Predictor')

print('Loading local CSV offline...')
csv_path = '/home/jeong-kihun/.openclaw/workspace/Binance_Signal_Predictor/data_storage/XRPUSDT_15m.csv'
# It seems the path might be in a different folder, let's try reading it directly
try:
    df = pd.read_csv(csv_path)
except Exception as e:
    # try another path if needed, we saw it in logs
    # 💾 최종 데이터 저장 완료: 105211건 (/home/jeong-kihun/.openclaw/workspace/Binance_Signal_Predictor/data_storage/XRPUSDT_15m.csv)
    print(e)
    sys.exit(1)

print(f'Original data length: {len(df)}')

# format if needed
if 'Open time' in df.columns:
    df['Open time'] = pd.to_datetime(df['Open time'])
    # change to lowercase to match format
    df.columns = [c.lower() for c in df.columns]
    
from feature_engineering import build_features

print('Running build_features without dropna...')
df_feat = build_features.__code__.co_consts # just hack it: let's copy the code or just run build_features and check before dropna is harder.
# Let's read the function and remove dropna
import inspect
import feature_engineering
source = inspect.getsource(feature_engineering.build_features)
source = source.replace('return df.dropna()', 'return df')
exec(source, feature_engineering.__dict__)

df_feat = feature_engineering.build_features(df)
print(f'Data length before dropna: {len(df_feat)}')

nans = df_feat.isna().sum()
print('--- NaN counts per column ---')
print(nans[nans > 0].sort_values(ascending=False).head(20))

# if any column is all NaN
all_nan_cols = nans[nans == len(df_feat)].index.tolist()
if all_nan_cols:
    print(f'⚠️ Columns that are completely ALL NaNs: {all_nan_cols}')
else:
    print('No column is completely NaN. Let us check ensure_stationarity...')
    
    # check ensure_stationarity
    df_feat_drop = df_feat.dropna()
    from feature_engineering import ensure_stationarity
    
    source2 = inspect.getsource(ensure_stationarity)
    source2 = source2.replace('return df.dropna()', 'return df')
    exec(source2, feature_engineering.__dict__)
    
    if len(df_feat_drop) > 0:
        df_stat = feature_engineering.ensure_stationarity(df_feat_drop)
        nans2 = df_stat.isna().sum()
        print('--- NaN counts after ensure_stationarity ---')
        print(nans2[nans2 > 0].sort_values(ascending=False).head(20))
        all_nan_cols2 = nans2[nans2 == len(df_stat)].index.tolist()
        if all_nan_cols2:
             print(f'⚠️ Columns all NaN in ensure_stationarity: {all_nan_cols2}')

