import pandas as pd
import numpy as np
import joblib
import matplotlib.pyplot as plt
from datetime import datetime

def run_realistic_backtest(symbol='XRPUSD_PERP', initial_xrp=1000, leverage=3, fee_rate=0.0005):
    """
    수수료와 AI가 보지 못한 데이터를 사용한 현실적인 백테스트
    """
    print(f"\n--- {symbol} 현실적 백테스팅 (XGBoost + 수수료 {fee_rate*100}% 반영) ---")
    
    # 1. 테스트 데이터 및 모델 로드
    test_file = f"test_data_{symbol}.csv"
    model_path = f"model_{symbol}_xgboost.pkl"
    
    if not os.path.exists(test_file):
        print("❌ 테스트 데이터 파일이 없습니다. 학습을 먼저 진행해 주세요.")
        return
    
    df = pd.read_csv(test_file)
    df['Open time'] = pd.to_datetime(df['Open time'])
    model = joblib.load(model_path)
    
    # 2. 예측 시그널 생성
    features = [
        'RSI', 'MACD', 'MACD_Signal', 'MACD_Hist',
        'SMA_20', 'EMA_20', 'BB_Upper', 'BB_Middle', 'BB_Lower',
        'OBV', 'Vol_MA_20', 'Vol_Change',
        'DXY', 'US10Y', 'Nasdaq100', 'Gold', 'VIX',
        'Oil', 'Semiconductor', 'ETH_BTC'
    ]
    df['Signal'] = model.predict(df[features])
    
    # 3. 수익률 및 수수료 시뮬레이션
    df['Price_Next'] = df['Close'].shift(-1)
    df = df.dropna(subset=['Price_Next'])
    
    balance = initial_xrp
    balances = []
    current_pos = 0 # 0: Neutral, 1: Long, 2: Short
    
    trades_count = 0
    
    for idx, row in df.iterrows():
        new_sig = int(row['Signal'])
        price = row['Close']
        next_price = row['Price_Next']
        
        # 포지션 스위칭 시 수수료 발생
        # 1. 기존 포지션 종료 수수료 + 2. 신규 포지션 진입 수수료
        if new_sig != current_pos:
            # 수수료 차감 (현재 잔고의 fee_rate * leverage)
            # 종료 시 한번, 진입 시 한번 총 두 번 발생한다고 가정
            fee = balance * fee_rate * leverage * 2
            balance -= fee
            trades_count += 1
            current_pos = new_sig
            
        # 보유 포지션에 따른 수익률 계산 (COIN-M 기준)
        if current_pos == 1: # Long
            # ROE = (1 - Entry/Exit) * Lev (XRP 개수 증가 기준)
            # 가격 상승 시 XRP 개수는 줄어들지만 가치는 오름. 
            # 하지만 기훈님의 목표는 'XRP 개수 늘리기'이므로 개수 변화에 집중
            change = (1 - price / next_price) * leverage
            balance *= (1 + change)
        elif current_pos == 2: # Short
            # ROE = (Entry/Exit - 1) * Lev
            change = (price / next_price - 1) * leverage
            balance *= (1 + change)
            
        balances.append(balance)
        
    df_result = df.iloc[:len(balances)].copy()
    df_result['Balance'] = balances
    
    # 4. 결과 요약
    final_balance = balance
    total_return = (final_balance / initial_xrp - 1) * 100
    
    print("\n" + "="*45)
    print(f"📊 {symbol} 현실적 백테스팅 결과")
    print(f"📅 기간: {df_result['Open time'].min()} ~ {df_result['Open time'].max()}")
    print(f"🕵️ AI 모델: XGBoost (Unseen Data)")
    print("-" * 45)
    print(f"💰 초기 자산: {initial_xrp:,.2f} XRP")
    print(f"💰 최종 자산: {final_balance:,.2f} XRP")
    print(f"📈 총 수익률: {total_return:.2f}%")
    print(f"🔄 총 포지션 스위칭 횟수: {trades_count}회")
    print("="*45)
    
    # 차트 저장
    plt.figure(figsize=(12, 6))
    plt.plot(df_result['Open time'], df_result['Balance'])
    plt.title(f'Realistic Backtest: {symbol} (XGBoost + Fees)')
    plt.xlabel('Date')
    plt.ylabel('XRP Balance')
    plt.grid(True)
    plt.savefig('realistic_backtest_result.png')
    
    return df_result

import os
if __name__ == "__main__":
    run_realistic_backtest()
