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
    
    model_path = f"model_{symbol}_switching.pkl"
    if not os.path.exists(model_path):
        print(f"❌ 모델 파일({model_path})이 없습니다.")
        return None
    
    model = joblib.load(model_path)
    
    # 1. 데이터 수집
    binance_data = fetch_historical_data(symbol, interval='1h', start_str='3 days ago UTC')
    macro_data = fetch_macro_data(years=0.1)
    
    # 2. 지표 결합
    df = add_all_indicators(binance_data)
    df = merge_with_binance_data(df, macro_data)
    
    features = [
        'RSI', 'MACD', 'MACD_Signal', 'MACD_Hist',
        'SMA_20', 'EMA_20', 'BB_Upper', 'BB_Middle', 'BB_Lower',
        'OBV', 'Vol_MA_20', 'Vol_Change',
        'DXY', 'US10Y', 'Nasdaq100', 'Gold', 'VIX',
        'Oil', 'Semiconductor', 'ETH_BTC'
    ]
    
    current_data = df[features].tail(1)
    
    # 3. 예측
    prediction = model.predict(current_data)[0]
    probabilities = model.predict_proba(current_data)[0]
    
    current_price = binance_data['Close'].iloc[-1]
    
    print("\n" + "="*45)
    print(f"🕵️  XRP 스위칭 전략 AI 리포트")
    print(f"⏰ 시각: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} (KST)")
    print(f"💰 현재가: {current_price:,.4f} USD (COIN-M)")
    print("-" * 45)
    
    # 결과 해석
    # 0: Neutral, 1: Long, 2: Short
    status_map = {0: "💤 관망 (Neutral)", 1: "🚀 롱 진입/유지 (LONG)", 2: "📉 숏 진입/유지 (SHORT)"}
    
    print(f"📢 AI 추천 포지션: {status_map[prediction]}")
    print("-" * 45)
    print(f"📊 분석 결과 (확신도):")
    print(f"  - LONG 확률  : {probabilities[1]*100:.2f}%")
    print(f"  - SHORT 확률 : {probabilities[2]*100:.2f}%")
    print(f"  - Neutral 확률: {probabilities[0]*100:.2f}%")
    print("="*45)
    
    return prediction

if __name__ == "__main__":
    get_switching_prediction('XRPUSD_PERP')
