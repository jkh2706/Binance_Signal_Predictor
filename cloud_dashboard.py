import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta

# 페이지 설정
st.set_page_config(page_title="기훈님 트레이딩 클라우드 대시보드", layout="wide", page_icon="🚀")

# 스타일 설정
st.markdown("""
    <style>
    .main { background-color: #0e1117; }
    .stMetric { background-color: #1e2130; padding: 15px; border-radius: 10px; }
    </style>
    """, unsafe_allow_html=True)

# 구글 시트 정보
SHEET_ID = "1xQuz_k_FjE1Mjo0R21YS49Pr3ZNpG3yPTofzYyNSbuk"
CSV_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv"

@st.cache_data(ttl=30)
def load_all_data():
    try:
        # 데이터가 없을 경우를 대비해 헤더가 포함된 빈 데이터프레임 구조 정의
        df = pd.read_csv(CSV_URL)
        if df.empty:
            return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()
            
        # 첫 번째 열의 이름을 'Category'로 강제 지정하여 정렬
        df.columns = ['Category'] + list(df.columns[1:])
        
        # REAL 데이터 (실전 매매)
        # 0:Cat, 1:Time, 2:Sym, 3:Dir, 4:Side, 5:Price, 6:PnL, 7:Fee, 8:PosAmt, 9:OrderID, 10:TradeID
        df_real = df[df['Category'] == "REAL"].copy()
        if not df_real.empty:
            df_real = df_real.iloc[:, :11]
            df_real.columns = ["Cat", "시간(KST)", "심볼", "방향", "매수/매도", "가격", "실현손익", "수수료", "포지션수량", "OrderID", "TradeID"]
            df_real["시간(KST)"] = pd.to_datetime(df_real["시간(KST)"]) + timedelta(hours=9)
            # 숫자형 변환
            for col in ['가격', '실현손익', '수수료', '포지션수량']:
                df_real[col] = pd.to_numeric(df_real[col], errors='coerce')
        
        # VIRT 데이터 (가상 매매)
        # 0:Cat, 1:Time, 2:Sym, 3:Action, 4:Side, 5:Price, 6:PnL, 7:Balance
        df_virt = df[df['Category'] == "VIRT"].copy()
        if not df_virt.empty:
            df_virt = df_virt.iloc[:, :8]
            df_virt.columns = ["Cat", "시간(KST)", "심볼", "액션", "포지션", "가격", "수익률(ROE)", "잔고(XRP)"]
            df_virt["시간(KST)"] = pd.to_datetime(df_virt["시간(KST)"]) + timedelta(hours=9)
            df_virt["잔고(XRP)"] = pd.to_numeric(df_virt["잔고(XRP)"].astype(str).str.replace(',', ''), errors='coerce')

        # AI 데이터 (AI 판단)
        # 0:Cat, 1:Time, 2:Sym, 3:Price, 4:Decision, 5:Prob_L, 6:Prob_S, 7:Prob_N
        df_ai = df[df['Category'] == "AI"].copy()
        if not df_ai.empty:
            df_ai = df_ai.iloc[:, :8]
            df_ai.columns = ["Cat", "시간(KST)", "심볼", "현재가", "AI_판단", "LONG_확률", "SHORT_확률", "NEUTRAL_확률"]
            df_ai["시간(KST)"] = pd.to_datetime(df_ai["시간(KST)"]) + timedelta(hours=9)
            for col in ['LONG_확률', 'SHORT_확률', 'NEUTRAL_확률']:
                df_ai[col] = pd.to_numeric(df_ai[col], errors='coerce')
        
        return df_real, df_virt, df_ai
    except Exception as e:
        st.error(f"데이터 파싱 오류: {e}")
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

st.title("🚀 트레이딩 마스터 대시보드 (Cloud)")

df_real, df_virt, df_ai = load_all_data()

# 탭 구성 (기존 기능 복구)
tab1, tab2, tab3 = st.tabs(["💰 실전 매매 현황", "🧪 AI 가상 실험실", "📡 실시간 시그널"])

