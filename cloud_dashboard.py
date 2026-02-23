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
# 데이터 소스 URL (gid=0은 첫 번째 시트)
CSV_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid=0"

# 2. 커스텀 CSS (시인성 중심)
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;700;900&family=Noto+Sans+KR:wght@400;700&display=swap');
    html, body, [class*="css"] { font-family: 'Inter', 'Noto Sans KR', sans-serif; }
    .main { background-color: #05070a; }
    [data-testid="stMetric"] { background: #11151c; border: 2px solid #22272e; padding: 2rem !important; border-radius: 20px !important; }
    [data-testid="stMetricValue"] { color: #58a6ff !important; font-size: 2.5rem !important; font-weight: 900 !important; }
    [data-testid="stMetricLabel"] { color: #adbac7 !important; font-size: 1.1rem !important; font-weight: 700 !important; }
    .stTabs [data-baseweb="tab"] { height: 55px; background-color: #1c2128; border-radius: 10px 10px 0 0; padding: 0 30px; color: #adbac7; font-weight: 700; }
    .stTabs [aria-selected="true"] { background-color: #316dca !important; color: white !important; }
    </style>
    """, unsafe_allow_html=True)

# 3. 실시간 가격 조회 (차단 방지 및 로직 개선)
def fetch_now_price(symbol="XRPUSDT"):
    """여러 백업 URL을 사용하여 가격 조회의 성공률을 높임"""
    urls = [
        f"https://api.binance.com/api/v3/ticker/price?symbol={symbol}",
        f"https://api1.binance.com/api/v3/ticker/price?symbol={symbol}",
        f"https://api2.binance.com/api/v3/ticker/price?symbol={symbol}"
    ]
    for url in urls:
        try:
            resp = requests.get(url, timeout=5)
            if resp.status_code == 200:
                return float(resp.json()['price'])
        except:
            continue
    return 0.0

@st.cache_data(ttl=5) # 캐시 시간을 줄여 새로고침 시 최신 데이터 보장
def load_sheet_data():
    try:
        df = pd.read_csv(CSV_URL, dtype=str).fillna("-")
        if df.empty: return None, None, None
        
        # 헤더 자동 정리
        if "Type" in df.columns or "종류" in df.columns:
            pass # 정상 헤더 존재
        elif df.iloc[0, 0] == "Type" or df.iloc[0, 0] == "REAL" or df.iloc[0, 0] == "AI":
            # 데이터 첫 줄이 헤더이거나 데이터인 경우 컬럼 재지정
            cols = ["종류", "시간", "심볼", "액션", "포지션", "가격", "수량", "수익", "수수료", "잔고", "지표", "확률분포"]
            if len(df.columns) >= 12:
                df = df.iloc[:, :12]
                df.columns = cols
        
        # 시간 파싱
        df['시간'] = pd.to_datetime(df.iloc[:, 1].apply(lambda x: str(x).replace("'", "").strip()), errors='coerce')
        df = df.dropna(subset=['시간']).sort_values('시간')
        
        # 숫자 변환 (인덱스 기반으로 더 안전하게 접근)
        num_cols = [5, 6, 7, 8, 9] # 가격, 수량, 수익, 수수료, 잔고 컬럼 인덱스
        for i in num_cols:
            col_name = df.columns[i]
            df[col_name] = pd.to_numeric(df[col_name].astype(str).str.replace('[+%,]', '', regex=True), errors='coerce').fillna(0.0)
            
        # 종류(Type)에 따른 데이터 분리
        type_col = df.columns[0]
        reals = df[df[type_col].str.contains("REAL", na=False)].copy()
        virts = df[df[type_col].str.contains("VIRT", na=False)].copy()
        signals = df[df[type_col].str.contains("AI", na=False)].copy()
        
        return reals, virts, signals
    except Exception as e:
        st.error(f"시트 데이터 로드 중 오류: {e}")
        return None, None, None

# 데이터 로드
df_r, df_v, df_s = load_sheet_data()
current_xrp_price = fetch_now_price("XRPUSDT")

# 헤더 UI
st.title("🎯 트레이딩 통합 관제 센터 (V5.1)")
now_kst = datetime.utcnow() + timedelta(hours=9)
st.caption(f"기준 시각: {now_kst.strftime('%H:%M:%S')} (KST) | 앱 새로고침 시 데이터가 갱신됩니다.")

tab1, tab2, tab3 = st.tabs(["💰 실전 거래", "🧪 가상 실험실", "📡 AI 판단 시그널"])

with tab1:
    if df_r is not None and not df_r.empty:
        c1, c2, c3 = st.columns(3)
        c1.metric("총 수익", f"{df_r.iloc[:, 7].sum():,.2f} XRP")
        
        if current_xrp_price > 0:
            last_price = df_r.iloc[-1, 5]
            diff = current_xrp_price - last_price
            c2.metric("현재 시장가 (바이낸스)", f"${current_xrp_price:,.4f}", delta=f"{diff:+.4f}")
        else:
            c2.metric("현재 시장가", "통신 일시 오류")
            
        c3.metric("포지션 잔고", f"{df_r.iloc[-1, 9]:,.2f} XRP")
        
        st.divider()
        st.subheader("📈 수익 변화 추이")
        df_r['누적수익'] = df_r.iloc[:, 7].cumsum()
        st.plotly_chart(px.line(df_r, x='시간', y='누적수익', template="plotly_dark"), use_container_width=True)
        st.dataframe(df_r.sort_values('시간', ascending=False), use_container_width=True)
    else:
        st.info("실전 매매 데이터를 불러오는 중이거나 데이터가 없습니다.")

with tab2:
    if df_v is not None and not df_v.empty:
        st.metric("가상 잔고 (VIRT)", f"${df_v.iloc[-1, 9]:,.2f} USD")
        st.plotly_chart(px.area(df_v, x='시간', y=df_v.columns[9], template="plotly_dark"), use_container_width=True)
        st.dataframe(df_v.sort_values('시간', ascending=False), use_container_width=True)

with tab3:
    if df_s is not None and not df_s.empty:
        def parse_probs(row):
            try:
                # 'L:0.XX/S:0.XX/N:0.XX' 파싱
                val = str(row.iloc[11])
                d = {p.split(':')[0].strip().upper(): float(p.split(':')[1]) for p in val.split('/')}
                return pd.Series([d.get('L', 0), d.get('S', 0), d.get('N', 0)])
            except: return pd.Series([0, 0, 0])
            
        prob_df = df_s.tail(50).copy()
        prob_df[['L', 'S', 'N']] = prob_df.apply(parse_probs, axis=1)
        
        st.subheader("📡 AI 포지션 확신도 (최근 50건)")
        fig = px.line(prob_df, x='시간', y=['L', 'S', 'N'], 
                     color_discrete_map={'L': '#00CC96', 'S': '#EF553B', 'N': '#636EFA'},
                     template="plotly_dark")
        st.plotly_chart(fig, use_container_width=True)
        st.dataframe(df_s.sort_values('시간', ascending=False).head(50), use_container_width=True)

st.sidebar.button("♻️ 강제 새로고침", on_click=st.cache_data.clear)
