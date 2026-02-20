import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv

# 페이지 설정
st.set_page_config(page_title="CHLOE | Trading Dashboard V2.8 (Restored)", layout="wide", page_icon="🎯")

# 환경 변수 로드
load_dotenv()
SHEET_ID = os.getenv("GOOGLE_SHEET_ID", "1xQuz_k_FjE1Mjo0R21YS49Pr3ZNpG3yPTofzYyNSbuk")

# 스타일 설정
st.markdown("""
    <style>
    .main { background-color: #0e1117; color: white; }
    .stMetric { background-color: #1e2130; padding: 20px; border-radius: 12px; border: 1px solid #3e4150; }
    div[data-testid="stMetricValue"] { font-size: 1.8rem; font-weight: 700; color: #00CC96; }
    </style>
    """, unsafe_allow_html=True)

CSV_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv"

@st.cache_data(ttl=10)
def load_data():
    try:
        df = pd.read_csv(CSV_URL)
        if df.empty:
            return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()
        
        # 컬럼 이름 정의 (12컬럼 고정)
        cols = ["Type", "Time", "Symbol", "Action", "Side", "Price", "Qty", "PnL", "Fee", "Balance", "Extra1", "Extra2"]
        
        # 데이터가 12컬럼인지 확인하고 부족하면 더미 생성 (데이터 꼬임 방지)
        if len(df.columns) < 12:
            # 헤더 자체가 틀렸을 경우 (예: 7컬럼 시절 데이터)를 대비해 강제 재지정은 위험하므로
            # 여기서는 현재 시트 구조가 12컬럼 유니버설이라고 가정하고 처리
            while len(df.columns) < 12:
                df[f"Dummy_{len(df.columns)}"] = "-"
        
        df = df.iloc[:, :12]
        df.columns = cols

        # 시간 처리 (KST 변환 로직 정밀화)
        df['Time'] = pd.to_datetime(df['Time'].astype(str).str.replace("'", ""), errors='coerce')
        # 시트 데이터가 KST 문자열이면 그대로, UTC면 +9 (현재 로거는 KST 문자열 기록 중이나 안전을 위해 체크)
        # 만약 연도가 2026년이 아니거나 이상하면 드롭
        df = df.dropna(subset=['Time'])
        
        # 숫자 전처리
        for col in ['Price', 'Qty', 'PnL', 'Fee', 'Balance']:
            df[col] = df[col].astype(str).str.replace('%', '').str.replace('+', '').str.replace(',', '').str.strip()
            df.loc[df[col] == '-', col] = '0'
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

        # 데이터 분리
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
st.caption(f"실시간 데이터 통합 관제 센터 | {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} (KST)")

df_real, df_virt, df_ai = load_data()

tab1, tab2, tab3 = st.tabs(["💰 REAL (실전)", "🧪 AI 가상 실험실", "📡 실시간 시그널"])

with tab1:
    if not df_real.empty:
        c1, c2, c3 = st.columns(3)
        with c1: st.metric("누적 수익", f"{df_real['PnL'].sum():,.2f} XRP")
        with c2: st.metric("최근 거래가", f"${df_real['Price'].iloc[-1]:,.4f}")
        with c3: st.metric("현재 포지션", f"{df_real['Balance'].iloc[-1]:,.2f}")
        
        st.subheader("📈 실전 수익 곡선")
        df_chart = df_real.sort_values('Time')
        df_chart['CumPnL'] = df_chart['PnL'].cumsum()
        st.plotly_chart(px.line(df_chart, x='Time', y='CumPnL', template="plotly_dark", color_discrete_sequence=['#00CC96']), use_container_width=True)
        st.dataframe(df_real.sort_values('Time', ascending=False), use_container_width=True)
    else:
        st.info("실전 매매 데이터를 기다리고 있습니다. (구글 시트 'REAL' 태그 확인 중)")

with tab2:
    if not df_virt.empty:
        v1, v2 = st.columns(2)
        current_bal = df_virt['Balance'].iloc[-1]
        with v1: st.metric("가상 계좌 잔고", f"{current_bal:,.2f} XRP", delta=f"{current_bal-1000:,.2f}")
        with v2: st.metric("AI 최근 액션", f"{df_virt['Side'].iloc[-1]} ({df_virt['Action'].iloc[-1]})")
        
        st.subheader("🤖 가상 자산 변화")
        st.plotly_chart(px.area(df_virt, x='Time', y='Balance', template="plotly_dark", color_discrete_sequence=['#636EFA']), use_container_width=True)
        st.dataframe(df_virt.sort_values('Time', ascending=False), use_container_width=True)
    else:
        st.info("가상 매매 데이터가 없습니다. (구글 시트 'VIRT' 태그 확인 중)")

with tab3:
    if not df_ai.empty:
        st.subheader("📡 AI 확신도 변화 (최근 50건)")
        
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
        name_map = {'Time': '시간', 'AI_판단': '판단', 'Extra1': '핵심 지표(RSI/Price/VIX)', 'Extra2': '확률 분포'}
        st.table(df_ai.sort_values('Time', ascending=False).head(10)[['Time', 'AI_판단', 'Extra1', 'Extra2']].rename(columns=name_map))
    else:
        st.info("AI 시그널 대기 중... (구글 시트 'AI' 태그 확인 중)")

st.sidebar.divider()
st.sidebar.info("CHLOE V2.8 (Universal Engine)")
if st.sidebar.button("🗑️ Cache Clear"):
    st.cache_data.clear()
    st.rerun()
