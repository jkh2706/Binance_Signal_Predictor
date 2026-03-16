import os
import pandas as pd
import numpy as np
import joblib
from datetime import datetime, timedelta
from binance.client import Client
from dotenv import load_dotenv
from data_fetcher import fetch_historical_data
from analyzer import add_all_indicators
from macro_fetcher import fetch_macro_data, merge_with_binance_data

load_dotenv()

# ─────────────────────────────────────────────
# [BUG 2 FIX] train_xrp_v3.py의 FEATURE_COLUMNS와 반드시 동일하게 유지
# ─────────────────────────────────────────────
FEATURE_COLUMNS = [
    'RSI', 'MACD', 'MACD_Signal', 'MACD_Hist',
    'SMA_20', 'EMA_20', 'BB_Upper', 'BB_Middle', 'BB_Lower',
    'OBV', 'Vol_MA_20', 'Vol_Change',
    'DXY', 'US10Y', 'Nasdaq100', 'Gold', 'VIX',
    'Oil', 'Semiconductor', 'ETH_BTC',
    'Price_Change_1h', 'Price_Change_4h', 'Price_Change_12h',
    'RSI_Lag_12', 'Vol_MA_Lag_12'
]

MACRO_COLUMNS = [
    'DXY', 'US10Y', 'Nasdaq100', 'Gold',
    'VIX', 'Oil', 'Semiconductor', 'ETH_BTC'
]


def get_realtime_prediction(symbol='BTCUSDT'):
    """
    현재 시장 데이터를 분석하여 AI의 실전 예측 결과를 반환합니다.
    """
    print(f"\n--- {symbol} 실시간 AI 분석 시작 ---")

    # 1. 모델 로드
    model_path = f"model_{symbol}.pkl"
    if not os.path.exists(model_path):
        print(f"❌ {symbol}에 대한 학습된 모델 파일({model_path})이 없습니다. 먼저 학습을 진행해 주세요.")
        return None

    model = joblib.load(model_path)

    # 2. 최신 코인 데이터 수집 (지표 계산을 위해 넉넉하게 최근 3일치)
    binance_data = fetch_historical_data(symbol, interval='1h', start_str='3 days ago UTC')
    if binance_data.empty:
        print("❌ 코인 데이터를 가져오는 데 실패했습니다.")
        return None

    # 3. 최신 매크로 데이터 수집
    macro_data = fetch_macro_data(years=0.1)

    # 4. 데이터 가공 및 지표 결합
    df = add_all_indicators(binance_data)

    # [BUG 1 FIX] 매크로 수집 실패 시 0으로 채운 컬럼 삽입
    if macro_data.empty:
        print("⚠️  매크로 데이터 수집 실패 — 해당 피처를 0으로 대체합니다.")
        for col in MACRO_COLUMNS:
            df[col] = 0.0
    else:
        df = merge_with_binance_data(df, macro_data)
        for col in MACRO_COLUMNS:
            if col not in df.columns:
                df[col] = 0.0

    # 5. 예측에 사용할 최신 1행(현재 시점) 추출
    # inf/-inf 방어 처리
    df = df.replace([np.inf, -np.inf], np.nan)

    current_data = df[FEATURE_COLUMNS].tail(1).fillna(0)

    # 6. 예측 실행 (결과값 및 확률)
    prediction = model.predict(current_data)[0]
    probabilities = model.predict_proba(current_data)[0]

    # 3분류 모델 대응 (0: Neutral, 1: Long, 2: Short)
    prob_long = probabilities[1] * 100
    prob_short = probabilities[2] * 100
    prob_neutral = probabilities[0] * 100
    current_price = binance_data['Close'].iloc[-1]

    print("\n" + "="*40)
    print(f"🚀 {symbol} 실전 예측 리포트")
    print(f"⏰ 분석 시각: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} (KST)")
    print(f"💰 현재 가격: {current_price:,.4f} USDT")
    print("-" * 40)

    if prediction == 1:
        print("📢 AI 의견: [매수 유망] ✨")
        print("📈 예측 결과: 향후 4시간 내 1.5% 이상 상승 확률이 높음")
    elif prediction == 2:
        print("📢 AI 의견: [매도 유망] 🔻")
        print("📉 예측 결과: 향후 4시간 내 1.5% 이상 하락 확률이 높음")
    else:
        print("📢 AI 의견: [관망/보유] 💤")
        print("📊 예측 결과: 현재 시점에서 뚜렷한 방향 신호가 포착되지 않음")

    print(f"📊 Long 확신도: {prob_long:.2f}% | Short 확신도: {prob_short:.2f}% | Neutral: {prob_neutral:.2f}%")
    print("="*40)

    return {
        'symbol': symbol,
        'price': current_price,
        'prediction': int(prediction),
        'prob_long': prob_long,
        'prob_short': prob_short,
        'prob_neutral': prob_neutral,
        'time': datetime.now()
    }


if __name__ == "__main__":
    target = input("실시간 예측을 진행할 코인 기호(예: XRPUSD_PERP): ") or 'XRPUSD_PERP'
    get_realtime_prediction(target)
