import pandas as pd
import numpy as np
from feature_engineering import build_features, ensure_stationarity
from label_engineering import label_triple_barrier
from data_fetcher import fetch_historical_data
import os

def test_run():
    symbol = 'XRPUSDT'
    print(f"--- {symbol} 15분봉 기반 정밀 테스트 시작 ---")
    
    # 테스트를 위해 짧은 기간(1개월)만 수집
    data = fetch_historical_data(symbol, interval='15m', start_str='1 month ago UTC')
    if data.empty:
        print("❌ 데이터 수집 실패")
        return
    
    print(f"수집된 원본 데이터 수: {len(data)}")
    
    # 1. 피처 엔지니어링
    df = build_features(data)
    print(f"피처 생성 완료. 컬럼 수: {len(df.columns)}")
    
    # 2. 정상성 변환
    df = ensure_stationarity(df)
    print(f"정상성 변환 완료. 최종 컬럼 수: {len(df.columns)}")
    
    # 3. Triple Barrier 레이블링
    df['target'] = label_triple_barrier(df)
    
    # 결과 요약
    y = df[df['target'] != -1]['target']
    print("\n" + "="*40)
    print(f"✅ 테스트 분석 결과")
    print(f"- 총 피처 수: {len([c for c in df.columns if c not in ['open', 'high', 'low', 'close', 'volume', 'target', 'open time']])}")
    print(f"- 레이블 분포 (0:SHORT, 1:LONG, 2:NEUTRAL):")
    print(y.value_counts(normalize=True))
    print(f"- 레이블 빈도:")
    print(y.value_counts())
    print("="*40)

if __name__ == "__main__":
    test_run()
