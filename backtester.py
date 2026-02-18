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
    수정된 ROE 공식 및 수수료 로직이 적용된 백테스터
    """
    print(f"\n--- {symbol} 트레이링 스탑 전략 백테스팅 ---")
    print(f"설정: 필터 {conf_threshold*100}%, 손절 {sl_threshold*100}%, TS활성 {ts_activation*100}%, TS콜백 {ts_callback*100}%")
    
    test_file = f"test_data_{symbol}.csv"
    model_path = f"model_{symbol}_xgboost.pkl"
    
    # [수정 2] 테스트 데이터 존재 여부 확인
    if not os.path.exists(test_file):
        print("❌ 테스트 데이터가 없습니다. 먼저 train_xrp_v3.py를 실행해서 모델과 테스트 데이터를 생성해 주세요.")
        return
    
    df = pd.read_csv(test_file)
    df['Open time'] = pd.to_datetime(df['Open time'])
    model = joblib.load(model_path)
    
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
    
    df['Price_Next'] = df['Close'].shift(-1)
    df = df.dropna(subset=['Price_Next'])
    
    balance = initial_xrp
    balances = []
    current_pos = 0 # 0: Neutral, 1: Long, 2: Short
    entry_price = 0
    peak_pnl = -999 
    
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
        
        # --- 1. 포지션 유지 중 관리 로직 ---
        if current_pos != 0:
            # [수정 1] 실시간 ROE 계산 공식 수정 (분모를 entry_price로)
            if current_pos == 1: # Long
                current_pnl = (price / entry_price - 1) * leverage
            else: # Short
                current_pnl = (1 - price / entry_price) * leverage
            
            peak_pnl = max(peak_pnl, current_pnl)
            
            # 손절 체크
            if current_pnl <= -sl_threshold:
                # [수정 4] 수수료 반영
                balance -= balance * fee_rate * leverage
                current_pos = 0
                sl_count += 1
                is_exited = True
            
            # 트레이링 스탑 체크
            elif peak_pnl >= ts_activation:
                if current_pnl <= (peak_pnl - ts_callback):
                    balance -= balance * fee_rate * leverage
                    current_pos = 0
                    tp_count += 1
                    is_exited = True

        # --- 2. 신규 진입 및 스위칭 로직 ---
        if not is_exited:
            if max_prob >= conf_threshold:
                new_sig = best_sig
                if new_sig != current_pos:
                    # 포지션 변경 시 수수료 차감 (기존 종료 수수료 + 신규 진입 수수료)
                    if current_pos != 0:
                        balance -= balance * fee_rate * leverage # 종료 수수료
                    
                    if new_sig != 0:
                        balance -= balance * fee_rate * leverage # 진입 수수료
                        entry_price = price
                        peak_pnl = -999
                        trades_count += 1
                    
                    current_pos = new_sig
            
        # --- 3. 자산 반영 (다음 봉 가격 기준) ---
        if current_pos != 0:
            # [수정 1] 다음 봉 수익률 계산 공식 수정
            if current_pos == 1: # Long
                change = (next_price / price - 1) * leverage
            else: # Short
                change = (1 - next_price / price) * leverage
            balance *= (1 + change)
            
        balances.append(balance)
        
    df_result = df.iloc[:len(balances)].copy()
    df_result['Balance'] = balances
    
    final_balance = balance
    total_return = (final_balance / initial_xrp - 1) * 100
    
    print("\n" + "="*45)
    print(f"📊 {symbol} 백테스트 결과 (수수료/ROE 공식 반영)")
    print(f"💰 최종 자산: {final_balance:,.2f} XRP ({total_return:+.2f}%)")
    print(f"🔄 거래: {trades_count}회 | 익절(TS): {tp_count}회 | 손절: {sl_count}회")
    print("="*45)
    
    plt.figure(figsize=(12, 6))
    plt.plot(df_result['Open time'], df_result['Balance'])
    plt.title(f'Corrected Backtest: {symbol} (Fee 0.05% reflected)')
    plt.grid(True)
    plt.savefig('backtest_result.png')
    
    return final_balance

if __name__ == "__main__":
    run_trailing_stop_backtest()
