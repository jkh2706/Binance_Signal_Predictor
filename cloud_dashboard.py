import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime

# 페이지 설정
st.set_page_config(page_title="CHLOE | Cloud Dashboard", layout="wide", page_icon="🛰️")

# 구글 시트 정보 (기훈님이 만드신 시트)
SHEET_ID = "1xQuz_k_FjE1Mjo0R21YS49Pr3ZNpG3yPTofzYyNSbuk"
# export?format=csv 방식은 시트가 '링크가 있는 모든 사용자에게 공개'되어 있어야 합니다.
CSV_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv"

@st.cache_data(ttl=30) # 30초마다 캐시 갱신
def load_data():
    try:
        df = pd.read_csv(CSV_URL)
        # 데이터 정제: 텅 빈 컬럼 제거
        df = df.dropna(axis=1, how='all')
        return df
    except Exception as e:
        return str(e)

st.title("🛰️ 클로이 실시간 트레이딩 대시보드")
st.write("본 앱은 구글 스프레드시트와 실시간으로 연동됩니다.")

res = load_data()

if isinstance(res, str):
    st.error("데이터 로드 중 오류가 발생했습니다.")
    st.info("💡 **체크리스트:**")
    st.markdown(f"""
    1. 구글 시트의 [공유] 설정이 **'링크가 있는 모든 사용자에게 공개(뷰어)'**로 되어있나요?
    2. 시트의 URL이 정확한가요? (ID: `{SHEET_ID}`)
    """)
    st.code(f"Error Details: {res}")
elif res.empty:
    st.warning("구글 시트에 데이터가 하나도 없습니다. 로봇이 데이터를 기록할 때까지 기다려주세요.")
else:
    df = res.copy()
    st.success(f"데이터 로드 성공! (총 {len(df)}건의 기록 발견)")
    
    # 상단 요약
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("최근 심볼", df['심볼'].iloc[-1] if '심볼' in df.columns else "-")
    with col2:
        st.metric("최근 상태", df['Action'].iloc[-1] if 'Action' in df.columns else "-")
    with col3:
        price = df['가격'].iloc[-1] if '가격' in df.columns else 0
        st.metric("현재가", f"${price:,.4f}")

    st.divider()

    # 수익 곡선
    if '실현손익' in df.columns:
        st.subheader("📈 누적 수익 흐름")
        df['PnL_num'] = pd.to_numeric(df['실현손익'], errors='coerce').fillna(0)
        df['Cumulative_PnL'] = df['PnL_num'].cumsum()
        fig = px.line(df, x=df.index, y='Cumulative_PnL', template="plotly_dark", markers=True)
        fig.update_layout(xaxis_title="거래 순서", yaxis_title="누적 수익")
        st.plotly_chart(fig, use_container_width=True)

    # 데이터 테이블
    st.subheader("📄 전체 매매 기록 (최근순)")
    st.dataframe(df.iloc[::-1], use_container_width=True)

st.sidebar.title("⚙️ 시스템 정보")
st.sidebar.write("- 대시보드 위치: Streamlit Cloud")
st.sidebar.write("- 데이터 소스: Google Sheets")
st.sidebar.write("- 업데이트 주기: 30초")
