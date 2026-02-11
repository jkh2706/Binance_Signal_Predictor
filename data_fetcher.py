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
    COIN-M의 200일 제한 이슈를 완벽하게 해결하기 위해 구간별 루프를 사용합니다.
    """
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
                # 간단한 기간 파싱 (예: '1 year ago UTC')
                try:
                    if 'year' in start_str:
                        num = int(start_str.split()[0])
                        current_start = int((datetime.now() - timedelta(days=365*num)).timestamp() * 1000)
                    elif 'month' in start_str:
                        num = int(start_str.split()[0])
                        current_start = int((datetime.now() - timedelta(days=30*num)).timestamp() * 1000)
                    else:
                        current_start = earliest_ts
                except:
                    current_start = earliest_ts
            
            current_start = max(earliest_ts, current_start)
            end_ts = int(time.time() * 1000)
            
            print(f"  > 수집 시작 시점: {pd.to_datetime(current_start, unit='ms')}")
            
            # 2. 루프 수집 (COIN-M 200일 제한 준수)
            # 한번에 가져올 '시간 윈도우'를 50일로 설정 (매우 안전)
            window_ms = 50 * 24 * 3600 * 1000 
            
            while current_start < end_ts:
                request_end = min(current_start + window_ms, end_ts)
                
                # 해당 50일 윈도우 내에서 klines 가져오기
                # limit 500/1000에 따라 여러번 호출될 수 있음
                temp_start = current_start
                while temp_start < request_end:
                    klines = client.futures_coin_klines(
                        symbol=symbol,
                        interval=interval,
                        startTime=temp_start,
                        endTime=request_end,
                        limit=500
                    )
                    
                    if not klines:
                        # 해당 지점에 데이터가 없으면 다음 윈도우로 점프
                        break
                        
                    all_klines.extend(klines)
                    last_ts = klines[-1][0]
                    
                    if last_ts <= temp_start: # 더 이상 가져올 데이터 없음
                        break
                        
                    temp_start = last_ts + 1
                    time.sleep(0.1) # 속도 제한
                
                # 다음 윈도우로 이동
                current_start = request_end + 1
                # 진행률 출력 (약식)
                print(f"  > 진행 중... ({pd.to_datetime(current_start, unit='ms')}까지 완료)")

            klines = all_klines
        else:
            # SPOT/USD-M은 기본 함수 사용 (내부에서 루프 돌려줌)
            klines = client.get_historical_klines(symbol, interval, start_str, klines_type=klines_type)

        if not klines:
            print("⚠️ 수집된 데이터가 없습니다.")
            return pd.DataFrame()

        # 데이터프레임 구성
        df = pd.DataFrame(klines, columns=[
            'Open time', 'Open', 'High', 'Low', 'Close', 'Volume',
            'Close time', 'Quote asset volume', 'Number of trades',
            'Taker buy base asset volume', 'Taker buy quote asset volume', 'Ignore'
        ])
        
        df['Open time'] = pd.to_datetime(df['Open time'], unit='ms')
        numeric_cols = ['Open', 'High', 'Low', 'Close', 'Volume']
        df[numeric_cols] = df[numeric_cols].apply(pd.to_numeric)
        
        # 중복 제거 및 정렬
        df = df.drop_duplicates(subset=['Open time']).sort_values('Open time')
        
        print(f"✅ 최종 완료: {len(df)}개의 데이터 포인트를 확보했습니다.")
        return df

    except Exception as e:
        print(f"❌ 데이터 수집 실패: {e}")
        return pd.DataFrame()

if __name__ == "__main__":
    # 테스트: 상장 초기부터 현재까지 (XRP)
    data = fetch_historical_data('XRPUSD_PERP', '1h', 'all')
    if not data.empty:
        print(f"첫 데이터: {data['Open time'].iloc[0]}")
        print(f"마지막 데이터: {data['Open time'].iloc[-1]}")
