import os
import pandas as pd
from binance.client import Client
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

def fetch_historical_data(symbol='BTCUSDT', interval='1h', start_str='1 day ago UTC'):
    """
    바이낸스에서 과거 K-라인 데이터를 가져와 데이터프레임으로 반환합니다.
    """
    api_key = os.getenv('BINANCE_API_KEY')
    api_secret = os.getenv('BINANCE_API_SECRET')
    
    client = Client(api_key, api_secret)
    
    print(f"[{datetime.now()}] {symbol} {interval} 데이터 가져오는 중 (시작: {start_str})...")
    
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
    
    print(f"완료: {len(df)}개의 데이터 포인트를 로드했습니다.")
    return df

if __name__ == "__main__":
    # 테스트 실행
    try:
        data = fetch_historical_data('BTCUSDT', Client.KLINE_INTERVAL_1HOUR, "1 day ago UTC")
        print(data.head())
    except Exception as e:
        print(f"오류 발생: {e}")
        print("참고: .env 파일에 BINANCE_API_KEY와 SECRET이 설정되어 있어야 합니다.")
