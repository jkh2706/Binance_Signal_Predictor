import streamlit as st
import pandas as pd
import requests
import os
from datetime import datetime, timedelta
import plotly.express as px
import plotly.graph_objects as go
from dotenv import load_dotenv

# 1. 시스템 설정
st.set_page_config(page_title="CHLOE AI Premium Dashboard", layout="wide", page_icon="💎")
load_dotenv()

# 2. 고정 경로 및 설정
WORKSPACE_DIR = "/home/jeong-kihun/.openclaw/workspace"
REAL_TRADES_CSV = os.path.join(WORKSPACE_DIR, "Trading_report_binance/trades_ws_v2.csv")
AI_LOG_CSV = os.path.join(WORKSPACE_DIR, "Binance_Signal_Predictor/ai_decision_log.csv")
VIRT_TRADES_CSV = os.path.join(WORKSPACE_DIR, "Binance_Signal_Predictor/virtual_trades.csv")

# 3. 데이터 로드 로직 (VM 로컬 파일 우선)
def load_local_data(file_path, type_label):
    if not os.path.exists(file_path):
        return pd.DataFrame()
    try:
        # AI 로그의 경우 콤마 파싱 이슈 대응
        if "ai_decision_log" in file_path:
            import csv
            with open(file_path, 'r', encoding='utf-8') as f:
                reader = csv.reader(f)
                data = list(reader)
            if not data: return pd.DataFrame()
            header = data[0]
            # 헤더가 '시간(KST)'로 시작하지 않으면 데이터로 간주
            if header[0] != "시간(KST)":
                df = pd.DataFrame(data)
            else:
                df = pd.DataFrame(data[1:], columns=header)
        else:
            df = pd.read_csv(file_path).fillna("-")
        
        df['Type'] = type_label
        return df
    except Exception as e:
        st.error(f"Error loading {type_label}: {e}")
        return pd.DataFrame()

# 4. 실시간 가격 조회 (바이낸스 공용 API)
def get_binance_price(symbol="XRPUSDT"):
    try:
        r = requests.get(f"https://api.binance.com/api/v3/ticker/price?symbol={symbol}", timeout=3)
        return float(r.json()['price'])
    except:
        return 0.0

# --- 메인 화면 구성 ---
st.title("💎 CHLOE AI 프리미엄 트레이딩 관제 센터")
st.markdown("---")

# 실시간 가격 및 지표 (최상단)
price = get_binance_price()
df_real = load_local_data(REAL_TRADES_CSV, "REAL")

c1, c2, c3 = st.columns(3)
with c1:
    if price > 0:
        st.metric("실시간 XRP 가격", f"${price:,.4f}")
    else:
        st.warning("가격 데이터 수신 중...")

with c2:
    if not df_real.empty:
        # 실전 매매 수익 컬럼 (인덱스 7 또는 이름 '실현손익')
        pnl_col = '실현손익' if '실현손익' in df_real.columns else df_real.columns[6]
        total_pnl = pd.to_numeric(df_real[pnl_col].astype(str).str.replace('[+%,]', '', regex=True), errors='coerce').sum()
        st.metric("실전 누적 수익", f"{total_pnl:,.2f} XRP")

with c3:
    st.metric("시스템 상태", "운영 중 (VM)", delta="Stable")

# 탭 구성
t1, t2, t3 = st.tabs(["💰 실전 매매", "📡 AI 실시간 시그널", "🧪 가상 실험실"])

with t1:
    if not df_real.empty:
        st.subheader("최근 실전 매매 기록 (VM 로컬 데이터)")
        st.dataframe(df_real.tail(50), use_container_width=True)
    else:
        st.info("실전 매매 기록이 없습니다.")

with t2:
    df_ai = load_local_data(AI_LOG_CSV, "AI")
    if not df_ai.empty:
        st.subheader("AI 판단 로그 및 확률 추이")
        # 확률 파싱 및 시각화 로직 추가 가능
        st.dataframe(df_ai.tail(50), use_container_width=True)
    else:
        st.info("AI 로그 데이터를 불러올 수 없습니다.")

with t3:
    df_virt = load_local_data(VIRT_TRADES_CSV, "VIRT")
    if not df_virt.empty:
        st.subheader("가상 매매 결과")
        st.dataframe(df_virt.tail(50), use_container_width=True)
    else:
        st.info("가상 매매 데이터가 없습니다.")

# 사이드바 제어
st.sidebar.header("⚙️ 시스템 설정")
if st.sidebar.button("♻️ 데이터 강제 갱신"):
    st.rerun()

st.sidebar.markdown("---")
st.sidebar.write(f"서버 시각: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
