import pandas as pd
import sys
sys.path.append('/home/jeong-kihun/.openclaw/workspace/Binance_Signal_Predictor')

def check_dupes():
    df = pd.read_csv('/home/jeong-kihun/.openclaw/workspace/Binance_Signal_Predictor/data_storage/XRPUSDT_15m.csv', nrows=1000)
    df['open time'] = pd.to_datetime(df['Open time'])
    df.columns = [c.lower() for c in df.columns]

    # feature_engineering.py 내 사용 중인 함수들 순차적용
    from utils import add_liquidity_sweep_features, add_fvg_features, calculate_heikin_ashi
    
    # 1. calculate_heikin_ashi
    df = calculate_heikin_ashi(df)
    
    # Check dupes
    from collections import Counter
    dups = [k for k,v in Counter(df.columns).items() if v > 1]
    if dups:
        print('Dupes after heikin_ashi:', dups)
        
    # 2. add_liquidity_sweep_features
    df = add_liquidity_sweep_features(df)
    dups = [k for k,v in Counter(df.columns).items() if v > 1]
    if dups:
        print('Dupes after liquidity_sweep_features:', dups)

    # 3. add_fvg_features
    df = add_fvg_features(df)
    dups = [k for k,v in Counter(df.columns).items() if v > 1]
    if dups:
        print('Dupes after fvg_features:', dups)
        
    print('Final columns:', df.columns.tolist())
    
if __name__ == '__main__':
    check_dupes()
