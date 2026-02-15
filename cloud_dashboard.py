import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta

# 페이지 설정
st.set_page_config(page_title="CHLOE | Trading Dashboard V3.1", layout="wide", page_icon="🎯")

# 스타일 설정
st.markdown("""
    <style>
    .main { background-color: #0e1117; color: white; }
    .stMetric { background-color: #1e2130; padding: 20px; border-radius: 12px; border: 1px solid #3e4150; }
    div[data-testid="stMetricValue"] { font-size: 1.8rem; font-weight: 700; color: #00CC96; }
    </style>
    """, unsafe_allow_html=True)

# 구글 시트 정보
SHEET_ID = "1xQuz_k_FjE1Mjo0R21YS49Pr3ZNpG3yPTofzYyNSbuk"
CSV_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv"

@st.cache_data(ttl=15)
def load_data():
    try:
        df = pd.read_csv(CSV_URL)
        if df.empty:
            return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()
        
        # 유니버설 12컬럼 포맷 강제 적용
        # 0:Type, 1:Time, 2:Sym, 3:Act, 4:Side, 5:Price, 6:Qty, 7:PnL, 8:Fee, 9:Bal, 10:Ex1, 11:Ex2
        cols = ["Type", "Time", "Symbol", "Action", "Side", "Price", "Qty", "PnL", "Fee", "Balance", "Extra1", "Extra2"]
        if len(df.columns) >= 12:
            df = df.iloc[:, :12]
            df.columns = cols
        else:
            # 컬럼수가 부족하면 유효한 데이터가 아님 (초기화 필요)
            return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

        # 데이터 타입 정리
        df['Time'] = pd.to_datetime(df['Time'], errors='coerce') + timedelta(hours=9)
        df = df.dropna(subset=['Time'])
        
        # 숫자 변환
        for col in ['Price', 'Qty', 'PnL', 'Fee', 'Balance']:
            if col == 'PnL': # ROE% 처리
                df[col] = df[col].astype(str).str.replace('%', '').str.replace('+', '')
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

        df_real = df[df['Type'] == "REAL"].copy()
        df_virt = df[df['Type'] == "VIRT"].copy()
        df_ai = df[df['Type'] == "AI"].copy()
        
        return df_real, df_virt, df_ai
    except Exception as e:
        st.error(f"Data Sync Error: {e}")
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

st.title("🎯 트레이딩 마스터 대시보드 V3.1")
st.caption("기훈님을 위한 실시간 데이터 통합 관제 센터")

df_real, df_virt, df_ai = load_data()

if df_real.empty and df_virt.empty and df_ai.empty:
    st.warning("⚠️ 데이터 구조 동기화 중이거나 시트가 비어있습니다. 잠시만 기다려주세요.")
    if st.button("🔄 강제 새로고침"):
        st.cache_data.clear()
        st.rerun()
else:
    tab1, tab2, tab3 = st.tabs(["💰 REAL (실전)", "🧪 VIRTUAL (가상)", "📡 AI SIGNAL"])

    with tab1:
        if not df_real.empty:
            c1, c2, c3 = st.columns(3)
            with c1: st.metric("오늘의 수익", f"{df_real['PnL'].sum():,.2f} XRP")
            with c2: st.metric("최근 거래가", f"${df_real['Price'].iloc[-1]:,.4f}")
            with c3: st.metric("현재 포지션 수량", f"{df_real['Balance'].iloc[-1]:,.2f}")
            
            st.subheader("📈 누적 수익 곡선")
            df_real['CumPnL'] = df_real['PnL'].cumsum()
            st.plotly_chart(px.line(df_real, x='Time', y='CumPnL', template="plotly_dark", color_discrete_sequence=['#00CC96']), use_container_width=True)
            
            st.subheader("📄 상세 거래 기록")
            st.dataframe(df_real.sort_values('Time', ascending=False), use_container_width=True)
        else:
            st.info("실전 매매 기록을 기다리는 중...")

    with tab2:
        if not df_virt.empty:
            c1, c2 = st.columns(2)
            current_bal = df_virt['Balance'].iloc[-1]
            with c1: st.metric("가상 계좌 잔고", f"{current_bal:,.2f} XRP", delta=f"{current_bal-1000:,.2f}")
            with c2: st.metric("최근 AI 액션", f"{df_virt['Side'].iloc[-1]} ({df_virt['Action'].iloc[-1]})")
            
            st.subheader("📉 자산 변화 흐름")
            st.plotly_chart(px.area(df_virt, x='Time', y='Balance', template="plotly_dark", color_discrete_sequence=['#636EFA']), use_container_width=True)
            
            st.subheader("📑 가상 매매 로그")
            st.dataframe(df_virt.sort_values('Time', ascending=False), use_container_width=True)

    with tab3:
        if not df_ai.empty:
            st.subheader("📡 AI 실시간 판단 및 확률 분석")
            # Extra2에서 확률 파싱 (L:0.50/S:0.10/N:0.40)
            def parse_probs(row):
                try:
                    parts = row['Extra2'].split('/')
                    l = float(parts[0].split(':')[1])
                    s = float(parts[1].split(':')[1])
                    n = float(parts[2].split(':')[1])
                    return pd.Series([l, s, n])
                except:
                    return pd.Series([0, 0, 0])
            
            prob_df = df_ai.tail(50).apply(parse_probs, axis=1)
            prob_df.columns = ['LONG', 'SHORT', 'NEUTRAL']
            prob_df['Time'] = df_ai.tail(50)['Time']
            
            st.plotly_chart(px.line(prob_df, x='Time', y=['LONG', 'SHORT', 'NEUTRAL'], 
                                   color_discrete_map={'LONG':'#00CC96', 'SHORT':'#EF553B', 'NEUTRAL':'#636EFA'},
                                   template="plotly_dark"), use_container_width=True)
            
            st.subheader("📝 판단 로그")
            st.dataframe(df_ai.sort_values('Time', ascending=False), use_container_width=True)

st.sidebar.title("⚙️ System Control")
st.sidebar.write("CHLOE V3.1 (Universal Sync)")
if st.sidebar.button("🗑️ Cache Clear"):
    st.cache_data.clear()
    st.rerun()
st.sidebar.divider()
st.sidebar.info(f"Last Sync: {datetime.now().strftime('%H:%M:%S')}")
