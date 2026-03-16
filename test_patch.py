import pandas as pd
import sys
sys.path.append('/home/jeong-kihun/.openclaw/workspace/Binance_Signal_Predictor')

def test_pipeline():
    print('Loading CSV offline...')
    df = pd.read_csv('/home/jeong-kihun/.openclaw/workspace/Binance_Signal_Predictor/data_storage/XRPUSDT_15m.csv', nrows=2000)
    print(f'Original length: {len(df)}')
    
    # 1. format columns
    if 'Open time' in df.columns:
        df.rename(columns={'Open time': 'open time'}, inplace=True)
    df.columns = [c.lower() for c in df.columns]
    df = df.loc[:, ~df.columns.duplicated()]

    # 2. build_features
    from feature_engineering import build_features, ensure_stationarity
    print('Running build_features...')
    df_feat = build_features(df)
    print(f'Length after build_features (dropna included): {len(df_feat)}')
    if len(df_feat) == 0:
        print('FAILED: build_features dropped all data!')
        return

    # 3. ensure_stationarity
    print('Running ensure_stationarity...')
    df_stat = ensure_stationarity(df_feat)
    print(f'Length after ensure_stationarity (dropna included): {len(df_stat)}')
    if len(df_stat) == 0:
        print('FAILED: ensure_stationarity dropped all data!')
        return
        
    print('SUCCESS! Fixed pipeline outputs data.')
    print('Final Shape:', df_stat.shape)

if __name__ == '__main__':
    test_pipeline()
