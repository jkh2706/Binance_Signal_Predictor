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

def prepare_training_data_multi(df, horizon=4, threshold=0.015):
    """
    3분류 학습 데이터 준비 (1: Long, 2: Short, 0: Neutral)
    """
    df = df.copy()
    df = add_all_indicators(df)
    
    # 상장 초기부터 학습하기 위해 매크로 데이터 기간을 6년으로 확대
    macro_data = fetch_macro_data(years=6)
    df = merge_with_binance_data(df, macro_data)
    
    df['Future_Close'] = df['Close'].shift(-horizon)
    df['Price_Change'] = (df['Future_Close'] - df['Close']) / df['Close']
    
    # 1: 상승(Long), 2: 하락(Short), 0: 관망(Neutral)
    df['Target'] = 0
    df.loc[df['Price_Change'] >= threshold, 'Target'] = 1
    df.loc[df['Price_Change'] <= -threshold, 'Target'] = 2
    
    features = [
        'RSI', 'MACD', 'MACD_Signal', 'MACD_Hist',
        'SMA_20', 'EMA_20', 'BB_Upper', 'BB_Middle', 'BB_Lower',
        'OBV', 'Vol_MA_20', 'Vol_Change',
        'DXY', 'US10Y', 'Nasdaq100', 'Gold', 'VIX',
        'Oil', 'Semiconductor', 'ETH_BTC',
        'Price_Change_1h', 'Price_Change_4h', 'Price_Change_12h',
        'RSI_Lag_12', 'Vol_MA_Lag_12'
    ]
    
    df = df.dropna(subset=features + ['Future_Close'])
    return df[features], df['Target'], df['Open time']

def train_xrp_xgboost_model(symbol='XRPUSDT'):
    print(f"\n--- {symbol} (USD-M) 대용량 전생 학습 시작 (COIN-M 전략용) ---")
    
    # 1. 데이터 수집 (5년치)
    data = fetch_historical_data(symbol, interval='1h', start_str='5 years ago UTC')
    if data.empty:
        print("❌ 데이터 수집 실패")
        return None
    
    # 2. 전처리
    X, y, times = prepare_training_data_multi(data, threshold=0.015)
    
    # inf/-inf 처리 및 NaN 채우기
    X = X.replace([np.inf, -np.inf], np.nan).fillna(0)
    
    # 3. Walk-Forward Split (순차 분리)
    split_idx = int(len(X) * 0.8)
    X_train, X_test = X.iloc[:split_idx], X.iloc[split_idx:]
    y_train, y_test = y.iloc[:split_idx], y.iloc[split_idx:]
    test_times = times.iloc[split_idx:]
    
    print(f"훈련 데이터: {len(X_train)}건 | 테스트 데이터: {len(X_test)}건")

    # 4. XGBoost 모델 학습
    print("XGBoost 모델 학습 중...")
    model = XGBClassifier(
        n_estimators=200,
        max_depth=6,
        learning_rate=0.03,
        objective='multi:softprob',
        num_class=3,
        random_state=42,
        tree_method='hist'
    )
    
    model.fit(X_train, y_train)
    
    # 5. 평가
    y_pred = model.predict(X_test)
    print("\n--- Walk-Forward 검증 결과 (최근 20% 데이터) ---")
    print(f"현실적 정확도: {accuracy_score(y_test, y_pred):.2%}")
    print(classification_report(y_test, y_pred, target_names=['Neutral', 'Long', 'Short']))
    
    # 6. 저장 (COIN-M에서 쓸 수 있도록 이름 고정)
    model_path = f"model_XRPUSD_PERP_xgboost.pkl"
    joblib.dump(model, model_path)
    
    # 백테스트용 데이터셋 별도 저장
    test_data = X_test.copy()
    test_data['Target'] = y_test
    test_data['Open time'] = test_times
    test_data['Close'] = data.loc[X_test.index, 'Close']
    test_data.to_csv(f"test_data_XRPUSD_PERP.csv", index=False)
    
    print(f"✅ 모델 및 테스트 데이터 저장 완료: {model_path}")
    return model

if __name__ == "__main__":
    model = train_xrp_xgboost_model()
    if model is None:
        sys.exit(1)
