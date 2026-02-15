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
LEARNING_LOG = "ai_decision_log.csv"
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
    # CSV에는 표준 UTC 시간으로 기록하고 대시보드에서 KST로 변환
    now_utc = datetime.utcnow()
    now_str = now_utc.strftime('%Y-%m-%d %H:%M:%S')
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

    # 구글 스프레드시트 업데이트 (Universal 12-column format)
    # [Type, Time, Sym, Act, Side, Price, Qty, PnL, Fee, Bal, Ex1, Ex2]
    try:
        SHEET_ID = "1xQuz_k_FjE1Mjo0R21YS49Pr3ZNpG3yPTofzYyNSbuk"
        values = [[
            "VIRT", now_str, symbol, action, side, str(price), "-", 
            f"{pnl:.2%}", "-", f"{balance:.2f}", "-", "-"
        ]]
        import json
        val_json = json.dumps(values)
        os.system(f"export GOG_KEYRING_PASSWORD=chloe && gog sheets append {SHEET_ID} '시트1!A:L' --values-json '{val_json}' --insert INSERT_ROWS")
    except:
        pass

def log_decision_for_learning(symbol, price, prediction, probs, df_final):
    """
    AI의 매시간 판단을 학습용 데이터로 기록하고 구글 시트에 근거를 남깁니다.
    """
    now_utc = datetime.utcnow()
    now_str = now_utc.strftime('%Y-%m-%d %H:%M:%S')
    
    # 예측값 해석
    pred_map = {0: "NEUTRAL", 1: "LONG", 2: "SHORT"}
    decision = pred_map.get(prediction, "UNKNOWN")
    
    # 판단 근거 추출 (최근 지표 값들)
    last_row = df_final.iloc[-1]
    reasoning = (
        f"RSI:{last_row['RSI']:.1f} / "
        f"Price1h:{last_row['Price_Change_1h']:.2%} / "
        f"MACD:{last_row['MACD_Hist']:.4f} / "
        f"VIX:{last_row['VIX']:.1f}"
    )
    
    # CSV 저장
    df_csv = pd.DataFrame([{
        "시간(KST)": now_str,
        "심볼": symbol,
        "현재가": price,
        "AI_판단": decision,
        "NEUTRAL_확률": f"{probs[0]:.4f}",
        "LONG_확률": f"{probs[1]:.4f}",
        "SHORT_확률": f"{probs[2]:.4f}",
        "판단근거": reasoning
    }])
    header = not os.path.exists(LEARNING_LOG)
    df_csv.to_csv(LEARNING_LOG, mode='a', index=False, header=header, encoding='utf-8-sig')

    # 구글 스프레드시트 업데이트 (Universal 12-column format)
    # Ex1: 판단결과 + 주요지표, Ex2: 확률분포
    try:
        SHEET_ID = "1xQuz_k_FjE1Mjo0R21YS49Pr3ZNpG3yPTofzYyNSbuk"
        prob_str = f"L:{probs[1]:.2f}/S:{probs[2]:.2f}/N:{probs[0]:.2f}"
        values = [[
            "AI", now_str, symbol, "JUDGE", decision, str(price), "-", 
            "-", "-", "-", reasoning, prob_str
        ]]
        import json
        val_json = json.dumps(values)
        os.system(f"export GOG_KEYRING_PASSWORD=chloe && gog sheets append {SHEET_ID} '시트1!A:L' --values-json '{val_json}' --insert INSERT_ROWS")
    except:
        pass

