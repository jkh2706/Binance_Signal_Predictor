import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta

import os
from dotenv import load_dotenv

# 페이지 설정
st.set_page_config(page_title="CHLOE | Trading Dashboard V2.8", layout="wide", page_icon="🎯")

# 환경 변수 로드
load_dotenv()
SHEET_ID = os.getenv("GOOGLE_SHEET_ID", "")

if not SHEET_ID:
    st.error("❌ .env 파일에 GOOGLE_SHEET_ID가 설정되지 않았습니다.")
    st.stop()

# 스타일 설정
st.markdown("""
    <style>
    .main { background-color: #0e1117; color: white; }
    .stMetric { background-color: #1e2130; padding: 20px; border-radius: 12px; border: 1px solid #3e4150; }
    div[data-testid="stMetricValue"] { font-size: 1.8rem; font-weight: 700; color: #00CC96; }
    </style>
    """, unsafe_allow_html=True)

CSV_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv"

@st.cache_data(ttl=15)
def load_data():
    try:
        df = pd.read_csv(CSV_URL)
        if df.empty:
            return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()
        
        # 유니버설 12컬럼 포맷 (롤백 이후에도 호환성 유지)
        # Type, Time, Symbol, Action, Side, Price, Qty, PnL, Fee, Balance, Extra1, Extra2
        cols = ["Type", "Time", "Symbol", "Action", "Side", "Price", "Qty", "PnL", "Fee", "Balance", "Extra1", "Extra2"]
        
        # 컬럼 수 보정
        while len(df.columns) < 12:
            df[f"Col_{len(df.columns)}"] = "-"
        
        df = df.iloc[:, :12]
        df.columns = cols

        # 시간 보정 (KST)
        df['Time'] = pd.to_datetime(df['Time'].astype(str).str.replace("'", ""), errors='coerce')
        df = df.dropna(subset=['Time'])
        
        # 숫자 전처리
        for col in ['Price', 'Qty', 'PnL', 'Fee', 'Balance']:
            df[col] = df[col].astype(str).str.replace('%', '').str.replace('+', '').str.replace(',', '').str.strip()
            df.loc[df[col] == '-', col] = '0'
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

        df_real = df[df['Type'] == "REAL"].drop_duplicates(subset=['Extra2'], keep='first').copy()
        df_virt = df[df['Type'] == "VIRT"].copy()
        df_ai = df[df['Type'] == "AI"].copy()
        
        if not df_ai.empty:
            df_ai['AI_판단'] = df_ai['Side']
            
        return df_real, df_virt, df_ai
    except Exception as e:
        st.error(f"Sync Error: {e}")
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

st.title("🎯 트레이딩 마스터 대시보드 V2.8 (Restored)")
st.caption("실시간 데이터 통합 관제 센터")

df_real, df_virt, df_ai = load_data()

tab1, tab2, tab3 = st.tabs(["💰 실전 매매 현황", "🧪 AI 가상 실험실", "📡 실시간 시그널"])

with tab1:
    if not df_real.empty:
        c1, c2, c3 = st.columns(3)
        with c1: st.metric("누적 수익", f"{df_real['PnL'].sum():,.2f} XRP")
        with c2: st.metric("최근 거래가", f"${df_real['Price'].iloc[-1]:,.4f}")
        with c3: st.metric("현재 포지션", f"{df_real['Balance'].iloc[-1]:,.2f}")
        
        st.subheader("📈 실전 수익 곡선")
        df_real['CumPnL'] = df_real['PnL'].cumsum()
        st.plotly_chart(px.line(df_real, x='Time', y='CumPnL', template="plotly_dark", color_discrete_sequence=['#00CC96']), use_container_width=True)
        st.dataframe(df_real.sort_values('Time', ascending=False), use_container_width=True)
    else:
        st.info("실전 매매 데이터를 기다리고 있습니다.")

with tab2:
    if not df_virt.empty:
        st.subheader("🤖 가상 자산 변화")
        st.plotly_chart(px.area(df_virt, x='Time', y='Balance', template="plotly_dark"), use_container_width=True)
        st.dataframe(df_virt.sort_values('Time', ascending=False), use_container_width=True)
    else:
        st.info("가상 매매 데이터가 없습니다.")

with tab3:
    if not df_ai.empty:
        st.subheader("📡 AI 확신도 변화")
        
        def parse_probs(row):
            try:
                parts = str(row['Extra2']).split('/')
                l = float(parts[0].split(':')[1])
                s = float(parts[1].split(':')[1])
                n = float(parts[2].split(':')[1])
                return pd.Series([l, s, n])
            except: return pd.Series([None, None, None])
            
        prob_df = df_ai.tail(50).apply(parse_probs, axis=1)
        prob_df.columns = ['LONG', 'SHORT', 'NEUTRAL']
        prob_df['Time'] = df_ai.tail(50)['Time']
        st.plotly_chart(px.line(prob_df.dropna(), x='Time', y=['LONG', 'SHORT', 'NEUTRAL'], 
                               color_discrete_map={'LONG':'#00CC96', 'SHORT':'#EF553B', 'NEUTRAL':'#636EFA'},
                               template="plotly_dark"), use_container_width=True)
        
        st.subheader("📝 판단 근거 로그")
        st.table(df_ai.sort_values('Time', ascending=False).head(10)[['Time', 'AI_판단', 'Extra1', 'Extra2']])
    else:
        st.info("AI 시그널 대기 중...")
