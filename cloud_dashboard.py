import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
import os
from dotenv import load_dotenv

# 페이지 설정
st.set_page_config(page_title="CHLOE | Trading Dashboard V3.2", layout="wide", page_icon="🎯")

load_dotenv()
SHEET_ID = os.getenv("GOOGLE_SHEET_ID", "1xQuz_k_FjE1Mjo0R21YS49Pr3ZNpG3yPTofzYyNSbuk")

# 구글 시트 CSV URL (gid=0)
CSV_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid=0"

@st.cache_data(ttl=5)
def load_data():
    try:
        # 데이터 로드
        df = pd.read_csv(CSV_URL, dtype=str).fillna("-")
        if df.empty: return None, None, None
        
        # 헤더 정리
        if df.iloc[0, 0] == "Type":
            df = df.iloc[1:].reset_index(drop=True)
            
        # 12컬럼 구조 보장
        cols = ["Type", "Time", "Symbol", "Action", "Side", "Price", "Qty", "PnL", "Fee", "Balance", "Extra1", "Extra2"]
        df = df.iloc[:, :12]
        df.columns = cols

        # 시간 파싱
        def parse_dt(t):
            try:
                s = str(t).replace("'", "").strip()
                return pd.to_datetime(s)
            except: return pd.NaT

        df['Time'] = df['Time'].apply(parse_dt)
        df = df.dropna(subset=['Time']).sort_values('Time')
        
        # 숫자 변환
        for col in ['Price', 'Qty', 'PnL', 'Fee', 'Balance']:
            df[col] = pd.to_numeric(df[col].str.replace('[+%,]', '', regex=True), errors='coerce').fillna(0.0)

        # 데이터 그룹화
        reals = df[df['Type'] == "REAL"].drop_duplicates(subset=['Extra2'], keep='last').copy()
        virts = df[df['Type'] == "VIRT"].copy()
        signals = df[df['Type'] == "AI"].copy()
        
        return reals, virts, signals
    except Exception as e:
        st.error(f"Sync Error: {e}")
        return None, None, None

st.title("🎯 트레이딩 마스터 대시보드 V3.2")
st.caption(f"Last Sync: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} (KST)")

df_r, df_v, df_s = load_data()

if st.sidebar.button("♻️ Force Sync"):
    st.cache_data.clear()
    st.rerun()

t1, t2, t3 = st.tabs(["💰 실전 매매", "🧪 가상 매매", "📡 AI 시그널"])

with t3:
    if df_s is not None and not df_s.empty:
        st.subheader("📈 AI 확신도 실시간 변화 (최근 100건)")
        
        def parse_ai_probs(row):
            try:
                # 'L:0.XX/S:0.XX/N:0.XX' 파싱
                txt = str(row['Extra2'])
                parts = txt.split('/')
                res = {'L': None, 'S': None, 'N': None}
                for p in parts:
                    if ':' not in p: continue
                    k, v = p.split(':', 1)
                    k_up = k.strip().upper()
                    if 'L' in k_up: res['L'] = float(v)
                    elif 'S' in k_up: res['S'] = float(v)
                    elif 'N' in k_up: res['N'] = float(v)
                return pd.Series([res['L'], res['S'], res['N']])
            except: return pd.Series([None, None, None])
            
        prob_df = df_s.tail(100).copy()
        parsed_data = prob_df.apply(parse_ai_probs, axis=1)
        prob_df[['LONG', 'SHORT', 'NEUTRAL']] = parsed_data
        
        # 유효한 숫자 데이터만 필터링
        chart_df = prob_df.dropna(subset=['LONG', 'SHORT', 'NEUTRAL'])
        if not chart_df.empty:
            fig = px.line(chart_df, x='Time', y=['LONG', 'SHORT', 'NEUTRAL'],
                         color_discrete_map={'LONG': '#00CC96', 'SHORT': '#EF553B', 'NEUTRAL': '#636EFA'},
                         template="plotly_dark")
            fig.update_layout(height=400, margin=dict(l=0, r=0, t=20, b=0))
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.warning("유효한 확률 데이터가 없습니다. 시트를 확인해 주세요.")
        
        st.subheader("📝 판단 근거 로그")
        st.dataframe(df_s.sort_values('Time', ascending=False).head(50)[['Time', 'Side', 'Extra1', 'Extra2']], use_container_width=True)
    else:
        st.info("AI 데이터를 불러오는 중...")

with t1:
    if df_r is not None and not df_r.empty:
        st.plotly_chart(px.line(df_r, x='Time', y=df_r['PnL'].cumsum(), title="Cumulative Profit (XRP)", template="plotly_dark"), use_container_width=True)
        st.dataframe(df_r.sort_values('Time', ascending=False), use_container_width=True)

with t2:
    if df_v is not None and not df_v.empty:
        st.plotly_chart(px.area(df_v, x='Time', y='Balance', title="Virtual Account Trend (USD)", template="plotly_dark"), use_container_width=True)
        st.dataframe(df_v.sort_values('Time', ascending=False), use_container_width=True)
