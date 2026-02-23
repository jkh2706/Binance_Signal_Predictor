import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import os
from dotenv import load_dotenv
from binance.client import Client

# 1. 고급스러운 테마 및 페이지 설정
st.set_page_config(
    page_title="클로이 AI | 프리미엄 트레이딩 대시보드",
    layout="wide",
    page_icon="💎"
)

load_dotenv()
SHEET_ID = os.getenv("GOOGLE_SHEET_ID", "1xQuz_k_FjE1Mjo0R21YS49Pr3ZNpG3yPTofzYyNSbuk")
CSV_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid=0"

# 바이낸스 클라이언트 설정 (실시간 가격 조회용)
BINANCE_API_KEY = os.getenv("BINANCE_API_KEY")
BINANCE_API_SECRET = os.getenv("BINANCE_API_SECRET")
client = Client(BINANCE_API_KEY, BINANCE_API_SECRET)

# 2. 커스텀 CSS (다크 모드 최적화 및 시인성 강화)
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;800&family=Noto+Sans+KR:wght@400;700&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Inter', 'Noto Sans KR', sans-serif;
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
        font-size: 0.9rem !important;
        text-transform: uppercase;
        letter-spacing: 0.1em;
        font-weight: 600;
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

    /* 데이터프레임 스타일 */
    .stDataFrame {
        border: 1px solid #30363d;
        border-radius: 12px;
    }
    
    h1, h2, h3 {
        color: #f0f6fc !important;
        font-weight: 700 !important;
    }
    </style>
    """, unsafe_allow_html=True)

@st.cache_data(ttl=5)
def load_data():
    try:
        df = pd.read_csv(CSV_URL, dtype=str).fillna("-")
        if df.empty: return None, None, None
        if df.iloc[0, 0] == "Type": df = df.iloc[1:].reset_index(drop=True)
        cols = ["종류", "시간", "심볼", "액션", "포지션", "가격", "수량", "수익", "수수료", "잔고", "지표", "확률분포"]
        df = df.iloc[:, :12]
        df.columns = cols
        df['시간'] = pd.to_datetime(df['시간'].apply(lambda x: str(x).replace("'", "").strip()), errors='coerce')
        df = df.dropna(subset=['시간']).sort_values('시간')
        for col in ['가격', '수량', '수익', '수수료', '잔고']:
            df[col] = pd.to_numeric(df[col].str.replace('[+%,]', '', regex=True), errors='coerce').fillna(0.0)
        
        reals = df[df['종류'] == "REAL"].drop_duplicates(subset=['확률분포'], keep='last').copy()
        virts = df[df['종류'] == "VIRT"].copy()
        signals = df[df['종류'] == "AI"].copy()
        return reals, virts, signals
    except Exception as e:
        st.error(f"동기화 오류: {e}")
        return None, None, None

def get_realtime_price(symbol="XRPUSDT"):
    try:
        ticker = client.get_symbol_ticker(symbol=symbol)
        return float(ticker['price'])
    except:
        return 0.0

# 헤더 섹션
c1, c2 = st.columns([3, 1])
with c1:
    st.title("💎 프리미엄 트레이딩 대시보드")
    st.markdown(f"**클로이(CHLOE) AI V4.2** | 실시간 시장 감시 가동 중")
with c2:
    st.markdown(f"<div style='text-align: right; color: #8b949e; padding-top: 20px;'>마지막 업데이트: {datetime.now().strftime('%H:%M:%S')}</div>", unsafe_allow_html=True)

df_r, df_v, df_s = load_data()

# 사이드바
with st.sidebar:
    st.header("제어판")
    if st.button("♻️ 데이터 강제 동기화", use_container_width=True):
        st.cache_data.clear()
        st.rerun()
    st.divider()
    st.info("실시간 시장가는 바이낸스 API를 통해 5초마다 갱신됩니다.")

# 메인 탭
tab1, tab2, tab3 = st.tabs(["💰 실전 매매 현황", "🧪 AI 가상 실험실", "📡 실시간 AI 시그널"])

# 탭 1: 실전 매매
with tab1:
    if df_r is not None and not df_r.empty:
        col1, col2, col3 = st.columns(3)
        total_pnl = df_r['수익'].sum()
        
        # 실시간 가격 조회
        rt_price = get_realtime_price("XRPUSDT")
        
        col1.metric("누적 수익", f"{total_pnl:,.4f} XRP", delta=f"{total_pnl:,.4f}")
        col2.metric("실시간 시장가", f"${rt_price:,.4f}" if rt_price > 0 else "조회 중...", 
                   delta=f"{rt_price - df_r['가격'].iloc[-1]:.4f}" if rt_price > 0 else None)
        col3.metric("현재 포지션 수량", f"{df_r['잔고'].iloc[-1]:,.2f} XRP")
        
        st.markdown("---")
        st.subheader("📈 누적 수익 곡선")
        df_r['누적수익'] = df_r['수익'].cumsum()
        fig_r = go.Figure()
        fig_r.add_trace(go.Scatter(x=df_r['시간'], y=df_r['누적수익'], fill='tozeroy', 
                                  line=dict(color='#58a6ff', width=3),
                                  fillcolor='rgba(88, 166, 255, 0.1)',
                                  name="수익 곡선"))
        fig_r.update_layout(template="plotly_dark", 
                           margin=dict(l=0, r=0, t=20, b=0), height=400,
                           xaxis=dict(showgrid=False), yaxis=dict(showgrid=True, gridcolor='#30363d'))
        st.plotly_chart(fig_r, use_container_width=True)
        
        st.subheader("📝 최근 실행 로그")
        st.dataframe(df_r.sort_values('시간', ascending=False), use_container_width=True)
    else:
        st.warning("실전 매매 데이터를 찾을 수 없습니다.")

# 탭 2: 가상 매매
with tab2:
    if df_v is not None and not df_v.empty:
        curr_v = df_v['잔고'].iloc[-1]
        st.metric("가상 계좌 잔고", f"${curr_v:,.2f} USD", delta=f"{curr_v-1000:,.2f}")
        
        st.subheader("🧪 가상 자산 변화 추이")
        fig_v = px.area(df_v, x='시간', y='잔고', template="plotly_dark")
        fig_v.update_traces(line_color='#79c0ff', fillcolor='rgba(121, 192, 255, 0.2)')
        fig_v.update_layout(margin=dict(l=0, r=0, t=20, b=0), height=400,
                           xaxis=dict(showgrid=False), yaxis=dict(gridcolor='#30363d'))
        st.plotly_chart(fig_v, use_container_width=True)
        st.dataframe(df_v.sort_values('시간', ascending=False), use_container_width=True)

# 탭 3: AI 분석
with tab3:
    if df_s is not None and not df_s.empty:
        def parse_ai_probs(row):
            try:
                txt = str(row['확률분포'])
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
        
        st.subheader("📡 AI 포지션 확신도 실시간 추이")
        if not chart_df.empty:
            fig_s = go.Figure()
            colors = {'LONG': '#3fb950', 'SHORT': '#f85149', 'NEUTRAL': '#58a6ff'}
            for col in ['LONG', 'SHORT', 'NEUTRAL']:
                fig_s.add_trace(go.Scatter(x=chart_df['시간'], y=chart_df[col], name=col,
                                          line=dict(color=colors[col], width=2, dash='solid' if col != 'NEUTRAL' else 'dot')))
            fig_s.update_layout(template="plotly_dark", margin=dict(l=0, r=0, t=20, b=0), height=450,
                               legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                               xaxis=dict(showgrid=False), yaxis=dict(gridcolor='#30363d'))
            st.plotly_chart(fig_s, use_container_width=True)
        
        st.subheader("📝 AI 판단 및 핵심 지표 로그")
        st.dataframe(df_s.sort_values('시간', ascending=False).head(50)[['시간', '포지션', '지표', '확률분포']], use_container_width=True)
    else:
        st.info("AI 분석 데이터를 수집 중입니다...")
