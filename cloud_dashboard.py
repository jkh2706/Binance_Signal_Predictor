import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import os
from dotenv import load_dotenv

# 1. 고급스러운 테마 및 페이지 설정
st.set_page_config(
    page_title="CHLOE AI | Premium Trading Intelligence",
    layout="wide",
    page_icon="💎"
)

load_dotenv()
SHEET_ID = os.getenv("GOOGLE_SHEET_ID", "1xQuz_k_FjE1Mjo0R21YS49Pr3ZNpG3yPTofzYyNSbuk")
CSV_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid=0"

# 2. 커스텀 CSS (다크 모드 최적화 및 시인성 강화)
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;800&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
    }
    
    .main {
        background-color: #05070a;
    }
    
    /* 카드 스타일 메트릭 */
    [data-testid="stMetric"] {
        background: linear-gradient(135deg, #161b22 0%, #0d1117 100%);
        border: 1px solid #30363d;
        padding: 1.5rem !important;
        border-radius: 16px !important;
        box-shadow: 0 4px 15px rgba(0,0,0,0.3);
    }
    
    [data-testid="stMetricValue"] {
        color: #58a6ff !important;
        font-size: 2.2rem !important;
        font-weight: 800 !important;
    }
    
    [data-testid="stMetricLabel"] {
        color: #8b949e !important;
        font-size: 1rem !important;
        text-transform: uppercase;
        letter-spacing: 0.1em;
    }

    /* 탭 스타일 커스텀 */
    .stTabs [data-baseweb="tab-list"] {
        gap: 24px;
        background-color: transparent;
    }
    
    .stTabs [data-baseweb="tab"] {
        height: 50px;
        background-color: #161b22;
        border-radius: 8px 8px 0px 0px;
        padding: 0 24px;
        color: #8b949e;
        border: 1px solid #30363d;
    }
    
    .stTabs [aria-selected="true"] {
        background-color: #1f6feb !important;
        color: white !important;
        border: 1px solid #1f6feb !important;
    }

    /* 사이드바 */
    .css-1d391kg {
        background-color: #0d1117;
    }
    
    /* 데이터프레임 스타일 */
    .stDataFrame {
        border: 1px solid #30363d;
        border-radius: 12px;
    }
    
    h1, h2, h3 {
        color: #f0f6fc !important;
        font-weight: 700 !important;
    }
    
    .status-badge {
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 0.8rem;
        font-weight: 600;
    }
    </style>
    """, unsafe_allow_html=True)

@st.cache_data(ttl=5)
def load_data():
    try:
        df = pd.read_csv(CSV_URL, dtype=str).fillna("-")
        if df.empty: return None, None, None
        if df.iloc[0, 0] == "Type": df = df.iloc[1:].reset_index(drop=True)
        cols = ["Type", "Time", "Symbol", "Action", "Side", "Price", "Qty", "PnL", "Fee", "Balance", "Extra1", "Extra2"]
        df = df.iloc[:, :12]
        df.columns = cols
        df['Time'] = pd.to_datetime(df['Time'].apply(lambda x: str(x).replace("'", "").strip()), errors='coerce')
        df = df.dropna(subset=['Time']).sort_values('Time')
        for col in ['Price', 'Qty', 'PnL', 'Fee', 'Balance']:
            df[col] = pd.to_numeric(df[col].str.replace('[+%,]', '', regex=True), errors='coerce').fillna(0.0)
        
        reals = df[df['Type'] == "REAL"].drop_duplicates(subset=['Extra2'], keep='last').copy()
        virts = df[df['Type'] == "VIRT"].copy()
        signals = df[df['Type'] == "AI"].copy()
        return reals, virts, signals
    except Exception as e:
        st.error(f"Sync Error: {e}")
        return None, None, None

# 헤더 섹션
c1, c2 = st.columns([3, 1])
with c1:
    st.title("💎 Premium Trading Intelligence")
    st.markdown(f"**CHLOE V4.0** | 실시간 데이터 동기화 활성화 중")
with c2:
    st.markdown(f"<div style='text-align: right; color: #8b949e; padding-top: 20px;'>Last Update: {datetime.now().strftime('%H:%M:%S')}</div>", unsafe_allow_html=True)

df_r, df_v, df_s = load_data()

# 사이드바
with st.sidebar:
    st.image("https://raw.githubusercontent.com/openclaw/openclaw/main/assets/logo.png", width=100) # 가상의 로고 주소
    st.header("Control Panel")
    if st.button("♻️ Force Sync Now", use_container_width=True):
        st.cache_data.clear()
        st.rerun()
    st.divider()
    st.info("시인성 강화를 위해 폰트 및 카드 디자인이 최적화되었습니다.")

# 메인 탭
tab1, tab2, tab3 = st.tabs(["💰 LIVE TRADES", "🧪 VIRTUAL LAB", "📡 AI ANALYTICS"])

# 탭 1: 실전 매매
with tab1:
    if df_r is not None and not df_r.empty:
        col1, col2, col3 = st.columns(3)
        total_pnl = df_r['PnL'].sum()
        pnl_color = "normal" if total_pnl >= 0 else "inverse"
        col1.metric("Cumulative PnL", f"{total_pnl:,.4f} XRP", delta=f"{total_pnl:,.4f}")
        col2.metric("Market Price", f"${df_r['Price'].iloc[-1]:,.4f}")
        col3.metric("Current Exposure", f"{df_r['Balance'].iloc[-1]:,.2f} XRP")
        
        st.markdown("---")
        # 수익 곡선 (고급형 그라데이션 차트)
        df_r['CumPnL'] = df_r['PnL'].cumsum()
        fig_r = go.Figure()
        fig_r.add_trace(go.Scatter(x=df_r['Time'], y=df_r['CumPnL'], fill='tozeroy', 
                                  line=dict(color='#58a6ff', width=3),
                                  fillcolor='rgba(88, 166, 255, 0.1)'))
        fig_r.update_layout(template="plotly_dark", title="Performance Curve", 
                           margin=dict(l=0, r=0, t=40, b=0), height=400,
                           xaxis=dict(showgrid=False), yaxis=dict(showgrid=True, gridcolor='#30363d'))
        st.plotly_chart(fig_r, use_container_width=True)
        
        st.subheader("Recent Execution Log")
        st.dataframe(df_r.sort_values('Time', ascending=False), use_container_width=True)
    else:
        st.warning("No live data found.")

# 탭 2: 가상 매매
with tab2:
    if df_v is not None and not df_v.empty:
        curr_v = df_v['Balance'].iloc[-1]
        st.metric("Virtual Balance", f"${curr_v:,.2f} USD", delta=f"{curr_v-1000:,.2f}")
        
        fig_v = px.area(df_v, x='Time', y='Balance', template="plotly_dark")
        fig_v.update_traces(line_color='#79c0ff', fillcolor='rgba(121, 192, 255, 0.2)')
        fig_v.update_layout(margin=dict(l=0, r=0, t=30, b=0), height=400)
        st.plotly_chart(fig_v, use_container_width=True)
        st.dataframe(df_v.sort_values('Time', ascending=False), use_container_width=True)

# 탭 3: AI 분석
with tab3:
    if df_s is not None and not df_s.empty:
        def parse_ai_probs(row):
            try:
                txt = str(row['Extra2'])
                parts = txt.split('/')
                res = {'L': 0.0, 'S': 0.0, 'N': 0.0}
                for p in parts:
                    if ':' in p:
                        k, v = p.split(':', 1)
                        key = k.strip().upper()
                        if 'L' in key: res['L'] = float(v)
                        elif 'S' in key: res['S'] = float(v)
                        elif 'N' in key: res['N'] = float(v)
                return pd.Series([res['L'], res['S'], res['N']])
            except: return pd.Series([None, None, None])
            
        prob_df = df_s.tail(100).copy()
        prob_df[['LONG', 'SHORT', 'NEUTRAL']] = prob_df.apply(parse_ai_probs, axis=1)
        chart_df = prob_df.dropna(subset=['LONG'])
        
        st.subheader("Intelligence Confidence Trend")
        if not chart_df.empty:
            fig_s = go.Figure()
            colors = {'LONG': '#3fb950', 'SHORT': '#f85149', 'NEUTRAL': '#58a6ff'}
            for col in ['LONG', 'SHORT', 'NEUTRAL']:
                fig_s.add_trace(go.Scatter(x=chart_df['Time'], y=chart_df[col], name=col,
                                          line=dict(color=colors[col], width=2, dash='solid' if col != 'NEUTRAL' else 'dot')))
            fig_s.update_layout(template="plotly_dark", margin=dict(l=0, r=0, t=30, b=0), height=450,
                               legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                               xaxis=dict(showgrid=False), yaxis=dict(gridcolor='#30363d'))
            st.plotly_chart(fig_s, use_container_width=True)
        
        st.subheader("Logic Reasoning Archive")
        st.dataframe(df_s.sort_values('Time', ascending=False).head(50)[['Time', 'Side', 'Extra1', 'Extra2']], use_container_width=True)
    else:
        st.info("Awaiting AI analysis data...")
