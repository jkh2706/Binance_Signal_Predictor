import os
import pandas as pd
import numpy as np
import joblib
from datetime import datetime
from binance.client import Client
from binance.enums import HistoricalKlinesType
from dotenv import load_dotenv
from data_fetcher import fetch_historical_data
from analyzer import add_all_indicators
from macro_fetcher import fetch_macro_data, merge_with_binance_data

load_dotenv()

def get_switching_prediction(symbol='XRPUSD_PERP'):
    """
    XRP COIN-M 스위칭 전략용 실시간 AI 분석
    """
    print(f"\n--- {symbol} COIN-M 스위칭 AI 분석 시작 ---")
    
    # 모델 파일 경로 설정 (절대 경로로 변경하여 실행 위치에 상관없이 로드 가능하게 함)
    current_dir = os.path.dirname(os.path.abspath(__file__))
    model_path = os.path.join(current_dir, f"model_{symbol}_xgboost.pkl")
    
    if not os.path.exists(model_path):
        print(f"❌ 모델 파일({model_path})이 없습니다.")
        return None
    
    model = joblib.load(model_path)
    # 모델 패키지 형식(dict)인 경우 처리
    if isinstance(model, dict):
        scaler = model.get('scaler')
        pca = model.get('pca')
        features = model.get('features')
        model = model.get('model')
    
    # 1. 데이터 수집 (가이드 권장: 1시간봉 기준)
    binance_data = fetch_historical_data(symbol, interval='1h', start_str='60 days ago UTC')
    macro_data = fetch_macro_data(years=0.1)
    
    # 2. 지표 결합
    from feature_engineering import build_features, ensure_stationarity
    df = build_features(binance_data)
    df = ensure_stationarity(df)
    
    # 모델 학습 시 사용한 피처 리스트 (train_xrp_v4.py의 로직과 일치)
    if 'features' not in locals() or features is None:
        exclude = ['open', 'high', 'low', 'close', 'volume', 'target', 'open time', 'close time', 'timestamp', 'fundingRate']
        features = [c for c in df.columns if c not in exclude]
    
    current_data = df[features].tail(1)
    
    # 전처리 적용
    if 'scaler' in locals() and scaler:
        current_data_scaled = scaler.transform(current_data)
        if 'pca' in locals() and pca:
            current_data_scaled = pca.transform(current_data_scaled)
    else:
        current_data_scaled = current_data
    
    # 3. 예측
    prediction = model.predict(current_data_scaled)[0]
    probabilities = model.predict_proba(current_data_scaled)[0]
    
    current_price = binance_data['Close'].iloc[-1]
    
    print("\n" + "="*45)
    print(f"🕵️  XRP 스위칭 전략 AI 리포트")
    print(f"⏰ 시각: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} (KST)")
    print(f"💰 현재가: {current_price:,.4f} USD (COIN-M)")
    print("-" * 45)
    
    # 결과 해석
    # [수정] 0: Short, 1: Long, 2: Neutral (신호 체계 통일)
    status_map = {0: "📉 숏 진입/유지 (SHORT)", 1: "🚀 롱 진입/유지 (LONG)", 2: "💤 관망 (Neutral)"}
    
    print(f"📢 AI 추천 포지션: {status_map[prediction]}")
    print("-" * 45)
    print(f"📊 분석 결과 (확신도):")
    print(f"  - SHORT 확률 : {probabilities[0]*100:.2f}%")
    print(f"  - LONG 확률  : {probabilities[1]*100:.2f}%")
    print(f"  - Neutral 확률: {probabilities[2]*100:.2f}%")
    print("="*45)
    
    return prediction, probabilities, df.tail(1)

if __name__ == "__main__":
    get_switching_prediction('XRPUSD_PERP')
