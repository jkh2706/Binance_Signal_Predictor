import streamlit as st
import pandas as pd
import requests
import os
from datetime import datetime, timedelta
import plotly.express as px
import plotly.graph_objects as go
from dotenv import load_dotenv

# [V7.0] VM 서버 전용 로컬 대시보드 - 클라우드/구글시트 의존성 완전 제거
st.set_page_config(page_title="클로이 AI 로컬 관제 센터", layout="wide", page_icon="🖥️")

# 1. 로컬 데이터 경로 설정
WORKSPACE_DIR = "/home/jeong-kihun/.openclaw/workspace"
REAL_CSV = os.path.join(WORKSPACE_DIR, "Trading_report_binance/trades_ws_v2.csv")
AI_CSV = os.path.join(WORKSPACE_DIR, "Binance_Signal_Predictor/ai_decision_log.csv")
VIRT_CSV = os.path.join(WORKSPACE_DIR, "Binance_Signal_Predictor/virtual_trades.csv")

# 2. 시인성 극대화 스타일 (VM 전용)
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;700;900&family=Noto+Sans+KR:wght@400;700&display=swap');
    html, body, [class*="css"] { font-family: 'Inter', 'Noto Sans KR', sans-serif; }
    .main { background-color: #0d1117; color: #c9d1d9; }
    [data-testid="stMetric"] { background: #161b22; border: 1px solid #30363d; padding: 1.5rem !important; border-radius: 12px !important; }
    [data-testid="stMetricValue"] { color: #58a6ff !important; font-size: 2.2rem !important; font-weight: 800 !important; }
    [data-testid="stMetricLabel"] { color: #8b949e !important; font-size: 1rem !important; font-weight: 600 !important; }
    .stDataFrame { border: 1px solid #30363d; border-radius: 8px; }
    </style>
    """, unsafe_allow_html=True)

# 3. 데이터 로드 로직 (로컬 파일 직접 읽기)
def load_csv(path, date_col=None):
    if not os.path.exists(path): return pd.DataFrame()
    try:
        # AI 로그의 경우 헤더 유무 및 Comma 이슈 대응을 위해 on_bad_lines='skip' 사용
        df = pd.read_csv(path, on_bad_lines='skip').fillna("-")
        if date_col and date_col in df.columns:
            df[date_col] = pd.to_datetime(df[date_col].astype(str).str.replace("'", ""), errors='coerce')
            df = df.dropna(subset=[date_col]).sort_values(date_col)
        return df
    except: return pd.DataFrame()

# 4. 실시간 가격 (바이낸스 공용 API)
def get_live_price():
    try:
        r = requests.get("https://api.binance.com/api/v3/ticker/price?symbol=XRPUSDT", timeout=2)
        return float(r.json()['price'])
    except: return 0.0

# --- 헤더 ---
st.title("🖥️ VM 로컬 트레이딩 관제 센터 (V7.0)")
st.caption(f"구글 시트/스트림릿 클라우드 미사용 | 서버 내부 데이터 직접 연동 중")

price = get_live_price()
df_real = load_csv(REAL_CSV, "시간(KST)")
df_ai = load_csv(AI_CSV, "시간(KST)")
df_virt = load_csv(VIRT_CSV, "시간(KST)")

# 상단 지표
col1, col2, col3 = st.columns(3)
with col1:
    st.metric("실시간 XRP 시세", f"${price:,.4f}" if price > 0 else "연결 확인 중")
with col2:
    if not df_real.empty:
        # '실현손익' 컬럼 합계
        pnl_sum = pd.to_numeric(df_real['실현손익'].astype(str).str.replace('[+%,]', '', regex=True), errors='coerce').sum()
        st.metric("실전 누적 수익", f"{pnl_sum:,.2f} XRP")
    else:
        st.metric("실전 누적 수익", "0.00 XRP")
with col3:
    if not df_real.empty:
        pos_amt = df_real['포지션수량'].iloc[-1]
        st.metric("현재 포지션", f"{pos_amt:,.1f} XRP")
    else:
        st.metric("현재 포지션", "0.0 XRP")

st.divider()

# 메인 콘텐츠
t1, t2, t3 = st.tabs(["💰 실전 매매 (LOCAL)", "📡 AI 분석 (REAL-TIME)", "🧪 가상 매매"])

with t1:
    if not df_real.empty:
        # 수익 곡선
        df_real['CumPnL'] = pd.to_numeric(df_real['실현손익'].astype(str).str.replace('[+%,]', '', regex=True), errors='coerce').cumsum()
        st.plotly_chart(px.line(df_real, x='시간(KST)', y='CumPnL', template="plotly_dark", title="Profit Evolution"), use_container_width=True)
        st.dataframe(df_real.sort_values('시간(KST)', ascending=False), use_container_width=True)
    else:
        st.info("로컬 매매 파일(trades_ws_v2.csv)을 찾을 수 없습니다.")

with t2:
    if not df_ai.empty:
        st.subheader("최근 AI 판단 로그 (XGBoost)")
        # 확률 분포 시각화
        def parse_probs(row):
            try:
                # 7컬럼 혹은 8컬럼 대응
                return pd.Series([float(row['LONG_확률']), float(row['SHORT_확률']), float(row['NEUTRAL_확률'])])
            except: return pd.Series([0.0, 0.0, 0.0])
        
        prob_df = df_ai.tail(50).copy()
        if 'LONG_확률' in prob_df.columns:
            st.plotly_chart(px.line(prob_df, x='시간(KST)', y=['LONG_확률', 'SHORT_확률', 'NEUTRAL_확률'], 
                                   color_discrete_map={'LONG_확률': '#00CC96', 'SHORT_확률': '#EF553B', 'NEUTRAL_확률': '#636EFA'},
                                   template="plotly_dark"), use_container_width=True)
        
        st.dataframe(df_ai.sort_values('시간(KST)', ascending=False).head(100), use_container_width=True)
    else:
        st.info("AI 로그 파일(ai_decision_log.csv)이 비어있습니다.")

with t3:
    if not df_virt.empty:
        st.subheader("가상 트레이딩 계좌")
        st.dataframe(df_virt.sort_values('시간(KST)', ascending=False), use_container_width=True)

# 자동 갱신 설정 (로컬 서버이므로 할당량 걱정 없음)
if st.sidebar.button("♻️ 즉시 갱신"):
    st.rerun()
st.sidebar.write(f"서버 가동 시간: {datetime.now().strftime('%H:%M:%S')}")