with tab1:
    if not df_real.empty:
        col_f1, col_f2 = st.columns([1, 2])
        with col_f1:
            selected_symbol = st.selectbox("심볼 선택", ["전체"] + list(df_real['심볼'].unique()))
        with col_f2:
            st.metric("총 실현손익", f"{df_real['실현손익'].sum():,.2f} XRP")

        if selected_symbol != "전체":
            df_real = df_real[df_real['심볼'] == selected_symbol]

        st.subheader("📈 누적 수익 곡선 (실전)")
        df_chart = df_real.sort_values('시간(KST)')
        df_chart['Cum_PnL'] = df_chart['실현손익'].cumsum()
        st.plotly_chart(px.line(df_chart, x='시간(KST)', y='Cum_PnL', template="plotly_dark", color_discrete_sequence=['#00CC96']), use_container_width=True)

        st.subheader("📄 상세 거래 내역")
        st.dataframe(df_real.sort_values('시간(KST)', ascending=False), use_container_width=True)
    
    # 레거시 데이터 (기존 시트 데이터) 표시
    st.divider()
    st.subheader("📜 레거시 매매 기록 (동기화 이전)")
    try:
        raw_df = pd.read_csv(CSV_URL)
        # Category가 없는 행들만 필터링
        legacy_df = raw_df[~raw_df.iloc[:, 0].isin(["REAL", "VIRT", "AI"])].copy()
        if not legacy_df.empty:
            st.dataframe(legacy_df, use_container_width=True)
    except:
        pass

with tab2:
    if not df_virt.empty:
        # 0:Cat, 1:Time, 2:Sym, 3:Action, 4:Side, 5:Price, 6:PnL, 7:Balance
        df_virt.columns = ["Cat", "시간(KST)", "심볼", "액션", "포지션", "가격", "수익률(ROE)", "잔고(XRP)"]
        
        st.subheader("🤖 AI 가상 자산 변화")
        current_bal = float(str(df_virt['잔고(XRP)'].iloc[-1]).replace(',', ''))
        st.metric("현재 가상 잔고", f"{current_bal:,.2f} XRP", delta=f"{current_bal-1000:.2f} XRP")
        
        fig_virt = px.area(df_virt, x='시간(KST)', y='잔고(XRP)', color_discrete_sequence=['#636EFA'], template="plotly_dark")
        st.plotly_chart(fig_virt, use_container_width=True)
        
        st.subheader("📑 가상 매매 일지")
        st.dataframe(df_virt.sort_values('시간(KST)', ascending=False), use_container_width=True)
    else:
        st.info("가상 매매 기록이 아직 없습니다.")

with tab3:
    if not df_ai.empty:
        # 0:Cat, 1:Time, 2:Sym, 3:Price, 4:Decision, 5:Prob_L, 6:Prob_S, 7:Prob_N
        df_ai.columns = ["Cat", "시간(KST)", "심볼", "현재가", "AI_판단", "LONG_확률", "SHORT_확률", "NEUTRAL_확률"]
        
        st.subheader("🎯 AI 확신도 변화 (최근 기록)")
        # 확률 데이터 숫자 변환
        for col in ['LONG_확률', 'SHORT_확률', 'NEUTRAL_확률']:
            df_ai[col] = pd.to_numeric(df_ai[col], errors='coerce')

        fig_ai = px.line(df_ai.tail(50), x='시간(KST)', y=['LONG_확률', 'SHORT_확률', 'NEUTRAL_확률'], 
                         color_discrete_map={'LONG_확률':'#00CC96', 'SHORT_확률':'#EF553B', 'NEUTRAL_확률':'#636EFA'},
                         template="plotly_dark")
        st.plotly_chart(fig_ai, use_container_width=True)
        
        st.subheader("📝 전체 판단 로그")
        st.dataframe(df_ai.sort_values('시간(KST)', ascending=False), use_container_width=True)
    else:
        st.info("AI 판단 로그가 아직 없습니다.")

st.sidebar.title("⚙️ 시스템 정보")
st.sidebar.write(f"데이터 소스: [Google Sheets](https://docs.google.com/spreadsheets/d/{SHEET_ID})")
st.sidebar.write(f"최종 업데이트: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} (KST)")
st.sidebar.divider()
st.sidebar.caption("기훈님을 위한 클로이 대시보드 V3.0")
