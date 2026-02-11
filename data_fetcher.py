import os
import pandas as pd
from binance.client import Client
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()

def fetch_historical_data(symbol='BTCUSDT', interval='1h', start_str=None):
    """
    바이낸스에서 과거 K-라인 데이터를 가져와 데이터프레임으로 반환합니다.
    start_str: 예) '1 year ago UTC', '3 days ago UTC'
    """
    api_key = os.getenv('BINANCE_API_KEY')
    api_secret = os.getenv('BINANCE_API_SECRET')
    
    client = Client(api_key, api_secret)
    
    if start_str is None:
        start_str = "1 year ago UTC"
        
    print(f"[{datetime.now()}] {symbol} {interval} 데이터 가져오는 중 (시작: {start_str})...")
    
    try:
        # K-라인 데이터 가져오기
        klines = client.get_historical_klines(symbol, interval, start_str)
        
        # 데이터프레임 변환
        df = pd.DataFrame(klines, columns=[
            'Open time', 'Open', 'High', 'Low', 'Close', 'Volume',
            'Close time', 'Quote asset volume', 'Number of trades',
            'Taker buy base asset volume', 'Taker buy quote asset volume', 'Ignore'
        ])
        
        # 시간 및 숫자 형식 변환
        df['Open time'] = pd.to_datetime(df['Open time'], unit='ms')
        df['Close time'] = pd.to_datetime(df['Close time'], unit='ms')
        
        numeric_cols = ['Open', 'High', 'Low', 'Close', 'Volume']
        df[numeric_cols] = df[numeric_cols].apply(pd.to_numeric)
        
        print(f"✅ 완료: {len(df)}개의 데이터 포인트를 로드했습니다.")
        return df
    except Exception as e:
        print(f"❌ 데이터 수집 중 오류 발생: {e}")
        return pd.DataFrame()

if __name__ == "__main__":
    # 테스트 실행
    symbol = input("데이터를 가져올 코인 기호(예: BTCUSDT): ") or 'BTCUSDT'
    data = fetch_historical_data(symbol, Client.KLINE_INTERVAL_1HOUR, "1 day ago UTC")
    if not data.empty:
        print(data.head())
