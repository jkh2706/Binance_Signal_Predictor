import pandas as pd
import sys

def main():
    print('Starting script...')
    df = pd.read_csv('/home/jeong-kihun/.openclaw/workspace/Binance_Signal_Predictor/data_storage/XRPUSDT_15m.csv')
    print('Data length:', len(df))
    
    # feature engineering 직접 임포트 후 적용
    sys.path.append('/home/jeong-kihun/.openclaw/workspace/Binance_Signal_Predictor')
    from feature_engineering import build_features
    import inspect
    import feature_engineering
    
    # dropna 제거 버전 동적 생성
    source = inspect.getsource(build_features)
    source = source.replace('return df.dropna()', 'return df')
    exec(source, feature_engineering.__dict__)
    
    df['open time'] = pd.to_datetime(df['Open time'])
    df.columns = [c.lower() for c in df.columns]
    
    df_feat = feature_engineering.build_features(df)
    nans = df_feat.isna().sum()
    print('NaNs per parameter:')
    print(nans[nans>0].sort_values(ascending=False).head(20))

if __name__ == '__main__':
    main()
