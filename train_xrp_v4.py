import pandas as pd
import numpy as np
from xgboost import XGBClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, accuracy_score
import joblib
import os
import sys

# 신규 모듈 import
from feature_engineering import build_features, ensure_stationarity
from label_engineering import label_triple_barrier
from model_training import train_model, optimize_hyperparams, BEST_PARAMS_XRP

# 기존 모듈 유지
from data_fetcher import fetch_historical_data

def train_xrp_xgboost_model_v4(symbol='XRPUSDT', use_optuna=False):
    print(f"\n--- {symbol} (USD-M) 1시간봉 기반 정밀 학습 시작 (V4.2) ---")
    
    # 1. 데이터 수집 (1시간봉 기준 3년치 - 가이드 권장)
    data = fetch_historical_data(symbol, interval='1h', start_str='3 years ago UTC')
    if data.empty:
        print("❌ 데이터 수집 실패")
        return None
    
    # 2. 피처 엔지니어링 및 레이블링
    print("피처 생성 및 정상성 검정 중...")
    df = build_features(data)
    df = ensure_stationarity(df)
    
    print("Triple Barrier 레이블링 생성 중...")
    # 가이드 권장 파라미터: max_holding=20 (20시간)
    df['target'] = label_triple_barrier(df, atr_multiplier_tp=1.5, atr_multiplier_sl=1.0, max_holding=20)
    
    # 레이블이 -1인 데이터(계산 불가 구간) 제거
    df = df[df['target'] != -1]
    
    # 3. 데이터 분리 및 준비
    y = df['target']
    features = [c for c in df.columns if c not in ['open', 'high', 'low', 'close', 'volume', 'target', 'open time', 'close time', 'timestamp', 'fundingRate']]
    X = df[features]
    
    # inf/-inf 처리 및 NaN 채우기
    X = X.replace([np.inf, -np.inf], np.nan).fillna(0)
    
    print(f"총 피처 수: {len(features)}")
    print(f"레이블 분포:\n{y.value_counts(normalize=True)}")

    # 4. Walk-Forward Split (순차 분리)
    split_idx = int(len(X) * 0.8)
    X_train, X_test = X.iloc[:split_idx], X.iloc[split_idx:]
    y_train, y_test = y.iloc[:split_idx], y.iloc[split_idx:]
    
    print(f"훈련 데이터: {len(X_train)}건 | 테스트 데이터: {len(X_test)}건")

    # 5. 하이퍼파라미터 최적화 (Optuna)
    params = BEST_PARAMS_XRP
    if use_optuna:
        print("Optuna 하이퍼파라미터 최적화 수행 중...")
        params = optimize_hyperparams(X_train, y_train, n_trials=30)

    # 6. 모델 학습 (PCA 포함된 통합 파이프라인 사용)
    print("XGBoost 모델 및 PCA 학습 중...")
    model, scaler, pca = train_model(X_train, y_train, params=params, use_pca=True, n_components=25)
    
    # 7. 평가
    # 테스트 데이터 전처리
    X_test_scaled = scaler.transform(X_test)
    if pca is not None:
        X_test_scaled = pca.transform(X_test_scaled)
        
    y_pred = model.predict(X_test_scaled)
    print("\n--- Walk-Forward 검증 결과 (최근 20% 데이터) ---")
    print(f"현실적 정확도: {accuracy_score(y_test, y_pred):.2%}")
    print(classification_report(y_test, y_pred, target_names=['SHORT', 'LONG', 'NEUTRAL']))
    
    # 7. 통합 저장
    # 기존 코드와의 호환성을 위해 모델 개별 저장 및 통합 메타데이터 저장
    model_path = f"model_XRPUSD_PERP_xgboost.pkl"
    # COIN-M 스위칭 모델로 저장
    save_data = {
        'model': model,
        'scaler': scaler,
        'pca': pca,
        'features': features,
        'params': BEST_PARAMS_XRP
    }
    joblib.dump(save_data, model_path)
    
    print(f"✅ 모델 패키지 저장 완료: {model_path}")
    return model

if __name__ == "__main__":
    train_xrp_xgboost_model_v4()
