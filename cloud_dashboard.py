import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import os
import requests
from dotenv import load_dotenv

# 1. 페이지 설정 (최상단 유지)
st.set_page_config(
    page_title="클로이 AI | 트레이딩 대시보드",
    layout="wide",
    page_icon="🎯"
)

load_dotenv()
SHEET_ID = os.getenv("GOOGLE_SHEET_ID", "1xQuz_k_FjE1Mjo0R21YS49Pr3ZNpG3yPTofzYyNSbuk")
CSV_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid=0"

# 2. 커스텀 CSS (시인성 극대화)
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;700;900&family=Noto+Sans+KR:wght@400;700&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Inter', 'Noto Sans KR', sans-serif;
    }
    
    .main {
        background-color: #05070a;
    }
    
    /* 지표 카드 스타일 */
    [data-testid="stMetric"] {
        background: #11151c;
        border: 2px solid #22272e;
        padding: 2rem !important;
        border-radius: 20px !important;
    }
    
    [data-testid="stMetricValue"] {
        color: #58a6ff !important;
        font-size: 2.5rem !important;
        font-weight: 900 !important;
    }
    
    [data-testid="stMetricLabel"] {
        color: #adbac7 !important;
        font-size: 1.1rem !important;
        font-weight: 700 !important;
        margin-bottom: 10px;
    }

    /* 탭 스타일 */
    .stTabs [data-baseweb="tab-list"] {
        gap: 15px;
    }
    
    .stTabs [data-baseweb="tab"] {
        height: 55px;
        background-color: #1c2128;
        border-radius: 10px 10px 0 0;
        padding: 0 30px;
        color: #adbac7;
        font-weight: 700;
    }
    
    .stTabs [aria-selected="true"] {
        background-color: #316dca !important;
        color: white !important;
    }
    </style>
    """, unsafe_allow_html=True)

# 3. 실시간 가격 조회 (새로고침 시 1회 실행)
def fetch_now_price(symbol="XRPUSDT"):
    try:
        # 캐싱 없이 직접 요청
        url = f"https://api.binance.com/api/v3/ticker/price?symbol={symbol}"
        resp = requests.get(url, timeout=3)
        if resp.status_code == 200:
            return float(resp.json()['price'])
    except:
        pass
    return 0.0

@st.cache_data(ttl=10)
def load_sheet_data():
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
        st.error(f"데이터 로드 중 오류: {e}")
        return None, None, None

# 헤더
st.title("🎯 트레이딩 통합 관제 센터 (V5.0)")
now_kst = datetime.utcnow() + timedelta(hours=9)
st.caption(f"기준 시각: {now_kst.strftime('%Y-%m-%d %H:%M:%S')} (KST) | 앱 새로고침 시 데이터가 갱신됩니다.")

df_r, df_v, df_s = load_sheet_data()
current_xrp_price = fetch_now_price("XRPUSDT")

tab1, tab2, tab3 = st.tabs(["💰 실전 거래", "🧪 가상 실험실", "📡 AI 판단 시그널"])

with tab1:
    if df_r is not None and not df_r.empty:
        c1, c2, c3 = st.columns(3)
        c1.metric("총 수익", f"{df_r['수익'].sum():,.2f} XRP")
        
        # 기훈님 요청: 새로고침 시에만 조회된 실시간 가격 표시
        if current_xrp_price > 0:
            last_trade_price = df_r['가격'].iloc[-1]
            diff = current_xrp_price - last_trade_price
            c2.metric("현재 시장가 (Binance)", f"${current_xrp_price:,.4f}", delta=f"{diff:+.4f}")
        else:
            c2.metric("현재 시장가", "조회 실패")
            
        c3.metric("포지션 잔고", f"{df_r['잔고'].iloc[-1]:,.2f} XRP")
        
        st.divider()
        st.subheader("📈 수익 변화 추이")
        df_r['누적수익'] = df_r['수익'].cumsum()
        st.plotly_chart(px.line(df_r, x='시간', y='누적수익', template="plotly_dark", line_shape="hv"), use_container_width=True)
        
        st.subheader("📝 최근 체결 내역")
        st.dataframe(df_r.sort_values('시간', ascending=False), use_container_width=True)
    else:
        st.info("실전 매매 데이터가 없습니다.")

with tab2:
    if df_v is not None and not df_v.empty:
        st.metric("가상 잔고 (VIRT)", f"${df_v['잔고'].iloc[-1]:,.2f} USD")
        st.plotly_chart(px.area(df_v, x='시간', y='잔고', template="plotly_dark"), use_container_width=True)
        st.dataframe(df_v.sort_values('시간', ascending=False), use_container_width=True)

with tab3:
    if df_s is not None and not df_s.empty:
        def parse_probs(row):
            try:
                d = {p.split(':')[0].strip().upper(): float(p.split(':')[1]) for p in str(row['확률분포']).split('/')}
                return pd.Series([d.get('L', 0), d.get('S', 0), d.get('N', 0)])
            except: return pd.Series([0, 0, 0])
            
        prob_df = df_s.tail(50).copy()
        prob_df[['L', 'S', 'N']] = prob_df.apply(parse_probs, axis=1)
        
        st.subheader("📡 AI 포지션 확신도 (최근 50건)")
        fig = px.line(prob_df, x='시간', y=['L', 'S', 'N'], 
                     color_discrete_map={'L': '#00CC96', 'S': '#EF553B', 'N': '#636EFA'},
                     template="plotly_dark")
        st.plotly_chart(fig, use_container_width=True)
        
        st.subheader("📝 AI 판단 기록")
        st.dataframe(df_s.sort_values('시간', ascending=False).head(50)[['시간', '포지션', '지표', '확률분포']], use_container_width=True)

st.sidebar.info("CHLOE V5.0 - 새로고침 시 실시간 시세 반영")
if st.sidebar.button("♻️ 강제 캐시 삭제 및 새로고침"):
    st.cache_data.clear()
    st.rerun()
