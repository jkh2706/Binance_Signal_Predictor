import os
import time
import pandas as pd
from binance.client import Client
from binance.enums import HistoricalKlinesType
from dotenv import load_dotenv

load_dotenv()
client = Client(os.getenv('BINANCE_API_KEY'), os.getenv('BINANCE_API_SECRET'))

symbol = 'XRPUSD_PERP'
interval = '1h'
try:
    start_ts = int((time.time() - (180 * 24 * 3600)) * 1000)
    print(f"Requesting 180 days ago: {pd.to_datetime(start_ts, unit='ms')}")
    
    k = client.futures_coin_klines(symbol=symbol, interval=interval, startTime=start_ts, limit=1000)
    print(f"Success! Got {len(k)} klines")
    
except Exception as e:
    print(f"Failed: {e}")
