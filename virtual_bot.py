import os
import json
import pandas as pd
import numpy as np
import joblib
from datetime import datetime, timedelta
import time
import subprocess
from binance.client import Client
from binance.enums import HistoricalKlinesType

# 현재 디렉토리를 path에 추가하여 모듈 로드 지원
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from xrp_realtime_predictor import get_switching_prediction
from data_fetcher import fetch_historical_data
from bot_modules import RiskManager, PerformanceTracker

# 설정값 (절대 경로로 변경하여 안정성 확보)
current_dir = os.path.dirname(os.path.abspath(__file__))
STATE_FILE = os.path.join(current_dir, "virtual_bot_state.json")
LOG_FILE = os.path.join(current_dir, "virtual_trades.csv")
LEARNING_LOG = os.path.join(current_dir, "ai_decision_log.csv")
TRADING_LOG_JSONL = os.path.join(current_dir, "logs/trading_log.jsonl")

CONF_THRESHOLD = 0.50 
SL_THRESHOLD = 0.02
TS_ACTIVATION = 0.03
TS_CALLBACK = 0.015
LEVERAGE = 3

# AGENT TASK 5: RiskManager 초기화
risk_mgr = RiskManager(
    account_balance=1000.0, 
    max_risk_per_trade=0.01, 
    max_leverage=5, 
    max_drawdown_stop=0.15, 
    daily_loss_limit=0.05
)

# AGENT TASK 6: PerformanceTracker 초기화
tracker = PerformanceTracker(TRADING_LOG_JSONL)

def load_bot_state():
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, 'r') as f:
                state = json.load(f)
                if state.get("current_pos") is None: state["current_pos"] = 0
                # 리스크 매니저 상태 동기화
                risk_mgr.set_state(
                    state.get("balance", 1000.0),
                    state.get("peak_balance", 1000.0),
                    state.get("daily_start_balance")
                )
                return state
        except:
            pass
    return {
        "current_pos": 0, # 0: None, 1: Long, 2: Short
        "entry_price": 0,
        "entry_time": None,
        "peak_pnl": -999,
        "balance": 1000.0,
        "peak_balance": 1000.0,
        "loop_count": 0
    }

def save_bot_state(state):
    state["balance"] = risk_mgr.current_balance
    state["peak_balance"] = risk_mgr.peak_balance
    state["daily_start_balance"] = risk_mgr.daily_start_balance
    with open(STATE_FILE, 'w') as f:
        json.dump(state, f, indent=2)

def log_virtual_trade(action, symbol, side, price, pnl_pct, balance):
    now_kst = datetime.utcnow() + timedelta(hours=9)
    now_str = now_kst.strftime('%Y-%m-%d %H:%M:%S')
    
    # AGENT TASK 6: JSONL 로그 기록
    if "EXIT" in action:
        trade_info = {
            "timestamp": now_str,
            "symbol": symbol,
            "side": side,
            "exit_price": price,
            "pnl_pct": pnl_pct,
            "balance": balance,
            "action": action
        }
        tracker.log_trade(trade_info)

    # 기존 CSV 로그 유지
    df = pd.DataFrame([{
        "시간(KST)": now_str,
        "액션": action,
        "심볼": symbol,
        "포지션": side,
        "가격": price,
        "수익률(ROE)": f"{pnl_pct:.2%}",
        "잔고(XRP)": f"{balance:.2f}"
    }])
    header = not os.path.exists(LOG_FILE)
    df.to_csv(LOG_FILE, mode='a', index=False, header=header, encoding='utf-8-sig')

def run_retraining():
    print(f"[{datetime.now()}] 🔄 재학습 트리거됨. train_xrp_v3.py 실행...")
    try:
        # 실제 환경에 맞게 경로 조정 필요할 수 있음
        subprocess.run(["python3", os.path.join(current_dir, "train_xrp_v3.py")], check=True)
        print("✅ 재학습 완료.")
    except Exception as e:
        print(f"❌ 재학습 실패: {e}")

