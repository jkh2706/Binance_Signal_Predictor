import os
import pandas as pd
import time
from binance.client import Client
from binance.enums import HistoricalKlinesType
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()

def fetch_historical_data(symbol='BTCUSDT', interval='1h', start_str='1 year ago UTC', klines_type=HistoricalKlinesType.SPOT):
    api_key = os.getenv('BINANCE_API_KEY')
    api_secret = os.getenv('BINANCE_API_SECRET')
    client = Client(api_key, api_secret)
    
    if "USD_" in symbol:
        klines_type = HistoricalKlinesType.FUTURES_COIN
    
    print(f"[{datetime.now()}] {symbol} ({klines_type}) {interval} 데이터 수집 중...")

    try:
        if klines_type == HistoricalKlinesType.FUTURES_COIN:
            all_klines = []
            
            # 1. 시작 시간 결정
            earliest_ts = int(client._get_earliest_valid_timestamp(symbol, interval, klines_type=klines_type))
            if start_str == 'all':
                current_start = earliest_ts
            else:
                # 1 year ago 등 간단한 처리
                if 'year' in start_str:
                    num = int(start_str.split()[0])
                    current_start = int((datetime.now() - timedelta(days=365*num)).timestamp() * 1000)
                else:
                    current_start = earliest_ts
            
            current_start = max(earliest_ts, current_start)
            end_ts = int(time.time() * 1000)
            
            print(f"  > 수집 범위: {pd.to_datetime(current_start, unit='ms')} ~ {pd.to_datetime(end_ts, unit='ms')}")
            
            # 2. 200일 제한을 피하기 위한 90일 단위 쪼개기
            chunk_ms = 90 * 24 * 3600 * 1000 
            
            while current_start < end_ts:
                chunk_end = min(current_start + chunk_ms, end_ts)
                
                # 구간 내 세부 수집 (500개씩)
                temp_start = current_start
                while temp_start < chunk_end:
                    # print(f"    - Fetching {pd.to_datetime(temp_start, unit='ms')} ~ {pd.to_datetime(chunk_end, unit='ms')}")
                    klines = client.futures_coin_klines(
                        symbol=symbol,
                        interval=interval,
                        startTime=temp_start,
                        endTime=chunk_end,
                        limit=500
                    )
                    
                    if not klines:
                        break
                        
                    all_klines.extend(klines)
                    last_ts = klines[-1][0]
                    
                    if last_ts <= temp_start:
                        break
                    temp_start = last_ts + 1
                    time.sleep(0.02)
                
                current_start = chunk_end + 1
                time.sleep(0.05)

            klines = all_klines
        else:
            # SPOT/USD-M (기본 기능 활용)
            klines = client.get_historical_klines(symbol, interval, start_str, klines_type=klines_type)

        if not klines:
            return pd.DataFrame()

        df = pd.DataFrame(klines, columns=[
            'Open time', 'Open', 'High', 'Low', 'Close', 'Volume',
            'Close time', 'Quote asset volume', 'Number of trades',
            'Taker buy base asset volume', 'Taker buy quote asset volume', 'Ignore'
        ])
        df['Open time'] = pd.to_datetime(df['Open time'], unit='ms')
        numeric_cols = ['Open', 'High', 'Low', 'Close', 'Volume']
        df[numeric_cols] = df[numeric_cols].apply(pd.to_numeric)
        
        df = df.drop_duplicates(subset=['Open time']).sort_values('Open time')
        print(f"✅ 완료: {len(df)}개의 데이터 포인트를 로드했습니다.")
        return df

    except Exception as e:
        print(f"❌ 데이터 수집 중 오류 발생: {e}")
        return pd.DataFrame()

if __name__ == "__main__":
    # 2년치 테스트
    data = fetch_historical_data('XRPUSD_PERP', '1h', '2 year ago UTC')
    if not data.empty:
        print(f"Range: {data['Open time'].iloc[0]} to {data['Open time'].iloc[-1]}")
