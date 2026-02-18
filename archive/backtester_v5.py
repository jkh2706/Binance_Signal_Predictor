import pandas as pd
import numpy as np
import joblib
import matplotlib.pyplot as plt
import os
from datetime import datetime

def run_tp_backtest(symbol='XRPUSD_PERP', initial_xrp=1000, leverage=3, fee_rate=0.0005, conf_threshold=0.8, tp_threshold=0.03):
    """
    고확신 필터링 + 익절(Take Profit) 로직을 추가한 백테스팅
    tp_threshold: 목표 수익률 (예: 0.03 = 3% 수익 시 익절)
    """
    print(f"\n--- {symbol} 초정밀 백테스팅 (필터: {conf_threshold*100}%, 익절: {tp_threshold*100}%) ---")
    
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
    entry_price = 0
    
    trades_count = 0
    tp_count = 0
    
    for i in range(len(df)):
        row = df.iloc[i]
        prob = probas[i]
        
        max_prob = np.max(prob)
        best_sig = np.argmax(prob)
        
        price = row['Close']
        next_price = row['Price_Next']
        
        # --- 익절 체크 로직 ---
        is_tp_triggered = False
        if current_pos != 0:
            unrealized_pnl = 0
            if current_pos == 1: # Long
                unrealized_pnl = (1 - entry_price / price) * leverage
            elif current_pos == 2: # Short
                unrealized_pnl = (entry_price / price - 1) * leverage
                
            if unrealized_pnl >= tp_threshold:
                # 익절 실행! 포지션을 중립으로 변경
                fee = balance * fee_rate * leverage # 종료 수수료만
                balance -= fee
                current_pos = 0
                tp_count += 1
                is_tp_triggered = True
                # print(f"  [TP] {row['Open time']} | 수익률: {unrealized_pnl:.2%}")

        # --- 신규 진입/스위칭 로직 ---
        # 익절이 방금 일어났다면 이번 봉에서는 쉬고 다음 봉부터 신호 체크
        if not is_tp_triggered:
            new_sig = best_sig if max_prob >= conf_threshold else current_pos
            
            if new_sig != current_pos:
                # 기존 종료 + 신규 진입 수수료
                fee = balance * fee_rate * leverage * 2
                balance -= fee
                trades_count += 1
                current_pos = new_sig
                entry_price = price
            
        # --- 수익금 반영 ---
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
    print(f"📊 {symbol} 익절 로직 적용 결과")
    print(f"📅 기간: {df_result['Open time'].min()} ~ {df_result['Open time'].max()}")
    print(f"🎯 설정: 필터 {conf_threshold*100}%, 익절 {tp_threshold*100}%")
    print("-" * 45)
    print(f"💰 초기 자산: {initial_xrp:,.2f} XRP")
    print(f"💰 최종 자산: {final_balance:,.2f} XRP")
    print(f"📈 총 수익률: {total_return:.2f}%")
    print(f"🔄 총 거래 횟수: {trades_count}회")
    print(f"💰 익절 성공 횟수: {tp_count}회")
    print("="*45)
    
    # 차트 저장
    plt.figure(figsize=(12, 6))
    plt.plot(df_result['Open time'], df_result['Balance'])
    plt.title(f'TP Backtest: {symbol} (Conf {conf_threshold}, TP {tp_threshold})')
    plt.xlabel('Date')
    plt.ylabel('XRP Balance')
    plt.grid(True)
    plt.savefig(f'tp_backtest_{tp_threshold}.png')
    
    return final_balance

if __name__ == "__main__":
    # 다양한 익절 라인 테스트 (1.5%, 3%, 5%)
    for tp in [0.015, 0.03, 0.05]:
        run_tp_backtest(tp_threshold=tp)
