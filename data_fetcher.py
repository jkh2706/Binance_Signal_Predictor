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
            
            # 1년 전 타임스탬프 계산 (수동)
            current_start = int((datetime.now() - timedelta(days=365)).timestamp() * 1000)
            end_ts = int(time.time() * 1000)
            
            while current_start < end_ts:
                # 200일 제한을 피하기 위해 endTime을 반드시 지정하고 그 간격을 좁힘
                # 1시간봉 500개는 약 20일치
                current_end = min(current_start + (500 * 3600 * 1000), end_ts)
                
                klines = client.futures_coin_klines(
                    symbol=symbol,
                    interval=interval,
                    startTime=current_start,
                    endTime=current_end,
                    limit=500
                )
                
                if not klines:
                    # 데이터가 없으면 조금 뒤로 넘어가서 시도
                    current_start += (500 * 3600 * 1000)
                    continue
                    
                all_klines.extend(klines)
                last_ts = klines[-1][0]
                current_start = last_ts + 1
                time.sleep(0.05)
                
                if len(klines) < 10: # 사실상 끝
                     break
            
            klines = all_klines
        else:
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
        print(f"✅ 완료: {len(df)}개의 데이터 포인트를 로드했습니다.")
        return df

    except Exception as e:
        print(f"❌ 데이터 수집 중 오류 발생: {e}")
        return pd.DataFrame()

if __name__ == "__main__":
    data = fetch_historical_data('XRPUSD_PERP', '1h', '1 year ago UTC')
    if not data.empty:
        print(data.tail())
