import pandas as pd
import numpy as np
import joblib
import matplotlib.pyplot as plt
import os
from datetime import datetime

def run_trailing_stop_backtest(symbol='XRPUSD_PERP', initial_xrp=1000, leverage=3, fee_rate=0.0005, 
                               conf_threshold=0.75, sl_threshold=0.02, 
                               ts_activation=0.03, ts_callback=0.015):
    """
    트레이링 스탑(Trailing Stop) 로직이 추가된 백테스팅
    - ts_activation: 트레이링 스탑이 활성화되는 수익률 (예: 3% 수익 달성 시 시작)
    - ts_callback: 고점 대비 허용하는 되돌림 비율 (예: 고점 대비 1.5% 하락 시 익절)
    """
    print(f"\n--- {symbol} 트레이링 스탑 전략 백테스팅 ---")
    print(f"설정: 필터 {conf_threshold*100}%, 손절 {sl_threshold*100}%, TS활성 {ts_activation*100}%, TS콜백 {ts_callback*100}%")
    
    test_file = f"test_data_{symbol}.csv"
    model_path = f"model_{symbol}_xgboost.pkl"
    
    if not os.path.exists(test_file):
        print("❌ 테스트 데이터 파일이 없습니다.")
        return
    
    df = pd.read_csv(test_file)
    df['Open time'] = pd.to_datetime(df['Open time'])
    model = joblib.load(model_path)
    
    # 1. 지표 리스트 (이전과 동일)
    features = [
        'RSI', 'MACD', 'MACD_Signal', 'MACD_Hist',
        'SMA_20', 'EMA_20', 'BB_Upper', 'BB_Middle', 'BB_Lower',
        'OBV', 'Vol_MA_20', 'Vol_Change',
        'DXY', 'US10Y', 'Nasdaq100', 'Gold', 'VIX',
        'Oil', 'Semiconductor', 'ETH_BTC',
        'Price_Change_1h', 'Price_Change_4h', 'Price_Change_12h',
        'RSI_Lag_12', 'Vol_MA_Lag_12'
    ]
    probas = model.predict_proba(df[features])
    
    # 2. 시뮬레이션 변수
    df['Price_Next'] = df['Close'].shift(-1)
    df = df.dropna(subset=['Price_Next'])
    
    balance = initial_xrp
    balances = []
    current_pos = 0 
    entry_price = 0
    peak_pnl = -999 # 포지션 진입 후 달성한 최고 수익률
    
    trades_count = 0
    tp_count = 0
    sl_count = 0
    
    for i in range(len(df)):
        row = df.iloc[i]
        prob = probas[i]
        max_prob = np.max(prob)
        best_sig = np.argmax(prob)
        
        price = row['Close']
        next_price = row['Price_Next']
        
        is_exited = False
        
        # --- 포지션 유지 중 관리 로직 ---
        if current_pos != 0:
            # 실시간 수익률 계산 (ROE 기준)
            if current_pos == 1: # Long
                current_pnl = (1 - entry_price / price) * leverage
            else: # Short
                current_pnl = (entry_price / price - 1) * leverage
            
            # 고점 갱신
            peak_pnl = max(peak_pnl, current_pnl)
            
            # 1. 손절 체크
            if current_pnl <= -sl_threshold:
                balance -= balance * fee_rate * leverage
                current_pos = 0
                sl_count += 1
                is_exited = True
            
            # 2. 트레이링 스탑 체크
            elif peak_pnl >= ts_activation:
                # 고점 대비 콜백 비율만큼 하락했는지 확인
                if current_pnl <= (peak_pnl - ts_callback):
                    balance -= balance * fee_rate * leverage
                    current_pos = 0
                    tp_count += 1
                    is_exited = True

        # --- 신규 진입 로직 ---
        if not is_exited:
            if max_prob >= conf_threshold:
                new_sig = best_sig
                if new_sig != current_pos:
                    # 스위칭 수수료
                    fee = balance * fee_rate * leverage * 2
                    balance -= fee
                    trades_count += 1
                    current_pos = new_sig
                    entry_price = price
                    peak_pnl = -999 # 고점 초기화
            
        # --- 자산 반영 ---
        if current_pos == 1:
            change = (1 - price / next_price) * leverage
            balance *= (1 + change)
        elif current_pos == 2:
            change = (price / next_price - 1) * leverage
            balance *= (1 + change)
            
        balances.append(balance)
        
    df_result = df.iloc[:len(balances)].copy()
    df_result['Balance'] = balances
    
    final_balance = balance
    total_return = (final_balance / initial_xrp - 1) * 100
    
    print("\n" + "="*45)
    print(f"📊 {symbol} 트레이링 스탑 테스트 결과")
    print(f"💰 최종 자산: {final_balance:,.2f} XRP ({total_return:+.2%})")
    print(f"🔄 거래: {trades_count}회 | 익절(TS): {tp_count}회 | 손절: {sl_count}회")
    print("="*45)
    
    plt.figure(figsize=(12, 6))
    plt.plot(df_result['Open time'], df_result['Balance'])
    plt.title(f'Trailing Stop Backtest: {symbol}')
    plt.grid(True)
    plt.savefig('trailing_backtest_result.png')
    
    return final_balance

if __name__ == "__main__":
    run_trailing_stop_backtest()
