import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, accuracy_score
from analyzer import add_all_indicators
from data_fetcher import fetch_historical_data
import joblib
import os

def prepare_training_data(df, horizon=4, threshold=0.01):
    """
    학습을 위한 타겟(Label) 생성
    - horizon: 미래 몇 칸을 볼 것인가 (예: 1시간봉 기준 4시간 뒤)
    - threshold: 몇 % 이상 상승하면 '상승(1)'으로 볼 것인가
    """
    df = df.copy()
    
    # 지표 추가
    df = add_all_indicators(df)
    
    # 미래 가격 변화율 계산 (Label 생성)
    # 미래의 Close 가격을 가져옴
    df['Future_Close'] = df['Close'].shift(-horizon)
    df['Price_Change'] = (df['Future_Close'] - df['Close']) / df['Close']
    
    # 타겟 생성: threshold 이상 상승하면 1, 아니면 0
    df['Target'] = (df['Price_Change'] >= threshold).astype(int)
    
    # 학습에 사용할 특성(Features) 선택
    features = [
        'RSI', 'MACD', 'MACD_Signal', 'MACD_Hist',
        'SMA_20', 'EMA_20', 'BB_Upper', 'BB_Middle', 'BB_Lower'
    ]
    
    # 결측치(지표 계산 초기값 등) 제거
    df = df.dropna(subset=features + ['Future_Close'])
    
    return df[features], df['Target']

def train_prediction_model(symbol='BTCUSDT'):
    """
    특정 코인의 1년치 데이터를 학습하여 모델을 생성
    """
    print(f"\n--- {symbol} 패턴 학습 시작 ---")
    
    # 1. 데이터 수집 (1년치)
    data = fetch_historical_data(symbol, interval='1h', years=1)
    if data.empty:
        print("데이터를 가져오지 못했습니다.")
        return None
    
    # 2. 데이터 전처리 및 타겟 생성
    X, y = prepare_training_data(data)
    
    # 3. 학습/테스트 데이터 분리 (8:2)
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, shuffle=False)
    
    # 4. 랜덤 포레스트 모델 학습
    print(f"모델 학습 중 (데이터 크기: {len(X_train)})...")
    model = RandomForestClassifier(n_estimators=100, random_state=42)
    model.fit(X_train, y_train)
    
    # 5. 성능 평가
    y_pred = model.predict(X_test)
    accuracy = accuracy_score(y_test, y_pred)
    
    print("\n--- 학습 결과 보고서 ---")
    print(f"정확도(Accuracy): {accuracy:.2%}")
    print("\n[상세 리포트]")
    print(classification_report(y_test, y_pred))
    
    # 6. 모델 저장
    model_path = f"model_{symbol}.pkl"
    joblib.dump(model, model_path)
    print(f"✅ 모델 저장 완료: {model_path}")
    
    return model

if __name__ == "__main__":
    target_symbol = input("학습할 코인 기호(예: BTCUSDT): ") or 'BTCUSDT'
    train_prediction_model(target_symbol)
