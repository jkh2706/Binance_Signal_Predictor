import pandas as pd
import numpy as np
import joblib
import matplotlib.pyplot as plt
import os
from datetime import datetime

def run_high_confidence_backtest(symbol='XRPUSD_PERP', initial_xrp=1000, leverage=3, fee_rate=0.0005, threshold=0.7):
    """
    확신도 필터링을 적용한 초정밀 백테스팅
    """
    print(f"\n--- {symbol} 고확신 필터링 백테스팅 (Threshold: {threshold*100}%, 수수료 반영) ---")
    
    test_file = f"test_data_{symbol}.csv"
    model_path = f"model_{symbol}_xgboost.pkl"
    
    if not os.path.exists(test_file):
        print("❌ 테스트 데이터 파일이 없습니다.")
        return
    
    df = pd.read_csv(test_file)
    df['Open time'] = pd.to_datetime(df['Open time'])
    model = joblib.load(model_path)
    
    # 1. 예측 확률 추출
    features = [
        'RSI', 'MACD', 'MACD_Signal', 'MACD_Hist',
        'SMA_20', 'EMA_20', 'BB_Upper', 'BB_Middle', 'BB_Lower',
        'OBV', 'Vol_MA_20', 'Vol_Change',
        'DXY', 'US10Y', 'Nasdaq100', 'Gold', 'VIX',
        'Oil', 'Semiconductor', 'ETH_BTC'
    ]
    probas = model.predict_proba(df[features])
    
    # 2. 수익률 시뮬레이션
    df['Price_Next'] = df['Close'].shift(-1)
    df = df.dropna(subset=['Price_Next'])
    
    balance = initial_xrp
    balances = []
    current_pos = 0 # 0: Neutral, 1: Long, 2: Short
    
    trades_count = 0
    skipped_count = 0
    
    for i in range(len(df)):
        row = df.iloc[i]
        prob = probas[i] # [Neutral_prob, Long_prob, Short_prob]
        
        max_prob = np.max(prob)
        best_sig = np.argmax(prob)
        
        # 필터링 로직: 확신도가 threshold보다 낮으면 'Neutral'로 간주하거나 포지션 유지
        if max_prob < threshold:
            new_sig = 0 # 확신 없으면 관망
            skipped_count += 1
        else:
            new_sig = best_sig
            
        price = row['Close']
        next_price = row['Price_Next']
        
        # 포지션 스위칭 (수수료 발생)
        if new_sig != current_pos:
            fee = balance * fee_rate * leverage * 2
            balance -= fee
            trades_count += 1
            current_pos = new_sig
            
        # 수익률 계산
        if current_pos == 1: # Long
            change = (1 - price / next_price) * leverage
            balance *= (1 + change)
        elif current_pos == 2: # Short
            change = (price / next_price - 1) * leverage
            balance *= (1 + change)
            
        balances.append(balance)
        
    df_result = df.iloc[:len(balances)].copy()
    df_result['Balance'] = balances
    
    # 3. 결과 보고
    final_balance = balance
    total_return = (final_balance / initial_xrp - 1) * 100
    
    print("\n" + "="*45)
    print(f"📊 {symbol} 고확신 필터링 결과")
    print(f"📅 기간: {df_result['Open time'].min()} ~ {df_result['Open time'].max()}")
    print(f"🎯 진입 문턱(Threshold): {threshold*100}%")
    print("-" * 45)
    print(f"💰 초기 자산: {initial_xrp:,.2f} XRP")
    print(f"💰 최종 자산: {final_balance:,.2f} XRP")
    print(f"📈 총 수익률: {total_return:.2f}%")
    print(f"🔄 총 거래 횟수: {trades_count}회 (낮은 확신으로 {skipped_count}회 관망)")
    print("="*45)
    
    # 차트 저장
    plt.figure(figsize=(12, 6))
    plt.plot(df_result['Open time'], df_result['Balance'])
    plt.title(f'Filtered Backtest: {symbol} (Threshold {threshold})')
    plt.xlabel('Date')
    plt.ylabel('XRP Balance')
    plt.grid(True)
    plt.savefig(f'filtered_backtest_{threshold}.png')
    
    return final_balance

if __name__ == "__main__":
    # 여러 문턱값 테스트
    for th in [0.6, 0.7, 0.8]:
        run_high_confidence_backtest(threshold=th)
