import os
import pandas as pd
import time
from binance.client import Client
from binance.enums import HistoricalKlinesType
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()

# 데이터 저장 경로 설정
DATA_DIR = "/home/jeong-kihun/.openclaw/workspace/Binance_Signal_Predictor/data_storage"
if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)

def sync_historical_data(symbol='XRPUSDT', interval='15m', start_str='3 years ago UTC'):
    """
    바이낸스에서 데이터를 가져와 로컬에 저장하고, 최신 데이터만 증분 업데이트합니다.
    """
    api_key = os.getenv('BINANCE_API_KEY')
    api_secret = os.getenv('BINANCE_API_SECRET')
    client = Client(api_key, api_secret)
    
    file_path = os.path.join(DATA_DIR, f"{symbol}_{interval}.csv")
    
    # 1. 기존 데이터 로드
    existing_df = pd.DataFrame()
    if os.path.exists(file_path):
        try:
            existing_df = pd.read_csv(file_path)
            existing_df['Open time'] = pd.to_datetime(existing_df['Open time'])
            print(f"✅ 로컬 데이터 로드 성공: {len(existing_df)}건")
        except Exception as e:
            print(f"⚠️ 로컬 데이터 로드 실패: {e}")

    # 2. 시작 시점 결정
    if not existing_df.empty:
        # 마지막 데이터의 다음 시간부터 수집
        last_ts = existing_df['Open time'].max()
        start_ts = int(last_ts.timestamp() * 1000) + 1
        print(f"🔄 증분 업데이트 시작: {last_ts}")
    else:
        # 데이터가 없으면 처음부터 수집
        start_ts = start_str
        print(f"📥 전체 데이터 수집 시작: {start_str}")

    # 3. 데이터 수집 (재시도 로직 포함)
    try:
        klines = client.get_historical_klines(symbol, interval, start_ts)
        if not klines:
            print("ℹ️ 추가할 새로운 데이터가 없습니다.")
            return existing_df

        new_df = _format_klines(klines)
        print(f"✅ 신규 데이터 수집 완료: {len(new_df)}건")

        # 4. 합치기 및 저장
        final_df = pd.concat([existing_df, new_df]).drop_duplicates(subset=['Open time']).sort_values('Open time')
        final_df.to_csv(file_path, index=False)
        print(f"💾 최종 데이터 저장 완료: {len(final_df)}건 ({file_path})")
        return final_df

    except Exception as e:
        print(f"❌ 데이터 수집 중 오류 발생: {e}")
        return existing_df

def sync_funding_rates(symbol='XRPUSDT', start_str='3 years ago UTC'):
    """
    바이낸스 선물 펀딩비를 가져와 로컬에 저장하고 업데이트합니다.
    """
    api_key = os.getenv('BINANCE_API_KEY')
    api_secret = os.getenv('BINANCE_API_SECRET')
    client = Client(api_key, api_secret)
    
    file_path = os.path.join(DATA_DIR, f"{symbol}_funding.csv")
    
    existing_df = pd.DataFrame()
    if os.path.exists(file_path):
        try:
            existing_df = pd.read_csv(file_path)
            existing_df['timestamp'] = pd.to_datetime(existing_df['timestamp'])
        except: pass

    start_ts = int(existing_df['timestamp'].max().timestamp() * 1000) + 1 if not existing_df.empty else start_str
    
    try:
        # get_funding_rate_history는 limit이 1000개이므로 반복 호출 필요할 수 있음
        # 하지만 get_historical_klines와 달리 자동으로 루프 돌지 않으므로 직접 구현
        all_funding = []
        # 간단하게 최근 데이터 위주로 가져오거나 필요한 만큼 루프
        funding = client.futures_funding_rate(symbol=symbol, startTime=start_ts, limit=1000)
        all_funding.extend(funding)
        
        if not all_funding:
            return existing_df
            
        new_df = pd.DataFrame(all_funding)
        new_df['timestamp'] = pd.to_datetime(new_df['fundingTime'], unit='ms')
        new_df['fundingRate'] = new_df['fundingRate'].astype(float)
        new_df = new_df[['timestamp', 'fundingRate']]
        
        final_df = pd.concat([existing_df, new_df]).drop_duplicates(subset=['timestamp']).sort_values('timestamp')
        final_df.to_csv(file_path, index=False)
        return final_df
    except Exception as e:
        print(f"❌ 펀딩비 수집 오류: {e}")
        return existing_df

def _format_klines(klines):
    df = pd.DataFrame(klines, columns=[
        'Open time', 'Open', 'High', 'Low', 'Close', 'Volume',
        'Close time', 'Quote asset volume', 'Number of trades',
        'Taker buy base asset volume', 'Taker buy quote asset volume', 'Ignore'
    ])
    df['Open time'] = pd.to_datetime(df['Open time'], unit='ms')
    numeric_cols = ['Open', 'High', 'Low', 'Close', 'Volume']
    df[numeric_cols] = df[numeric_cols].apply(pd.to_numeric)
    return df

if __name__ == "__main__":
    sync_historical_data()
