import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta

def fetch_macro_data(years=1):
    """
    Yahoo Finance에서 주요 거시 경제 지표 데이터를 가져옵니다.
    """
    end_date = datetime.now()
    start_date = end_date - timedelta(days=years * 365 + 10)
    
    # 1. 대상 지표 설정 (보강됨)
    tickers = {
        'DX-Y.NYB': 'DXY',      # 달러 인덱스
        '^TNX': 'US10Y',        # 미국채 10년물 금리
        '^NDX': 'Nasdaq100',    # 나스닥 100
        'GC=F': 'Gold',         # 금 선물
        '^VIX': 'VIX',          # 변동성 지수
        'CL=F': 'Oil',          # 국제 유가 (WTI)
        'SMH': 'Semiconductor', # 반도체 지수 (ETF)
        'ETH-BTC': 'ETH_BTC'    # 이더리움/비트코인 비율
    }
    
    print(f"[{datetime.now()}] 매크로 지표 데이터 수집 중 (기간: {years}년)...")
    
    try:
        macro_frames = []
        for ticker, name in tickers.items():
            print(f"[{name}] 데이터 다운로드 중...")
            df = yf.download(ticker, start=start_date, end=end_date)
            if not df.empty:
                # MultiIndex 방지: 단일 컬럼만 추출
                if isinstance(df.columns, pd.MultiIndex):
                    df.columns = df.columns.get_level_values(0)
                
                col = 'Adj Close' if 'Adj Close' in df.columns else 'Close'
                df = df[[col]].rename(columns={col: name})
                macro_frames.append(df)
        
        if not macro_frames:
            return pd.DataFrame()
            
        data = pd.concat(macro_frames, axis=1)
        data = data.reset_index()
        
        # Date 컬럼 이름 표준화
        if 'Date' not in data.columns:
            # 인덱스 이름이 다를 수 있음
            data.rename(columns={data.columns[0]: 'Date'}, inplace=True)
        
        # 주말/공휴일 빈칸 채우기
        data = data.ffill().bfill()
        
        print(f"✅ 완료: {len(data)}일치 매크로 데이터를 로드했습니다.")
        return data
    except Exception as e:
        print(f"❌ 매크로 데이터 수집 중 오류 발생: {e}")
        return pd.DataFrame()

def merge_with_binance_data(binance_df, macro_df):
    """
    바이낸스 시간봉 데이터와 일봉 매크로 데이터를 결합합니다.
    """
    if macro_df.empty:
        print("⚠️ 매크로 데이터가 비어있어 결합을 건너뜁니다.")
        return binance_df

    # 1. 날짜 기준 결합을 위해 'Date_Join' 컬럼 생성
    binance_df['Date_Join'] = binance_df['Open time'].dt.date
    macro_df['Date_Join'] = pd.to_datetime(macro_df['Date']).dt.date
    
    # 2. Merge
    merged_df = pd.merge(binance_df, macro_df, on='Date_Join', how='left')
    
    # 3. 빈칸 채우기
    macro_cols = ['DXY', 'US10Y', 'Nasdaq100', 'Gold', 'VIX', 'Oil', 'Semiconductor', 'ETH_BTC']
    for col in macro_cols:
        if col in merged_df.columns:
            merged_df[col] = merged_df[col].ffill().bfill()
    
    # 불필요한 컬럼 제거
    cols_to_drop = ['Date_Join']
    if 'Date' in merged_df.columns: cols_to_drop.append('Date')
    merged_df = merged_df.drop(columns=cols_to_drop)
    
    return merged_df

if __name__ == "__main__":
    macro_data = fetch_macro_data(years=1)
    if not macro_data.empty:
        print(macro_data.tail())
