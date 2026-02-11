import pandas as pd
import numpy as np
import joblib
import matplotlib.pyplot as plt
from analyzer import add_all_indicators
from data_fetcher import fetch_historical_data
from macro_fetcher import fetch_macro_data, merge_with_binance_data
from datetime import datetime

def run_backtest(symbol='XRPUSD_PERP', initial_xrp=1000, leverage=3):
    print(f"\n--- {symbol} 전략 백테스팅 시작 (초기 자산: {initial_xrp} XRP, 레버리지: {leverage}배) ---")
    
    # 1. 데이터 및 모델 로드
    model_path = f"model_{symbol}_switching.pkl"
    model = joblib.load(model_path)
    
    data = fetch_historical_data(symbol, interval='1h', start_str='1 year ago UTC')
    macro_data = fetch_macro_data(years=1.1)
    
    # 2. 지표 결합
    df = add_all_indicators(data)
    df = merge_with_binance_data(df, macro_data)
    
    features = [
        'RSI', 'MACD', 'MACD_Signal', 'MACD_Hist',
        'SMA_20', 'EMA_20', 'BB_Upper', 'BB_Middle', 'BB_Lower',
        'OBV', 'Vol_MA_20', 'Vol_Change',
        'DXY', 'US10Y', 'Nasdaq100', 'Gold', 'VIX',
        'Oil', 'Semiconductor', 'ETH_BTC'
    ]
    
    df = df.dropna(subset=features)
    
    # 3. 예측값 생성 (전체 데이터에 대해)
    X = df[features]
    df['Signal'] = model.predict(X)
    
    # 4. 수익률 시뮬레이션 (COIN-M 기준)
    # Signal: 1(Long), 2(Short), 0(Neutral)
    
    df['Price_Next'] = df['Close'].shift(-1)
    df = df.dropna(subset=['Price_Next'])
    
    # 시간봉별 수익률 계산 (단순화: 수수료 제외, 펀딩비 제외)
    # ROE = (1 - Entry/Exit) * Lev (Long)
    # ROE = (Entry/Exit - 1) * Lev (Short)
    
    def calc_returns(row):
        price = row['Close']
        next_price = row['Price_Next']
        sig = row['Signal']
        
        if sig == 1: # Long
            return (1 - price / next_price) * leverage
        elif sig == 2: # Short
            return (price / next_price - 1) * leverage
        else: # Neutral
            return 0.0

    df['Hourly_Return'] = df.apply(calc_returns, axis=1)
    
    # 누적 수익률 계산
    df['Cumulative_Return'] = (1 + df['Hourly_Return']).cumprod()
    df['Final_XRP'] = initial_xrp * df['Cumulative_Return']
    
    # 5. 결과 요약
    final_balance = df['Final_XRP'].iloc[-1]
    total_return_pct = (final_balance / initial_xrp - 1) * 100
    win_rate = (df['Hourly_Return'] > 0).sum() / (df['Hourly_Return'] != 0).sum()
    
    print("\n" + "="*45)
    print(f"📊 {symbol} 백테스팅 결과 보고서")
    print(f"📅 기간: {df['Open time'].min()} ~ {df['Open time'].max()}")
    print("-" * 45)
    print(f"💰 초기 자산: {initial_xrp:,.2f} XRP")
    print(f"💰 최종 자산: {final_balance:,.2f} XRP")
    print(f"📈 총 수익률: {total_return_pct:.2f}%")
    print(f"🎯 승률 (시간봉 기준): {win_rate:.2%}")
    print(f"🔄 총 거래 시그널 횟수: {len(df[df['Signal'] != 0])}회")
    print("="*45)
    
    # 차트 저장 (KST 폰트 문제로 영문 제목 사용)
    plt.figure(figsize=(12, 6))
    plt.plot(df['Open time'], df['Final_XRP'])
    plt.title(f'Backtest Result: {symbol} (Initial: {initial_xrp} XRP)')
    plt.xlabel('Date')
    plt.ylabel('XRP Balance')
    plt.grid(True)
    plt.savefig('backtest_result.png')
    
    return df

if __name__ == "__main__":
    run_backtest()
