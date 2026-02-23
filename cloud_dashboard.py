import streamlit as st
import pandas as pd
import requests
import os
from datetime import datetime, timedelta
import plotly.express as px
import plotly.graph_objects as go
from dotenv import load_dotenv

# [V6.0] VM 기반 데이터 연동 및 클라우드 배포 최적화 버전
st.set_page_config(page_title="CHLOE AI Premium", layout="wide", page_icon="💎")

load_dotenv()
SHEET_ID = os.getenv("GOOGLE_SHEET_ID", "1xQuz_k_FjE1Mjo0R21YS49Pr3ZNpG3yPTofzYyNSbuk")
CSV_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid=0"

# 1. 시인성 강화 스타일
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;700;900&family=Noto+Sans+KR:wght@400;700&display=swap');
    html, body, [class*="css"] { font-family: 'Inter', 'Noto Sans KR', sans-serif; }
    .main { background-color: #05070a; }
    [data-testid="stMetric"] { background: #11151c; border: 2px solid #22272e; padding: 1.5rem !important; border-radius: 16px !important; }
    [data-testid="stMetricValue"] { color: #58a6ff !important; font-size: 2.2rem !important; font-weight: 800 !important; }
    [data-testid="stMetricLabel"] { color: #adbac7 !important; font-size: 1rem !important; font-weight: 600 !important; }
    </style>
    """, unsafe_allow_html=True)

# 2. 데이터 로드 (최대한 안정적인 구조)
@st.cache_data(ttl=10)
def load_data():
    try:
        df = pd.read_csv(CSV_URL, dtype=str).fillna("-")
        if df.empty: return None
        if df.iloc[0, 0] == "Type": df = df.iloc[1:].reset_index(drop=True)
        cols = ["Type", "Time", "Symbol", "Action", "Side", "Price", "Qty", "PnL", "Fee", "Balance", "Extra1", "Extra2"]
        df = df.iloc[:, :12]
        df.columns = cols
        df['Time'] = pd.to_datetime(df['Time'].str.replace("'", ""), errors='coerce')
        df = df.dropna(subset=['Time']).sort_values('Time')
        for c in ["Price", "Qty", "PnL", "Fee", "Balance"]:
            df[c] = pd.to_numeric(df[c].str.replace('[+%,]', '', regex=True), errors='coerce').fillna(0.0)
        return df
    except: return None

# 3. 바이낸스 실시간 가격 (가장 검증된 공용 API)
def get_live_price():
    try:
        r = requests.get("https://api.binance.com/api/v3/ticker/price?symbol=XRPUSDT", timeout=5)
        return float(r.json()['price'])
    except: return 0.0

# --- 화면 구성 ---
st.title("💎 CHLOE AI 프리미엄 트레이딩 관제 센터")
st.caption(f"시스템 버전: V6.0 (VM-Sync Optimized) | {datetime.now().strftime('%H:%M:%S')} (KST)")

price = get_live_price()
full_df = load_data()

if full_df is not None:
    reals = full_df[full_df['Type'] == "REAL"].copy()
    
    # 상단 대형 지표
    m1, m2, m3 = st.columns(3)
    with m1:
        st.metric("실시간 XRP 가격", f"${price:,.4f}" if price > 0 else "데이터 지연")
    with m2:
        total_pnl = reals['PnL'].sum()
        st.metric("실전 누적 수익", f"{total_pnl:,.2f} XRP", delta=f"{total_pnl:,.2f}")
    with m3:
        current_pos = reals['Balance'].iloc[-1] if not reals.empty else 0
        st.metric("현재 포지션", f"{current_pos:,.1f} XRP")

    # 탭 메뉴
    t1, t2, t3 = st.tabs(["💰 실전 매매 현황", "📡 AI 분석 엔진", "🧪 가상 시뮬레이션"])

    with t1:
        st.plotly_chart(px.line(reals, x='Time', y=reals['PnL'].cumsum(), template="plotly_dark", title="Revenue Curve"), use_container_width=True)
        st.dataframe(reals.sort_values('Time', ascending=False), use_container_width=True)

    with t2:
        signals = full_df[full_df['Type'] == "AI"].tail(100).copy()
        st.subheader("AI Decision History")
        st.dataframe(signals.sort_values('Time', ascending=False), use_container_width=True)

    with t3:
        virts = full_df[full_df['Type'] == "VIRT"].copy()
        if not virts.empty:
            st.metric("가상 잔고 (VIRT)", f"${virts['Balance'].iloc[-1]:,.2f}")
            st.plotly_chart(px.area(virts, x='Time', y='Balance', template="plotly_dark"), use_container_width=True)
else:
    st.error("구글 시트 데이터 로드에 실패했습니다. 공유 설정을 확인해 주세요.")

if st.sidebar.button("♻️ 데이터 강제 새로고침"):
    st.cache_data.clear()
    st.rerun()
