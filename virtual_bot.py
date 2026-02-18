import os
import json
import pandas as pd
import numpy as np
import joblib
from datetime import datetime, timedelta
import time
from binance.client import Client

# 현재 디렉토리를 path에 추가하여 모듈 로드 지원
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from xrp_realtime_predictor import get_switching_prediction
from data_fetcher import fetch_historical_data

# 설정값
STATE_FILE = "virtual_bot_state.json"
LOG_FILE = "virtual_trades.csv"
CONF_THRESHOLD = 0.65
SL_THRESHOLD = 0.02
TS_ACTIVATION = 0.03
TS_CALLBACK = 0.015
LEVERAGE = 3

def load_bot_state():
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, 'r') as f:
                state = json.load(f)
                if state.get("current_pos") is None: state["current_pos"] = 0
                return state
        except:
            pass
    return {
        "current_pos": 0, # 0: None, 1: Long, 2: Short
        "entry_price": 0,
        "entry_time": None,
        "peak_pnl": -999,
        "balance": 1000.0
    }

def save_bot_state(state):
    with open(STATE_FILE, 'w') as f:
        json.dump(state, f, indent=2)

def log_virtual_trade(action, symbol, side, price, pnl, balance):
    now_kst = datetime.utcnow() + timedelta(hours=9)
    now_str = now_kst.strftime('%Y-%m-%d %H:%M:%S')
    df = pd.DataFrame([{
        "시간(KST)": now_str,
        "액션": action,
        "심볼": symbol,
        "포지션": side,
        "가격": price,
        "수익률(ROE)": f"{pnl:.2%}",
        "잔고(XRP)": f"{balance:.2f}"
    }])
    header = not os.path.exists(LOG_FILE)
    df.to_csv(LOG_FILE, mode='a', index=False, header=header, encoding='utf-8-sig')

def run_virtual_bot_cycle():
    state = load_bot_state()
    symbol = 'XRPUSD_PERP'
    
    print(f"\n[{datetime.now()}] --- 가상 매매 감시 사이클 시작 ---")
    
    # 1. AI 예측값 가져오기
    try:
        prediction = get_switching_prediction(symbol)
        if prediction is None:
            return "⚠️ **[AI 분석 오류]**\n- 모델을 로드할 수 없거나 분석에 실패했습니다."
    except Exception as e:
        print(f"예측 실패: {e}")
        return f"⚠️ **[AI 분석 오류]**\n- 에러 발생: {e}"

    # 현재가 확인
    try:
        from binance.enums import HistoricalKlinesType
        # COIN-M의 경우 klines_type을 명시하지 않으면 fetch_historical_data 내부에서 
        # symbol에 'USD_'가 있으면 FUTURES_COIN으로 설정됨.
        # 1m 데이터 에러 우회를 위해 SPOT으로 가격을 가져옴
        data = fetch_historical_data('XRPUSDT', interval='1m', start_str='10 minutes ago UTC', klines_type=HistoricalKlinesType.SPOT)
    except Exception as e:
        print(f"SPOT 현재가 수집 실패: {e}")
        return "⚠️ **[데이터 오류]**\n- 최신 가격 정보를 가져올 수 없습니다."
    if data.empty: return "⚠️ **[데이터 오류]**\n- 최신 가격 정보를 가져올 수 없습니다."
    current_price = data['Close'].iloc[-1]
    
    is_exited = False
    pnl_report = ""

    # 2. 기존 포지션 관리 (익절/손절 체크)
    if state["current_pos"] != 0:
        if state["current_pos"] == 1: # Long
            current_pnl = (1 - state["entry_price"] / current_price) * LEVERAGE
            side_str = "LONG"
        else: # Short
            current_pnl = (state["entry_price"] / current_price - 1) * LEVERAGE
            side_str = "SHORT"
            
        state["peak_pnl"] = max(state["peak_pnl"], current_pnl)
        pnl_report = f"(현재 수익률: {current_pnl:+.2%}, 최고점: {state['peak_pnl']:+.2%})"
        
        # 손절 체크
        if current_pnl <= -SL_THRESHOLD:
            state["balance"] *= (1 + current_pnl)
            log_virtual_trade("EXIT(SL)", symbol, side_str, current_price, current_pnl, state["balance"])
            state["current_pos"] = 0
            is_exited = True
            print(f"🚩 [가상 손절] {side_str} 종료 @ {current_price}")
            
        # 트레이링 스탑 체크
        elif state["peak_pnl"] >= TS_ACTIVATION:
            if current_pnl <= (state["peak_pnl"] - TS_CALLBACK):
                state["balance"] *= (1 + current_pnl)
                log_virtual_trade("EXIT(TS)", symbol, side_str, current_price, current_pnl, state["balance"])
                state["current_pos"] = 0
                is_exited = True
                print(f"💰 [가상 익절] {side_str} 종료 @ {current_price}")

    # 3. 신규 진입 및 스위칭
    # 0: Neutral, 1: Long, 2: Short
    if not is_exited:
        # 기존 포지션과 다른 신호(1 or 2)가 왔을 때만 스위칭
        if prediction != 0 and prediction != state["current_pos"]:
            if state["current_pos"] != 0:
                if state["current_pos"] == 1:
                    pnl = (1 - state["entry_price"] / current_price) * LEVERAGE
                    side_old = "LONG"
                else:
                    pnl = (state["entry_price"] / current_price - 1) * LEVERAGE
                    side_old = "SHORT"
                state["balance"] *= (1 + pnl)
                log_virtual_trade("EXIT(SWITCH)", symbol, side_old, current_price, pnl, state["balance"])
            
            state["current_pos"] = int(prediction)
            state["entry_price"] = current_price
            state["entry_time"] = datetime.now().isoformat()
            state["peak_pnl"] = -999
            side_new = "LONG" if state["current_pos"] == 1 else "SHORT"
            log_virtual_trade("ENTRY", symbol, side_new, current_price, 0, state["balance"])
            print(f"🚀 [가상 진입] {side_new} 시작 @ {current_price}")
            save_bot_state(state)
            return f"🚀 **[AI 가상 매매 신호]**\n- 심볼: {symbol}\n- 신규 포지션: {side_new}\n- 진입가: {current_price:,.4f}\n- 확신도: AI가 새로운 추세를 포착했습니다!"
        
        # 만약 prediction이 0(Neutral)이고 포지션이 있다면 유지하거나 종료할 수 있는데,
        # 여기서는 기존 로직대로 '유지'함. (전략적 선택)

    save_bot_state(state)
    
    if is_exited:
        return f"🏁 **[AI 가상 매매 종료 보고]**\n- 포지션 종료가 감지되었습니다.\n- 현재 자산: {state['balance']:.2f} XRP"
    
    if state["current_pos"] != 0:
        side_str = "LONG" if state["current_pos"] == 1 else "SHORT"
        return f"🛰️ **[AI 가상 매매 모니터링]**\n- 포지션: {side_str} 유지 중\n- {pnl_report}"
    
    return "💤 **[AI 가상 매매 모니터링]**\n- 현재 관망 중입니다. 확실한 신호를 기다리고 있어요."

if __name__ == "__main__":
    msg = run_virtual_bot_cycle()
    if msg:
        print(msg)
