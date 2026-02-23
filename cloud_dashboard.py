import streamlit as st
import pandas as pd
import requests
from datetime import datetime
import os

# [V5.3] 극단적 단순화 버전 - 파기 위기 극복용
st.set_page_config(page_title="XRP 모니터", layout="wide")

# 1. 실시간 가격 조회 (이게 안 뜨면 파기라는 각오로 작성)
def get_price():
    try:
        # 타임아웃 넉넉히, 에러 시 0 리턴
        r = requests.get("https://api.binance.com/api/v3/ticker/price?symbol=XRPUSDT", timeout=10)
        return float(r.json()['price'])
    except:
        return 0.0

# 2. 데이터 로드 (시트 ID 고정)
SHEET_ID = "1xQuz_k_FjE1Mjo0R21YS49Pr3ZNpG3yPTofzYyNSbuk"
CSV_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid=0"

def load_data():
    try:
        df = pd.read_csv(CSV_URL)
        return df
    except:
        return pd.DataFrame()

# UI 구성
st.title("XRP 실시간 트레이딩 대시보드")

# 시장가 표시 (가장 상단에 배치)
price = get_price()
if price > 0:
    st.metric(label="현재 XRP 시장가 (Binance)", value=f"${price:,.4f}")
else:
    st.error("거래소 통신 지연 중... (새로고침을 시도하세요)")

st.divider()

# 데이터 테이블
df = load_data()
if not df.empty:
    st.subheader("최근 트레이딩 데이터 (Google Sheets)")
    st.dataframe(df.head(50), use_container_width=True)
else:
    st.warning("시트 데이터를 불러올 수 없습니다.")

if st.button("데이터 갱신"):
    st.rerun()
