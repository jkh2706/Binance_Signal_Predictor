import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime

# 페이지 설정
st.set_page_config(page_title="CHLOE | Cloud Dashboard", layout="wide")

# 구글 시트 정보 (기훈님이 만드신 시트)
SHEET_ID = "1xQuz_k_FjE1Mjo0R21YS49Pr3ZNpG3yPTofzYyNSbuk"
CSV_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv"

@st.cache_data(ttl=60) # 1분마다 캐시 갱신
def load_data():
    try:
        df = pd.read_csv(CSV_URL)
        return df
    except Exception as e:
        st.error(f"데이터를 불러오지 못했습니다. 시트의 공유 설정을 '링크가 있는 모든 사용자에게 공개(뷰어)'로 바꿔주세요! \n에러: {e}")
        return pd.DataFrame()

st.title("✨ 클로이 클라우드 대시보드")
st.write("이 대시보드는 서버 리소스를 쓰지 않는 외부 독립형 앱입니다. 🛰️")

df = load_data()

if not df.empty:
    # 대시보드 내용 구성
    st.divider()
    
    # 상단 요약 지표
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("최근 거래 심볼", df['심볼'].iloc[-1] if '심볼' in df else "-")
    with col2:
        st.metric("최근 액션", df['Action'].iloc[-1] if 'Action' in df else "-")
    with col3:
        st.metric("최근 가격", f"${df['가격'].iloc[-1]:,.4f}" if '가격' in df else "-")

    # 수익 곡선 (간단하게 구현)
    if '실현손익' in df.columns:
        st.subheader("📈 실시간 누적 수익 추이")
        df['Cum_PnL'] = pd.to_numeric(df['실현손익'], errors='coerce').fillna(0).cumsum()
        fig = px.line(df, x=df.index, y='Cum_PnL', template="plotly_dark", title="누적 수익 (시트 데이터 기준)")
        st.plotly_chart(fig, use_container_width=True)

    # 상세 로그
    st.subheader("📄 실시간 트레이딩 로그 (구글 시트 연동)")
    st.dataframe(df.sort_index(ascending=False), use_container_width=True)

else:
    st.info("구글 시트에 데이터가 쌓이기를 기다리고 있습니다...")

st.sidebar.title("⚙️ 설정")
st.sidebar.info("기본 서버의 부담을 0으로 줄이기 위해 구글 스프레드시트 데이터를 직접 읽어옵니다.")
