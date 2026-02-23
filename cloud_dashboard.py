import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import os
import requests
from dotenv import load_dotenv

# 1. 페이지 설정
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
    html, body, [class*="css"] { font-family: 'Inter', 'Noto Sans KR', sans-serif; }
    .main { background-color: #05070a; }
    [data-testid="stMetric"] { background: #11151c; border: 2px solid #22272e; padding: 2rem !important; border-radius: 20px !important; }
    [data-testid="stMetricValue"] { color: #58a6ff !important; font-size: 2.5rem !important; font-weight: 900 !important; }
    [data-testid="stMetricLabel"] { color: #adbac7 !important; font-size: 1.1rem !important; font-weight: 700 !important; }
    </style>
    """, unsafe_allow_html=True)

@st.cache_data(ttl=5)
def load_data():
    try:
        # 데이터 로드 (인증 없이 공개 시트로 접근)
        df = pd.read_csv(CSV_URL, dtype=str).fillna("-")
        if df.empty: return None, None, None
        
        # 헤더 정리 및 12컬럼 고정
        cols = ["종류", "시간", "심볼", "액션", "포지션", "가격", "수량", "수익", "수수료", "잔고", "지표", "확률분포"]
        if df.iloc[0, 0] == "Type": df = df.iloc[1:].reset_index(drop=True)
        df = df.iloc[:, :12]
        df.columns = cols
        
        # 시간 및 숫자 변환
        df['시간'] = pd.to_datetime(df['시간'].str.replace("'", ""), errors='coerce')
        df = df.dropna(subset=['시간']).sort_values('시간')
        for c in ["가격", "수량", "수익", "수수료", "잔고"]:
            df[c] = pd.to_numeric(df[c].str.replace('[+%,]', '', regex=True), errors='coerce').fillna(0.0)
        
        return df[df['종류'] == "REAL"].copy(), df[df['종류'] == "VIRT"].copy(), df[df['종류'] == "AI"].copy()
    except Exception as e:
        st.error(f"데이터 로드 실패: {e}")
        return None, None, None

def get_price():
    """가장 심플한 방식의 가격 조회"""
    try:
        r = requests.get("https://api.binance.com/api/v3/ticker/price?symbol=XRPUSDT", timeout=5)
        return float(r.json()['price'])
    except:
        try:
            r = requests.get("https://api1.binance.com/api/v3/ticker/price?symbol=XRPUSDT", timeout=5)
            return float(r.json()['price'])
        except: return 0.0

st.title("🎯 트레이딩 통합 관제 센터 (V5.2)")
df_r, df_v, df_s = load_data()
price = get_price()

tab1, tab2, tab3 = st.tabs(["💰 실전 거래", "🧪 가상 실험실", "📡 AI 시그널"])

with tab1:
    if df_r is not None and not df_r.empty:
        c1, c2, c3 = st.columns(3)
        c1.metric("총 수익", f"{df_r['수익'].sum():,.2f} XRP")
        c2.metric("실시간 시장가", f"${price:,.4f}" if price > 0 else "데이터 지연")
        c3.metric("포지션 잔고", f"{df_r['잔고'].iloc[-1]:,.2f} XRP")
        st.plotly_chart(px.line(df_r, x='시간', y=df_r['수익'].cumsum(), template="plotly_dark"), use_container_width=True)
        st.dataframe(df_r.sort_values('시간', ascending=False), use_container_width=True)

with tab2:
    if df_v is not None and not df_v.empty:
        st.metric("가상 잔고", f"${df_v['잔고'].iloc[-1]:,.2f}")
        st.plotly_chart(px.area(df_v, x='시간', y='잔고', template="plotly_dark"), use_container_width=True)

with tab3:
    if df_s is not None and not df_s.empty:
        st.subheader("📝 최근 AI 판단 로그")
        st.dataframe(df_s.sort_values('시간', ascending=False).head(50), use_container_width=True)

if st.sidebar.button("♻️ 새로고침"):
    st.cache_data.clear()
    st.rerun()
