import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, accuracy_score
from analyzer import add_all_indicators
from data_fetcher import fetch_historical_data
from macro_fetcher import fetch_macro_data, merge_with_binance_data
import joblib
import os

def prepare_training_data_multi(df, horizon=4, threshold=0.015):
    """
    3분류 학습 데이터 준비 (1: Long, 2: Short, 0: Neutral)
    """
    df = df.copy()
    
    # 1. 지표 추가
    df = add_all_indicators(df)
    
    # 2. 매크로 데이터 결합
    macro_data = fetch_macro_data(years=1.1)
    df = merge_with_binance_data(df, macro_data)
    
    # 3. 타겟 생성
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
        'Oil', 'Semiconductor', 'ETH_BTC'
    ]
    
    df = df.dropna(subset=features + ['Future_Close'])
    return df[features], df['Target']

def train_xrp_switching_model(symbol='XRPUSD_PERP'):
    """
    XRP COIN-M 스위칭 전략 전용 모델 학습
    """
    print(f"\n--- {symbol} COIN-M 스위칭 모델 학습 시작 ---")
    
    # 1. 데이터 수집 (COIN-M API 제한에 따라 50일치 수집 테스트)
    data = fetch_historical_data(symbol, interval='1h', start_str='50 days ago UTC')
    if data.empty:
        print("데이터 수집 실패")
        return None
    
    # 2. 전처리 (3분류)
    X, y = prepare_training_data_multi(data, threshold=0.015)
    
    # 3. 분리
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, shuffle=False)
    
    # 4. 모델 학습 (RandomForest - 클래스 가중치 밸런스 조정)
    print(f"모델 학습 중... (데이터: {len(X_train)}건)")
    model = RandomForestClassifier(n_estimators=200, class_weight='balanced', random_state=42)
    model.fit(X_train, y_train)
    
    # 5. 평가
    y_pred = model.predict(X_test)
    print("\n--- XRP 스위칭 모델 성능 보고 ---")
    print(f"정확도: {accuracy_score(y_test, y_pred):.2%}")
    print(classification_report(y_test, y_pred, target_names=['Neutral', 'Long', 'Short']))
    
    # 6. 저장
    model_path = f"model_{symbol}_switching.pkl"
    joblib.dump(model, model_path)
    print(f"✅ 모델 저장 완료: {model_path}")
    return model

if __name__ == "__main__":
    train_xrp_switching_model()
