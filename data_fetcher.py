import os
import pandas as pd
import time
from binance.client import Client
from binance.enums import HistoricalKlinesType
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()

def fetch_historical_data(symbol='BTCUSDT', interval='1h', start_str='1 year ago UTC', klines_type=HistoricalKlinesType.SPOT):
    """
    바이낸스에서 과거 K-라인 데이터를 가져와 데이터프레임으로 반환합니다.
    COIN-M의 200일 제한 이슈를 해결하기 위해 200일 이상 요청 시 루프 방식을 사용합니다.
    """
    api_key = os.getenv('BINANCE_API_KEY')
    api_secret = os.getenv('BINANCE_API_SECRET')
    client = Client(api_key, api_secret)
    
    if "USD_" in symbol and klines_type == HistoricalKlinesType.SPOT:
        klines_type = HistoricalKlinesType.FUTURES_COIN

    try:
        if klines_type == HistoricalKlinesType.FUTURES_COIN and ('d' in interval or 'h' in interval):
            # 1h, 1d 등은 200일 제한 에러 가능성이 높으므로 Safe Loop 사용
            current_start = None
            try:
                if 'day' in start_str:
                    num = int(start_str.split()[0])
                    current_start = int((datetime.now() - timedelta(days=num)).timestamp() * 1000)
                elif 'year' in start_str:
                    num = int(start_str.split()[0])
                    current_start = int((datetime.now() - timedelta(days=365*num)).timestamp() * 1000)
                elif 'month' in start_str:
                    num = int(start_str.split()[0])
                    current_start = int((datetime.now() - timedelta(days=30*num)).timestamp() * 1000)
                elif 'hour' in start_str:
                    num = int(start_str.split()[0])
                    current_start = int((datetime.now() - timedelta(hours=num)).timestamp() * 1000)
            except: pass

            try:
                earliest_ts = int(client._get_earliest_valid_timestamp(symbol, interval, klines_type=klines_type))
            except:
                earliest_ts = int((datetime.now() - timedelta(days=365)).timestamp() * 1000)
            
            if current_start is None: current_start = earliest_ts
            current_start = max(earliest_ts, current_start)
            end_ts = int(time.time() * 1000)
            
            # 190일 미만이면 직접 호출 시도 (성능 우수)
            if (end_ts - current_start) < (190 * 24 * 3600 * 1000):
                try:
                    klines = client.get_historical_klines(symbol, interval, start_str, klines_type=klines_type)
                    return _format_klines(klines)
                except: pass

            all_klines = []
            window_ms = 100 * 24 * 3600 * 1000 
            while current_start < end_ts:
                request_end = min(current_start + window_ms, end_ts)
                temp_start = current_start
                while temp_start < request_end:
                    klines = client.futures_coin_klines(
                        symbol=symbol, interval=interval,
                        startTime=temp_start, endTime=request_end, limit=500
                    )
                    if not klines: break
                    all_klines.extend(klines)
                    last_ts = klines[-1][0]
                    if last_ts <= temp_start: break
                    temp_start = last_ts + 1
                    time.sleep(0.05)
                current_start = request_end + 1
            return _format_klines(all_klines)
        else:
            klines = client.get_historical_klines(symbol, interval, start_str, klines_type=klines_type)
            return _format_klines(klines)

    except Exception:
        return pd.DataFrame()

def _format_klines(klines):
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
    return df