def run_virtual_bot_cycle():
    state = load_bot_state()
    symbol = 'XRPUSD_PERP'
    state["loop_count"] = state.get("loop_count", 0) + 1
    
    print(f"\n[{datetime.now()}] --- 루프 #{state['loop_count']} 시작 ---")
    
    # AGENT TASK 5: 리스크 체크 (MDD/일일 손실)
    allowed, reason = risk_mgr.check_trading_allowed()
    if not allowed:
        print(f"🛑 [리스크 제한] 거래가 중단되었습니다: {reason}")
        # return f"🛑 **[리스크 중단 알림]**\n- 사유: {reason}\n- 봇을 정지합니다."

    # 현재가 확인
    try:
        data = fetch_historical_data('XRPUSDT', interval='1m', start_str='10 minutes ago UTC', klines_type=HistoricalKlinesType.SPOT)
        if data.empty: return "⚠️ **[데이터 오류]** 가격 수집 실패"
        current_price = data['Close'].iloc[-1]
    except Exception as e:
        return f"⚠️ **[데이터 오류]** {e}"

    # 1. AI 예측값 가져오기
    try:
        prediction, probabilities, df_last = get_switching_prediction(symbol)
        if prediction is None:
            return "⚠️ **[AI 분석 오류]** 예측 실패"
            
        # [V7.3 추가] AI 판단 로그 기록 (ai_decision_log.csv)
        now_kst = datetime.utcnow() + timedelta(hours=9)
        now_str = now_kst.strftime('%Y-%m-%d %H:%M:%S')
        
        # probabilities: [Neutral, Long, Short]
        # CSV 컬럼: 시간(KST), 심볼, 가격, 판단, LONG_확률, SHORT_확률, NEUTRAL_확률, 지표
        indicators_str = ""
        if not df_last.empty:
            last_row = df_last.iloc[-1]
            indicators_str = f"RSI:{last_row.get('RSI', 0):.1f}/P1h:{last_row.get('P1h', 0):.2f}%/VIX:{last_row.get('VIX', 0):.1f}"

        status_map = {0: "NEUTRAL", 1: "LONG", 2: "SHORT"}
        
        log_df = pd.DataFrame([{
            "시간(KST)": now_str,
            "심볼": symbol,
            "현재가": current_price,
            "판단": status_map[int(prediction)],
            "LONG": f"{probabilities[1]:.8f}",
            "SHORT": f"{probabilities[2]:.8f}",
            "NEUTRAL": f"{probabilities[0]:.8f}",
            "지표": indicators_str
        }])
        
        header = not os.path.exists(LEARNING_LOG)
        log_df.to_csv(LEARNING_LOG, mode='a', index=False, header=header, encoding='utf-8-sig')
        
    except Exception as e:
        return f"⚠️ **[AI 분석 오류]** {e}"
    
    # 동적 문턱값 계산 (VIX 등 반영)
    dynamic_threshold = CONF_THRESHOLD
    last_vix = df_last.get('VIX', pd.Series([0])).iloc[-1]
    if last_vix > 25:
        dynamic_threshold -= 0.05
        print(f"⚠️ 매크로 위기 감지 (VIX:{last_vix:.1f}) - 문턱값 하향: {dynamic_threshold:.2f}")

    is_exited = False
    
    # 2. 기존 포지션 관리
    if state["current_pos"] != 0:
        if state["current_pos"] == 1: # Long
            current_pnl = (current_price / state["entry_price"] - 1) * LEVERAGE
            side_str = "LONG"
        else: # Short
            current_pnl = (1 - current_price / state["entry_price"]) * LEVERAGE
            side_str = "SHORT"
            
        state["peak_pnl"] = max(state.get("peak_pnl", -999), current_pnl)
        
        # 종료 조건 체크 (SL/TS)
        exit_action = None
        if current_pnl <= -SL_THRESHOLD:
            exit_action = "EXIT(SL)"
        elif state["peak_pnl"] >= TS_ACTIVATION and current_pnl <= (state["peak_pnl"] - TS_CALLBACK):
            exit_action = "EXIT(TS)"
            
        if exit_action:
            pnl_amount = state["balance"] * current_pnl
            risk_mgr.update_balance(pnl_amount)
            log_virtual_trade(exit_action, symbol, side_str, current_price, current_pnl, risk_mgr.current_balance)
            state["current_pos"] = 0
            is_exited = True

    # 3. 신규 진입 및 스위칭
    if not is_exited:
        if probabilities[int(prediction)] >= dynamic_threshold:
            if prediction != 0 and prediction != state["current_pos"]:
                # 스위칭 시 기존 포지션 종료
                if state["current_pos"] != 0:
                    if state["current_pos"] == 1:
                        pnl = (current_price / state["entry_price"] - 1) * LEVERAGE
                        side_old = "LONG"
                    else:
                        pnl = (1 - current_price / state["entry_price"]) * LEVERAGE
                        side_old = "SHORT"
                    pnl_amount = state["balance"] * pnl
                    risk_mgr.update_balance(pnl_amount)
                    log_virtual_trade("EXIT(SWITCH)", symbol, side_old, current_price, pnl, risk_mgr.current_balance)
                
                # 진입 전 리스크 매니저 기반 수량 계산 (로깅용)
                qty = risk_mgr.calculate_position_size(current_price, SL_THRESHOLD)
                
                state["current_pos"] = int(prediction)
                state["entry_price"] = current_price
                state["entry_time"] = datetime.now().isoformat()
                state["peak_pnl"] = -999
                side_new = "LONG" if state["current_pos"] == 1 else "SHORT"
                log_virtual_trade("ENTRY", symbol, side_new, current_price, 0, risk_mgr.current_balance)
                print(f"🚀 신규 진입: {side_new} (수량: {qty:.2f})")

    # AGENT TASK 6: 24봉마다 성과 지표 출력
    if state["loop_count"] % 24 == 0:
        perf = tracker.get_performance_summary()
        if perf:
            print("\n" + "="*40)
            print(f"📊 [정기 보고 - {state['loop_count']}봉]")
            print(f"- 누적 수익률: {perf['total_return']:.2%}")
            print(f"- 샤프 비율: {perf['sharpe_ratio']:.2f}")
            print(f"- MDD: {perf['mdd']:.2%}")
            print(f"- 승률: {perf['win_rate']:.2%}")
            print(f"- 손익비: {perf['profit_factor']:.2f}")
            print("="*40 + "\n")

    # AGENT TASK 7: 재학습 트리거 체크
    recent_acc = tracker.get_recent_accuracy(window=50)
    # (1) 매 168봉(7일)마다 자동 재학습
    # (2) 최근 50봉 정확도 45% 미만 시 즉시 재학습
    if (state["loop_count"] % 168 == 0) or (recent_acc is not None and recent_acc < 0.45):
        reason = "주기적 재학습" if state["loop_count"] % 168 == 0 else f"정확도 저하 ({recent_acc:.1%})"
        print(f"🔄 재학습 조건 충족: {reason}")
        run_retraining()

    save_bot_state(state)
    return "NO_REPLY"

def run_once():
    msg = run_virtual_bot_cycle()
    if msg != "NO_REPLY":
        print(msg)

if __name__ == "__main__":
    import sys
    if "--once" in sys.argv:
        run_once()
    else:
        while True:
            try:
                msg = run_virtual_bot_cycle()
                if msg != "NO_REPLY":
                    print(msg)
                time.sleep(60) 
            except KeyboardInterrupt:
                break
            except Exception as e:
                print(f"루프 에러: {e}")
                time.sleep(60)