def run_virtual_bot_cycle():
    state = load_bot_state()
    symbol = 'XRPUSD_PERP'
    
    print(f"\n[{datetime.now()}] --- 가상 매매 및 학습 데이터 수집 시작 ---")
    
    # 1. AI 예측값 및 확률 가져오기
    try:
        # 모델 로드 및 예측 (확률 포함)
        model_path = f"model_{symbol}_xgboost.pkl"
        model = joblib.load(model_path)
        
        # 최신 데이터 수집 및 분석
        binance_data = fetch_historical_data(symbol, interval='1h', start_str='3 days ago UTC')
        from analyzer import add_all_indicators
        from macro_fetcher import fetch_macro_data, merge_with_binance_data
        
        df_analyzed = add_all_indicators(binance_data)
        macro_data = fetch_macro_data(years=0.1)
        df_final = merge_with_binance_data(df_analyzed, macro_data)
        
        features = [
            'RSI', 'MACD', 'MACD_Signal', 'MACD_Hist',
            'SMA_20', 'EMA_20', 'BB_Upper', 'BB_Middle', 'BB_Lower',
            'OBV', 'Vol_MA_20', 'Vol_Change',
            'DXY', 'US10Y', 'Nasdaq100', 'Gold', 'VIX',
            'Oil', 'Semiconductor', 'ETH_BTC',
            'Price_Change_1h', 'Price_Change_4h', 'Price_Change_12h',
            'RSI_Lag_12', 'Vol_MA_Lag_12'
        ]
        
        current_features = df_final[features].tail(1)
        prediction = model.predict(current_features)[0]
        probabilities = model.predict_proba(current_features)[0]
        current_price = binance_data['Close'].iloc[-1]
        
        # 매시간의 모든 판단을 학습 데이터로 기록
        log_decision_for_learning(symbol, current_price, prediction, probabilities, df_final)
        print(f"📊 매시간 AI 판단 기록 완료: {pred_map.get(prediction, 'NEUTRAL')}")
        
    except Exception as e:
        print(f"분석/기록 실패: {e}")
        return f"⚠️ **[시스템 오류]**\n- 분석 중 에러 발생: {e}"

    is_exited = False
    action_log = ""

    # 2. 기존 포지션 관리 (익절/손절 체크)
    if state["current_pos"] != 0:
        if state["current_pos"] == 1: # Long
            current_pnl = (1 - state["entry_price"] / current_price) * LEVERAGE
            side_str = "LONG"
        else: # Short
            current_pnl = (state["entry_price"] / current_price - 1) * LEVERAGE
            side_str = "SHORT"
            
        state["peak_pnl"] = max(state["peak_pnl"], current_pnl)
        
        # 손절 체크
        if current_pnl <= -SL_THRESHOLD:
            state["balance"] *= (1 + current_pnl)
            action_log = "EXIT(SL)"
            log_virtual_trade(action_log, symbol, side_str, current_price, current_pnl, state["balance"])
            state["current_pos"] = 0
            is_exited = True
            
        # 트레이링 스탑 체크
        elif state["peak_pnl"] >= TS_ACTIVATION:
            if current_pnl <= (state["peak_pnl"] - TS_CALLBACK):
                state["balance"] *= (1 + current_pnl)
                action_log = "EXIT(TS)"
                log_virtual_trade(action_log, symbol, side_str, current_price, current_pnl, state["balance"])
                state["current_pos"] = 0
                is_exited = True

    # 3. 신규 진입 및 스위칭
    if not is_exited:
        # 확신도가 문턱(65%) 이상일 때만 액션
        if probabilities[int(prediction)] >= CONF_THRESHOLD:
            if prediction != 0 and prediction != state["current_pos"]:
                if state["current_pos"] != 0:
                    # 기존 포지션 정산
                    if state["current_pos"] == 1:
                        pnl = (1 - state["entry_price"] / current_price) * LEVERAGE
                        side_old = "LONG"
                    else:
                        pnl = (state["entry_price"] / current_price - 1) * LEVERAGE
                        side_old = "SHORT"
                    state["balance"] *= (1 + pnl)
                    log_virtual_trade("EXIT(SWITCH)", symbol, side_old, current_price, pnl, state["balance"])
                
                # 신규 진입
                state["current_pos"] = int(prediction)
                state["entry_price"] = current_price
                state["entry_time"] = datetime.now().isoformat()
                state["peak_pnl"] = -999
                side_new = "LONG" if state["current_pos"] == 1 else "SHORT"
                log_virtual_trade("ENTRY", symbol, side_new, current_price, 0, state["balance"])
                save_bot_state(state)
                return f"🚀 **[AI 가상 매매 신호]**\n- 심볼: {symbol}\n- 신규 포지션: {side_new}\n- 진입가: {current_price:,.4f}\n- 확신도: {probabilities[int(prediction)]*100:.2f}%"

    save_bot_state(state)
    
    if is_exited:
        return f"🏁 **[AI 가상 매매 종료 보고]**\n- 사유: {action_log}\n- 종료가: {current_price:,.4f}\n- 현재 자산: {state['balance']:.2f} XRP"
    
    return "NO_REPLY"

# 헬퍼 맵
pred_map = {0: "NEUTRAL", 1: "LONG", 2: "SHORT"}

if __name__ == "__main__":
    msg = run_virtual_bot_cycle()
    if msg:
        print(msg)
