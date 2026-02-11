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

def prepare_training_data_multi(df, horizon=4, threshold=0.015):
    df = df.copy()
    df = add_all_indicators(df)
    
    macro_data = fetch_macro_data(years=1.1)
    df = merge_with_binance_data(df, macro_data)
    
    df['Future_Close'] = df['Close'].shift(-horizon)
    df['Price_Change'] = (df['Future_Close'] - df['Close']) / df['Close']
    
    df['Target'] = 0
    df.loc[df['Price_Change'] >= threshold, 'Target'] = 1
    df.loc[df['Price_Change'] <= -threshold, 'Target'] = 2
    
    features = [
        'RSI', 'MACD', 'MACD_Signal', 'MACD_Hist',
        'SMA_20', 'EMA_20', 'BB_Upper', 'BB_Middle', 'BB_Lower',
        'OBV', 'Vol_MA_20', 'Vol_Change',
        'DXY', 'US10Y', 'Nasdaq100', 'Gold', 'VIX',
        'Oil', 'Semiconductor', 'ETH_BTC'
    ]
    
    df = df.dropna(subset=features + ['Future_Close'])
    return df[features], df['Target'], df['Open time']

def train_xrp_xgboost_model(symbol='XRPUSD_PERP'):
    print(f"\n--- {symbol} XGBoost 알고리즘 업그레이드 및 학습 시작 ---")
    
    # 1. 데이터 수집
    data = fetch_historical_data(symbol, interval='1h', start_str='1 year ago UTC')
    if data.empty:
        return None
    
    # 2. 전처리
    X, y, times = prepare_training_data_multi(data, threshold=0.015)
    
    # 3. Walk-Forward를 위한 Temporal Split (순차 분리)
    # 데이터를 섞지 않고 과거 80%로 학습, 최근 20%로 검증
    split_idx = int(len(X) * 0.8)
    X_train, X_test = X.iloc[:split_idx], X.iloc[split_idx:]
    y_train, y_test = y.iloc[:split_idx], y.iloc[split_idx:]
    test_times = times.iloc[split_idx:]
    
    print(f"훈련 데이터: {len(X_train)}건 (과거 80%)")
    print(f"테스트 데이터: {len(X_test)}건 (최근 20% - AI가 처음 보는 데이터)")

    # 4. XGBoost 모델 학습
    # 과적합 방지를 위해 파라미터 조절
    model = XGBClassifier(
        n_estimators=100,
        max_depth=5,
        learning_rate=0.05,
        objective='multi:softprob',
        num_class=3,
        random_state=42,
        tree_method='hist' # CPU 효율적 학습
    )
    
    model.fit(X_train, y_train)
    
    # 5. 평가
    y_pred = model.predict(X_test)
    print("\n--- Walk-Forward 테스트 결과 (최근 20% 데이터) ---")
    print(f"현실적 정확도: {accuracy_score(y_test, y_pred):.2%}")
    print(classification_report(y_test, y_pred, target_names=['Neutral', 'Long', 'Short']))
    
    # 6. 저장
    model_path = f"model_{symbol}_xgboost.pkl"
    joblib.dump(model, model_path)
    
    # 테스트용 데이터셋 별도 저장 (백테스터 사용용)
    test_data = X_test.copy()
    test_data['Target'] = y_test
    test_data['Open time'] = test_times
    test_data['Close'] = data.loc[X_test.index, 'Close']
    test_data.to_csv(f"test_data_{symbol}.csv", index=False)
    
    print(f"✅ XGBoost 모델 저장 완료: {model_path}")
    return model

if __name__ == "__main__":
    train_xrp_xgboost_model()
