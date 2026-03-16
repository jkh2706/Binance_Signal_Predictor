import os
import pandas as pd
import time
from binance.client import Client
from binance.enums import HistoricalKlinesType
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()

DATA_DIR = "/home/jeong-kihun/.openclaw/workspace/Binance_Signal_Predictor/data_storage"

def fetch_historical_data(symbol='BTCUSDT', interval='1h', start_str='1 year ago UTC', klines_type=HistoricalKlinesType.SPOT, max_retries=3):
    """
    로컬 저장소에서 데이터를 로드하고, 필요시 최신 데이터만 바이낸스에서 동기화하여 반환합니다.
    """
    from data_sync import sync_historical_data, sync_funding_rates
    
    # 1. 로컬 데이터 동기화 및 로드
    df = sync_historical_data(symbol, interval, start_str)
    
    # 2. 선물일 경우 펀딩비 추가
    if 'PERP' in symbol or symbol.endswith('USDT'):
        funding_df = sync_funding_rates(symbol.replace('USD_PERP', 'USDT'), start_str)
        if not funding_df.empty and not df.empty:
            df = pd.merge_asof(df.sort_values('Open time'), funding_df.sort_values('timestamp'), 
                              left_on='Open time', right_on='timestamp', direction='backward')
            df['fundingRate'] = df['fundingRate'].fillna(0)
    
    if df.empty:
        print(f"❌ [{symbol}] 데이터를 확보하지 못했습니다.")
        return pd.DataFrame()

    return df
