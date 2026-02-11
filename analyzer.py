import pandas as pd
import numpy as np

def calculate_sma(df, period=20):
    """단순 이동평균(SMA) 계산"""
    return df['Close'].rolling(window=period).mean()

def calculate_ema(df, period=20):
    """지수 이동평균(EMA) 계산"""
    return df['Close'].ewm(span=period, adjust=False).mean()

def calculate_rsi(df, period=14):
    """RSI(상대강도지수) 계산"""
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def calculate_macd(df, fast=12, slow=26, signal=9):
    """MACD 및 시그널 라인 계산"""
    exp1 = df['Close'].ewm(span=fast, adjust=False).mean()
    exp2 = df['Close'].ewm(span=slow, adjust=False).mean()
    macd = exp1 - exp2
    signal_line = macd.ewm(span=signal, adjust=False).mean()
    histogram = macd - signal_line
    return macd, signal_line, histogram

def calculate_bollinger_bands(df, period=20, std_dev=2):
    """볼린저 밴드 계산"""
    sma = calculate_sma(df, period)
    std = df['Close'].rolling(window=period).std()
    upper_band = sma + (std * std_dev)
    lower_band = sma - (std * std_dev)
    return upper_band, sma, lower_band

def calculate_obv(df):
    """OBV(On-Balance Volume) 계산"""
    obv = (np.sign(df['Close'].diff()) * df['Volume']).fillna(0).cumsum()
    return obv

def calculate_volume_ma(df, period=20):
    """거래량 이동평균 계산"""
    return df['Volume'].rolling(window=period).mean()

def add_all_indicators(df):
    """모든 주요 지표를 데이터프레임에 추가"""
    df = df.copy()
    
    # 1. 이동평균선
    df['SMA_20'] = calculate_sma(df, 20)
    df['EMA_20'] = calculate_ema(df, 20)
    
    # 2. RSI
    df['RSI'] = calculate_rsi(df, 14)
    
    # 3. MACD
    macd, signal, hist = calculate_macd(df)
    df['MACD'] = macd
    df['MACD_Signal'] = signal
    df['MACD_Hist'] = hist
    
    # 4. 볼린저 밴드
    upper, mid, lower = calculate_bollinger_bands(df)
    df['BB_Upper'] = upper
    df['BB_Middle'] = mid
    df['BB_Lower'] = lower
    
    # 5. 거래량 관련 지표 (신규 추가)
    df['OBV'] = calculate_obv(df)
    df['Vol_MA_20'] = calculate_volume_ma(df, 20)
    df['Vol_Change'] = df['Volume'].pct_change().fillna(0)
    
    return df

if __name__ == "__main__":
    # 데이터 수집 모듈에서 샘플 데이터를 가져와 테스트
    try:
        from data_fetcher import fetch_historical_data
        sample_data = fetch_historical_data('BTCUSDT', '1h', '3 days ago UTC')
        
        if not sample_data.empty:
            analyzed_data = add_all_indicators(sample_data)
            print("\n--- 분석 결과 (최근 5개 행) ---")
            cols_to_show = ['Open time', 'Close', 'RSI', 'MACD', 'BB_Upper', 'BB_Lower']
            print(analyzed_data[cols_to_show].tail())
            print("\n✅ 지표 분석 모듈이 정상적으로 작동합니다!")
    except ImportError:
        print("data_fetcher.py 파일을 찾을 수 없습니다. 같은 디렉토리에 있는지 확인하세요.")
    except Exception as e:
        print(f"오류 발생: {e}")
