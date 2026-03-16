import argparse
import pandas as pd
import numpy as np
from xgboost import XGBClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, accuracy_score
from analyzer import add_all_indicators
from data_fetcher import fetch_historical_data
from macro_fetcher import fetch_macro_data, merge_with_binance_data
import joblib
import os
import sys

# ─────────────────────────────────────────────
# [BUG 2 FIX] 피처 목록을 단일 상수로 관리
# ─────────────────────────────────────────────
FEATURE_COLUMNS = [
    'RSI', 'MACD', 'MACD_Signal', 'MACD_Hist',
    'SMA_20', 'EMA_20', 'BB_Upper', 'BB_Middle', 'BB_Lower',
    'OBV', 'Vol_MA_20', 'Vol_Change',
    'DXY', 'US10Y', 'Nasdaq100', 'Gold', 'VIX',
    'Oil', 'Semiconductor', 'ETH_BTC',
    'Price_Change_1h', 'Price_Change_4h', 'Price_Change_12h',
    'RSI_Lag_12', 'Vol_MA_Lag_12'
]

MACRO_COLUMNS = [
    'DXY', 'US10Y', 'Nasdaq100', 'Gold',
    'VIX', 'Oil', 'Semiconductor', 'ETH_BTC'
]

def prepare_training_data_multi(df, horizon=4, threshold=0.015):
    df = df.copy()
    df = add_all_indicators(df)
    macro_data = fetch_macro_data(years=6)
    if macro_data.empty:
        for col in MACRO_COLUMNS:
            df[col] = 0.0
    else:
        df = merge_with_binance_data(df, macro_data)
        for col in MACRO_COLUMNS:
            if col not in df.columns:
                df[col] = 0.0
    df['Future_Close'] = df['Close'].shift(-horizon)
    df['Price_Change'] = (df['Future_Close'] - df['Close']) / df['Close']
    df['Target'] = 0
    df.loc[df['Price_Change'] >= threshold, 'Target'] = 1
    df.loc[df['Price_Change'] <= -threshold, 'Target'] = 2
    df = df.dropna(subset=FEATURE_COLUMNS + ['Future_Close'])
    return df[FEATURE_COLUMNS], df['Target'], df['Open time'], df.index

def train_xrp_xgboost_model(symbol='XRPUSDT', n_estimators=200, max_depth=6, lr=0.03, threshold=0.015, suffix=""):
    print(f"\n--- {symbol} 학습 시작 (n={n_estimators}, depth={max_depth}, lr={lr}, th={threshold}) ---")
    try:
        data = fetch_historical_data(symbol, interval='1h', start_str='2 years ago UTC')
        if data.empty: return None
        data = data.reset_index(drop=True)
        X, y, times, filtered_idx = prepare_training_data_multi(data, threshold=threshold)
        if X.empty: return None
        X = X.replace([np.inf, -np.inf], np.nan).fillna(0)
        split_idx = int(len(X) * 0.8)
        X_train, X_test = X.iloc[:split_idx], X.iloc[split_idx:]
        y_train, y_test = y.iloc[:split_idx], y.iloc[split_idx:]
        test_times = times.iloc[split_idx:]
        test_filtered_idx = filtered_idx[split_idx:]
        
        model = XGBClassifier(
            n_estimators=n_estimators,
            max_depth=max_depth,
            learning_rate=lr,
            objective='multi:softprob',
            num_class=3,
            random_state=42,
            tree_method='hist'
        )
        model.fit(X_train, y_train)
        
        y_pred = model.predict(X_test)
        acc = accuracy_score(y_test, y_pred)
        print(f"\n현실적 정확도: {acc:.2%}")
        
        # 접미사가 있으면 별도 저장, 없으면 기본 파일 갱신
        model_name = f"model_XRPUSD_PERP_xgboost{suffix}.pkl"
        joblib.dump(model, model_name)
        
        test_data = X_test.copy()
        test_data['Target'] = y_test.values
        test_data['Open time'] = test_times.values
        test_data['Close'] = data.loc[test_filtered_idx, 'Close'].values
        test_data.to_csv(f"test_data_XRPUSD_PERP{suffix}.csv", index=False)
        
        print(f"✅ 모델 저장 완료: {model_name}")
        return acc
    except Exception as e:
        print(f"❌ 오류: {e}")
        return None

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--n", type=int, default=200)
    parser.add_argument("--depth", type=int, default=6)
    parser.add_argument("--lr", type=float, default=0.03)
    parser.add_argument("--th", type=float, default=0.015)
    parser.add_argument("--suffix", type=str, default="")
    args = parser.parse_args()
    
    train_xrp_xgboost_model(n_estimators=args.n, max_depth=args.depth, lr=args.lr, threshold=args.th, suffix=args.suffix)
