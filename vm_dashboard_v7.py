import streamlit as st
import pandas as pd
import requests
import os
from datetime import datetime, timedelta
import plotly.express as px
import plotly.graph_objects as go
from dotenv import load_dotenv

# [V7.2] AI 알고리즘 판단 정밀 반영 및 가상 계좌 그래프 추가
st.set_page_config(page_title="클로이 AI 프리미엄 관제", layout="wide", page_icon="💎")

WORKSPACE_DIR = "/home/jeong-kihun/.openclaw/workspace"
REAL_CSV = os.path.join(WORKSPACE_DIR, "Trading_report_binance/trades_ws_v2.csv")
AI_CSV = os.path.join(WORKSPACE_DIR, "Binance_Signal_Predictor/ai_decision_log.csv")
VIRT_CSV = os.path.join(WORKSPACE_DIR, "Binance_Signal_Predictor/virtual_trades.csv")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;700;900&family=Noto+Sans+KR:wght@400;700&display=swap');
    html, body, [class*="css"] { font-family: 'Inter', 'Noto Sans KR', sans-serif; }
    .main { background-color: #05070a; color: #e6edf3; }
    [data-testid="stMetric"] { background: #0d1117; border: 1px solid #30363d; padding: 1.5rem !important; border-radius: 12px !important; }
    [data-testid="stMetricValue"] { color: #58a6ff !important; font-size: 2.2rem !important; font-weight: 800 !important; }
    [data-testid="stMetricLabel"] { color: #8b949e !important; font-size: 1rem !important; }
    .stDataFrame { border: 1px solid #30363d; border-radius: 8px; }
    </style>
    """, unsafe_allow_html=True)

def load_ai_log(path):
    if not os.path.exists(path): return pd.DataFrame()
    try:
        import csv
        with open(path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        data = []
        for line in lines:
            parts = [p.strip() for p in line.strip().split(',')]
            if len(parts) >= 7 and parts[0] != "시간(KST)":
                # [V7.2 최신화] ai_decision_log.csv 헤더 순서 대응
                # 로그 파일 컬럼 순서: 시간, 심볼, 가격, 판단, LONG_확률, SHORT_확률, NEUTRAL_확률
                data.append(parts[:8] if len(parts) >= 8 else parts + ["-"])
        
        cols = ["시간(KST)", "심볼", "현재가", "판단", "LONG", "SHORT", "NEUTRAL", "지표"]
        df = pd.DataFrame(data, columns=cols)
        df['시간(KST)'] = pd.to_datetime(df['시간(KST)'], errors='coerce')
        df = df.dropna(subset=['시간(KST)']).sort_values('시간(KST)')
        
        for c in ["현재가", "NEUTRAL", "LONG", "SHORT"]:
            df[c] = pd.to_numeric(df[c], errors='coerce').fillna(0.0)
            
        return df
    except: return pd.DataFrame()

def load_simple_csv(path, date_col):
    if not os.path.exists(path): return pd.DataFrame()
    try:
        df = pd.read_csv(path)
        df[date_col] = pd.to_datetime(df[date_col].astype(str).str.replace("'", ""), errors='coerce')
        return df.dropna(subset=[date_col]).sort_values(date_col).fillna("-")
    except: return pd.DataFrame()

def get_live_price():
    try:
        r = requests.get("https://api.binance.com/api/v3/ticker/price?symbol=XRPUSDT", timeout=2)
        return float(r.json()['price'])
    except: return 0.0

st.title("💎 CHLOE AI 프리미엄 관제 센터 (V7.2)")
st.caption(f"Last Check: {datetime.now().strftime('%H:%M:%S')} (KST)")

price = get_live_price()
df_ai = load_ai_log(AI_CSV)
df_real = load_simple_csv(REAL_CSV, "시간(KST)")

c1, c2, c3 = st.columns(3)
with c1: st.metric("XRP 실시간 시세", f"${price:,.4f}" if price > 0 else "연결 중")
with c2:
    if not df_real.empty:
        pnl = pd.to_numeric(df_real['실현손익'].astype(str).str.replace('[+%,]', '', regex=True), errors='coerce').sum()
        st.metric("실전 누적 수익", f"{pnl:,.2f} XRP")
with c3:
    if not df_ai.empty:
        last_dt = df_ai['시간(KST)'].iloc[-1].strftime('%H:%M:%S')
        st.metric("최근 AI 분석 시각", last_dt, delta="Active")

tab1, tab2, tab3 = st.tabs(["📡 AI 실시간 분석", "💰 실전 매매 기록", "🧪 가상 계좌"])

with tab1:
    if not df_ai.empty:
        st.subheader("📊 AI 포지션 확신도 추이 (최근 100건)")
        fig = px.line(df_ai.tail(100), x='시간(KST)', y=['LONG', 'SHORT', 'NEUTRAL'],
                     color_discrete_map={'LONG': '#00CC96', 'SHORT': '#EF553B', 'NEUTRAL': '#636EFA'},
                     template="plotly_dark")
        fig.update_layout(margin=dict(l=0, r=0, t=30, b=0), height=400)
        st.plotly_chart(fig, use_container_width=True)
        st.dataframe(df_ai.sort_values('시간(KST)', ascending=False).head(100), use_container_width=True)
    else:
        st.info("AI 데이터를 불러올 수 없습니다.")

with tab2:
    if not df_real.empty:
        st.dataframe(df_real.sort_values('시간(KST)', ascending=False), use_container_width=True)

with tab3:
    st.subheader("🧪 가상 계좌 수익률 현황")
    df_virt = load_simple_csv(VIRT_CSV, "시간(KST)")
    if not df_virt.empty:
        # 잔고 컬럼을 숫자로 변환
        df_virt['잔고_num'] = pd.to_numeric(df_virt['잔고(XRP)'], errors='coerce')
        fig_pnl = px.line(df_virt, x='시간(KST)', y='잔고_num', 
                         title="가상 매매 누적 잔고 (XRP)",
                         template="plotly_dark",
                         color_discrete_sequence=['#FFD700'])
        fig_pnl.update_layout(yaxis_title="Balance (XRP)")
        st.plotly_chart(fig_pnl, use_container_width=True)
        
        st.dataframe(df_virt.sort_values('시간(KST)', ascending=False), use_container_width=True)
    else:
        st.info("가상 매매 기록이 없습니다.")

if st.sidebar.button("♻️ 데이터 강제 새로고침"):
    st.cache_data.clear()
    st.rerun()
