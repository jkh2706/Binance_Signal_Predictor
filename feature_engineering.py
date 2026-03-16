import pandas as pd
import numpy as np
from ta import add_all_ta_features
from ta.momentum import RSIIndicator, StochasticOscillator, WilliamsRIndicator, ROCIndicator
from ta.trend import MACD, EMAIndicator, ADXIndicator, CCIIndicator, IchimokuIndicator, TRIXIndicator, PSARIndicator
from ta.volatility import BollingerBands, AverageTrueRange, KeltnerChannel, DonchianChannel, UlcerIndex
from ta.volume import OnBalanceVolumeIndicator, VolumeWeightedAveragePrice, MFIIndicator, ChaikinMoneyFlowIndicator, EaseOfMovementIndicator, ForceIndexIndicator, NegativeVolumeIndexIndicator
from statsmodels.tsa.stattools import adfuller

def build_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    입력: OHLCV DataFrame (columns: open, high, low, close, volume)
    출력: 피처 엔지니어링된 DataFrame (총 80+ 피처 생성 목표)
    [피처 카테고리 - 고도화된 기술적 분석]
    1. 모멘텀 (Momentum)
    2. 트렌드 (Trend)
    3. 변동성 (Volatility)
    4. 거래량 (Volume)
    5. 통계 및 시간 (Statistical & Temporal)
    """
    df = df.copy()
    
    # 컬럼명을 소문자로 통일 (ta 라이브러리 호환성)
    df.columns = [col.lower() for col in df.columns]

    # ── 1. 모멘텀 지표 (Momentum) ──────────────────────────
    df['rsi_14'] = RSIIndicator(df['close'], window=14).rsi()
    df['rsi_7'] = RSIIndicator(df['close'], window=7).rsi()
    df['rsi_21'] = RSIIndicator(df['close'], window=21).rsi()
    
    stoch = StochasticOscillator(df['high'], df['low'], df['close'])
    df['stoch_k'] = stoch.stoch()
    df['stoch_d'] = stoch.stoch_signal()
    
    df['williams_r'] = WilliamsRIndicator(df['high'], df['low'], df['close']).williams_r()
    df['roc_10'] = ROCIndicator(df['close'], window=10).roc()
    df['roc_20'] = ROCIndicator(df['close'], window=20).roc()
    df['trix'] = TRIXIndicator(df['close']).trix()

    # ── 2. 트렌드 지표 (Trend) ─────────────────────────────
    macd = MACD(df['close'])
    df['macd'] = macd.macd()
    df['macd_signal'] = macd.macd_signal()
    df['macd_diff'] = macd.macd_diff()
    
    df['ema_7'] = EMAIndicator(df['close'], window=7).ema_indicator()
    df['ema_25'] = EMAIndicator(df['close'], window=25).ema_indicator()
    df['ema_99'] = EMAIndicator(df['close'], window=99).ema_indicator()
    
    df['ema_cross_7_25'] = df['ema_7'] - df['ema_25']
    df['ema_cross_25_99'] = df['ema_25'] - df['ema_99']
    
    adx_ind = ADXIndicator(df['high'], df['low'], df['close'])
    df['adx'] = adx_ind.adx()
    df['adx_pos'] = adx_ind.adx_pos()
    df['adx_neg'] = adx_ind.adx_neg()
    
    df['cci'] = CCIIndicator(df['high'], df['low'], df['close']).cci()
    
    ichi = IchimokuIndicator(df['high'], df['low'])
    df['ichi_a'] = ichi.ichimoku_a()
    df['ichi_b'] = ichi.ichimoku_b()
    df['ichi_base'] = ichi.ichimoku_base_line()
    df['ichi_conv'] = ichi.ichimoku_conversion_line()
    
    df['psar'] = PSARIndicator(df['high'], df['low'], df['close']).psar()

    # ── 3. 변동성 지표 (Volatility) ─────────────────────────
    bb = BollingerBands(df['close'])
    df['bb_upper'] = bb.bollinger_hband()
    df['bb_lower'] = bb.bollinger_lband()
    df['bb_width'] = bb.bollinger_wband()
    df['bb_pct'] = bb.bollinger_pband()
    
    df['atr_14'] = AverageTrueRange(df['high'], df['low'], df['close'], window=14).average_true_range()
    
    kc = KeltnerChannel(df['high'], df['low'], df['close'])
    df['kc_upper'] = kc.keltner_channel_hband()
    df['kc_lower'] = kc.keltner_channel_lband()
    
    dc = DonchianChannel(df['high'], df['low'], df['close'])
    df['dc_upper'] = dc.donchian_channel_hband()
    df['dc_lower'] = dc.donchian_channel_lband()
    
    df['ulcer'] = UlcerIndex(df['close']).ulcer_index()

    # ── 4. 거래량 지표 (Volume) ────────────────────────────
    df['obv'] = OnBalanceVolumeIndicator(df['close'], df['volume']).on_balance_volume()
    df['mfi'] = MFIIndicator(df['high'], df['low'], df['close'], df['volume']).money_flow_index()
    df['cmf'] = ChaikinMoneyFlowIndicator(df['high'], df['low'], df['close'], df['volume']).chaikin_money_flow()
    df['em'] = EaseOfMovementIndicator(df['high'], df['low'], df['volume']).ease_of_movement()
    df['force_index'] = ForceIndexIndicator(df['close'], df['volume']).force_index()
    df['nvi'] = NegativeVolumeIndexIndicator(df['close'], df['volume']).negative_volume_index()
    
    df['volume_sma_20'] = df['volume'].rolling(20).mean()
    df['volume_ratio'] = df['volume'] / df['volume_sma_20']

    # ── 5. 바이낸스 선물 및 수익률 파생 피처 ────────────────
    # 펀딩비 피처 추가 (data_fetcher에서 로드된 경우)
    if 'fundingrate' in df.columns:
        df['funding_rate'] = df['fundingrate']
    elif 'fundingRate' in df.columns:
        df['funding_rate'] = df['fundingRate']
    else:
        df['funding_rate'] = 0.0

    # 수익률 및 변동성 (Rolling Std)
    for w in [1, 3, 7, 14, 21]:
        df[f'return_{w}'] = df['close'].pct_change(w)
        if w > 1:
            df[f'vol_{w}'] = df['close'].pct_change(1).rolling(w).std()
        # FIX: vol_1 (window 1)은 계산 불가능하므로 0이 아닌 제외
    
    df['high_low_ratio'] = (df['high'] - df['low']) / df['close']
    df['close_open_ratio'] = (df['close'] - df['open']) / df['open']
    df['upper_shadow'] = (df['high'] - df[['open','close']].max(axis=1)) / df['close']
    df['lower_shadow'] = (df[['open','close']].min(axis=1) - df['low']) / df['close']

    # 고차 모멘트 롤링 통계 (왜도, 첨도)
    for w in [7, 14, 30]:
        df[f'roll_mean_{w}'] = df['return_1'].rolling(w).mean()
        df[f'roll_std_{w}'] = df['return_1'].rolling(w).std()
        df[f'roll_max_{w}'] = df['return_1'].rolling(w).max()
        df[f'roll_min_{w}'] = df['return_1'].rolling(w).min()
        df[f'roll_skew_{w}'] = df['return_1'].rolling(w).skew()
        df[f'roll_kurt_{w}'] = df['return_1'].rolling(w).kurt()

    # 시간 피처 (삼각함수 변환으로 주기성 강조)
    if isinstance(df.index, pd.DatetimeIndex):
        df['hour'] = df.index.hour
        df['dayofweek'] = df.index.dayofweek
        df['is_weekend'] = (df.index.dayofweek >= 5).astype(int)
        df['sin_hour'] = np.sin(2 * np.pi * df['hour']/24)
        df['cos_hour'] = np.cos(2 * np.pi * df['hour']/24)
    elif 'open time' in df.columns:
        temp_dt = pd.to_datetime(df['open time'])
        df['hour'] = temp_dt.dt.hour
        df['dayofweek'] = temp_dt.dt.dayofweek
        df['is_weekend'] = (temp_dt.dt.dayofweek >= 5).astype(int)
        df['sin_hour'] = np.sin(2 * np.pi * df['hour']/24)
        df['cos_hour'] = np.cos(2 * np.pi * df['hour']/24)
    
    return df.dropna()

def ensure_stationarity(df: pd.DataFrame, significance: float = 0.05) -> pd.DataFrame:
    """
    ADF 검정으로 비정상성 피처를 퍼센트 변화율로 변환
    금융 시계열의 핵심 전처리 단계 - XGBoost 성능에 직접 영향
    """
    df = df.copy()
    for col in df.select_dtypes(include=[np.number]).columns:
        if col == 'target':
            continue
            
        # FIX: 대상 컬럼의 고유값이 1개 뿐이라면 (constant) 검정을 건너뜀
        # 이는 ADFuller 계산 실패 빛 pct_change() 시의 NaN(0/0) 산출을 방지합니다.
        if df[col].nunique() <= 1:
            continue
            
        vals = df[col].dropna()
        if len(vals) < 30: # 샘플 수가 너무 적어도 건너뜀
            continue
            
        try:
            p_value = adfuller(vals)[1]
            if p_value > significance: # 비정상 시계열
                changed = df[col].pct_change()
                changed = changed.replace([np.inf, -np.inf], np.nan)
                df[col] = changed
        except Exception:
            changed = df[col].pct_change()
            changed = changed.replace([np.inf, -np.inf], np.nan)
            df[col] = changed
    
    return df.dropna()
