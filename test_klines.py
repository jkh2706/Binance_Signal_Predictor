import os
from binance.client import Client
from binance.enums import HistoricalKlinesType
from dotenv import load_dotenv

load_dotenv()
client = Client(os.getenv('BINANCE_API_KEY'), os.getenv('BINANCE_API_SECRET'))

try:
    print("Testing BTCUSD_PERP (COIN-M) 1h 1 day...")
    k = client.get_historical_klines("BTCUSD_PERP", Client.KLINE_INTERVAL_1HOUR, "1 day ago UTC", klines_type=HistoricalKlinesType.FUTURES_COIN)
    print(f"Success: {len(k)} candles")
except Exception as e:
    print(f"Failed: {e}")

try:
    print("\nTesting futures_coin_klines directly...")
    k = client.futures_coin_klines(symbol="XRPUSD_PERP", interval="1h", limit=100)
    print(f"Success: {len(k)} candles")
except Exception as e:
    print(f"Failed: {e}")

try:
    print("\nTesting USD-M 1h 10 days...")
    k = client.get_historical_klines("XRPUSDT", Client.KLINE_INTERVAL_1HOUR, "10 days ago UTC", klines_type=HistoricalKlinesType.FUTURES)
    print(f"Success: {len(k)} candles")
except Exception as e:
    print(f"Failed: {e}")
