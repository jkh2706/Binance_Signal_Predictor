import numpy as np
import pandas as pd
from ta.volatility import AverageTrueRange

# ── 방법 1 : 단순 방향 레이블 (현재 사용 중, 기본값) ─────────
def label_direction(df: pd.DataFrame, forward: int = 1) -> pd.Series:
    """
    다음 N봉 종가 기준 상승(1) / 하락(0) 이진 분류
    XRP 연구 결과: XGBoost로 53.8% 정확도 달성 가능
    """
    future_return = df['close'].shift(-forward) / df['close'] - 1
    return (future_return > 0).astype(int)

# ── 방법 2 : 임계값 기반 레이블 (노이즈 필터링) ──────────────
def label_threshold(df: pd.DataFrame, forward: int = 1, threshold: float = 0.003) -> pd.Series:
    """
    작은 움직임을 중립(2)으로 처리하는 3-클래스 레이블
    0 : 하락 (< -threshold)
    1 : 상승 (> +threshold)
    2 : 중립 (|change| <= threshold)
    threshold 추천값: 수수료(0.05%) * 2 + 슬리피지 -> 약 0.3%
    """
    future_return = df['close'].shift(-forward) / df['close'] - 1
    labels = pd.Series(2, index=df.index) # 기본: 중립
    labels[future_return > threshold] = 1 # 상승
    labels[future_return < -threshold] = 0 # 하락
    return labels

# ── 방법 3 : Triple Barrier Method (선물 자동매매 권장) ───────
def label_triple_barrier(df: pd.DataFrame, 
                         atr_multiplier_tp: float = 1.5, 
                         atr_multiplier_sl: float = 1.0, 
                         max_holding: int = 20) -> pd.Series:
    """
    3중 배리어 레이블링 - 자동매매에 가장 현실적인 방법
    """
    # 1. 입력 복사 및 컬럼명 소문화
    df_copy = df.copy()
    df_copy.columns = [c.lower() for c in df_copy.columns]

    # [데이터 무결성 검증] 최소 데이터 확보 확인
    if len(df_copy) < 14 + max_holding:
        print(f"⚠️ [레이블링 중단] 데이터가 부족합니다 (현재: {len(df_copy)}건, 필요: {14+max_holding}건).")
        return pd.Series(-1, index=df.index)
    
    # 2. ATR 계산 (변동성 기반 배리어 설정용)
    atr_indicator = AverageTrueRange(df_copy['high'], df_copy['low'], df_copy['close'], window=14)
    atr = atr_indicator.average_true_range()
    
    # 3. 레이블 초기화 (-1: 계산 불가, 0: SL, 1: TP, 2: Time)
    labels = pd.Series(-1, index=df.index, dtype=int)
    
    # 4. 레이블링 루프
    # 계산 가능한 마지막 지점까지 반복 (미래 데이터를 봐야 하므로 max_holding만큼 뺌)
    for i in range(len(df_copy) - max_holding):
        entry_price = df_copy['close'].iloc[i]
        atr_val = atr.iloc[i]
        
        # ATR이 없거나(초반 14개) 0인 경우 스킵
        if pd.isna(atr_val) or atr_val <= 0:
            continue
            
        tp_price = entry_price + (atr_val * atr_multiplier_tp)
        sl_price = entry_price - (atr_val * atr_multiplier_sl)
        
        # 기본값은 시간 초과(2)
        result = 2 
        
        # 미래 max_holding 봉 동안 배리어 터치 여부 확인
        for j in range(1, max_holding + 1):
            curr_idx = i + j
            high_p = df_copy['high'].iloc[curr_idx]
            low_p = df_copy['low'].iloc[curr_idx]
            
            # 고가가 익절가 도달 시
            if high_p >= tp_price:
                result = 1 # TP 터치
                break
            # 저가가 손절가 도달 시
            if low_p <= sl_price:
                result = 0 # SL 터치
                break
        
        labels.iloc[i] = result
        
    return labels
