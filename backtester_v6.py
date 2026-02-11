import pandas as pd
import numpy as np
import joblib
import matplotlib.pyplot as plt
import os
from datetime import datetime

def run_advanced_backtest(symbol='XRPUSD_PERP', initial_xrp=1000, leverage=3, fee_rate=0.0005, conf_threshold=0.75, tp_threshold=0.04, sl_threshold=0.02):
    """
    고확신 필터링 + 익절(TP) + 손절(SL) 로직을 모두 포함한 최종 진화형 백테스팅
    tp_threshold: 목표 수익률 (예: 4% 수익 시 익절)
    sl_threshold: 허용 손실률 (예: 2% 손실 시 손절)
    """
    print(f"\n--- {symbol} 최종 진화형 백테스팅 ---")
    print(f"설정: 필터 {conf_threshold*100}%, 익절 {tp_threshold*100}%, 손절 {sl_threshold*100}%")
    
    test_file = f"test_data_{symbol}.csv"
    model_path = f"model_{symbol}_xgboost.pkl"
    
    if not os.path.exists(test_file):
        print("❌ 테스트 데이터 파일이 없습니다. 최신 모델로 다시 학습해 주세요.")
        return
    
    df = pd.read_csv(test_file)
    df['Open time'] = pd.to_datetime(df['Open time'])
    model = joblib.load(model_path)
    
    # 1. 예측 확률 추출 (새로운 피처 포함)
    features = [
        'RSI', 'MACD', 'MACD_Signal', 'MACD_Hist',
        'SMA_20', 'EMA_20', 'BB_Upper', 'BB_Middle', 'BB_Lower',
        'OBV', 'Vol_MA_20', 'Vol_Change',
        'DXY', 'US10Y', 'Nasdaq100', 'Gold', 'VIX',
        'Oil', 'Semiconductor', 'ETH_BTC',
        'Price_Change_1h', 'Price_Change_4h', 'Price_Change_12h',
        'RSI_Lag_12', 'Vol_MA_Lag_12'
    ]
    
    # 데이터에 피처가 없는 경우 대비 (학습 데이터와 맞춤)
    available_features = [f for f in features if f in df.columns]
    probas = model.predict_proba(df[available_features])
    
    # 2. 수익률 시뮬레이션
    df['Price_Next'] = df['Close'].shift(-1)
    df = df.dropna(subset=['Price_Next'])
    
    balance = initial_xrp
    balances = []
    current_pos = 0 # 0: Neutral, 1: Long, 2: Short
    entry_price = 0
    
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
        
        # --- 청산(Exit) 로직: 익절 및 손절 체크 ---
        is_exited = False
        if current_pos != 0:
            unrealized_pnl = 0
            if current_pos == 1: # Long
                unrealized_pnl = (1 - entry_price / price) * leverage
            elif current_pos == 2: # Short
                unrealized_pnl = (entry_price / price - 1) * leverage
                
            # 익절 체크
            if unrealized_pnl >= tp_threshold:
                fee = balance * fee_rate * leverage
                balance -= fee
                current_pos = 0
                tp_count += 1
                is_exited = True
            
            # 손절 체크
            elif unrealized_pnl <= -sl_threshold:
                fee = balance * fee_rate * leverage
                balance -= fee
                current_pos = 0
                sl_count += 1
                is_exited = True

        # --- 진입(Entry) 로직 ---
        if not is_exited:
            # 확신도가 문턱을 넘을 때만 포지션 변경
            if max_prob >= conf_threshold:
                new_sig = best_sig
                if new_sig != current_pos:
                    # 수수료 발생
                    fee = balance * fee_rate * leverage * 2
                    balance -= fee
                    trades_count += 1
                    current_pos = new_sig
                    entry_price = price
            
        # --- 시간당 수익률 반영 ---
        if current_pos == 1: # Long
            change = (1 - price / next_price) * leverage
            balance *= (1 + change)
        elif current_pos == 2: # Short
            change = (price / next_price - 1) * leverage
            balance *= (1 + change)
            
        balances.append(balance)
        
    df_result = df.iloc[:len(balances)].copy()
    df_result['Balance'] = balances
    
    final_balance = balance
    total_return = (final_balance / initial_xrp - 1) * 100
    
    print("\n" + "="*45)
    print(f"📊 {symbol} 최종 진화형 테스트 결과")
    print(f"💰 최종 자산: {final_balance:,.2f} XRP ({total_return:+.2%})")
    print(f"🔄 총 거래: {trades_count}회 | 익절: {tp_count}회 | 손절: {sl_count}회")
    print("="*45)
    
    plt.figure(figsize=(12, 6))
    plt.plot(df_result['Open time'], df_result['Balance'])
    plt.title(f'Advanced Backtest: {symbol} (TP {tp_threshold}, SL {sl_threshold})')
    plt.grid(True)
    plt.savefig('advanced_backtest_result.png')
    
    return final_balance

if __name__ == "__main__":
    run_advanced_backtest()
