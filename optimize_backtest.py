import pandas as pd
import numpy as np
import joblib
import matplotlib.pyplot as plt
import os
from backtester_v7 import run_trailing_stop_backtest

def optimize_threshold():
    results = []
    # 0.4부터 0.7까지 0.05 단위로 테스트
    thresholds = [0.4, 0.45, 0.5, 0.55, 0.6, 0.65]
    
    for th in thresholds:
        print(f"\n[테스트 중] 확신도 문턱: {th*100}%")
        # run_trailing_stop_backtest를 수정하여 결과 balance를 리턴하게 함
        final_bal = run_trailing_stop_backtest(conf_threshold=th)
        results.append({'threshold': th, 'final_balance': final_bal})
    
    res_df = pd.DataFrame(results)
    print("\n" + "="*40)
    print("📈 문턱값별 백테스팅 최적화 결과")
    print(res_df.to_string(index=False))
    print("="*40)
    
    # 최적의 결과 찾기
    best = res_df.loc[res_df['final_balance'].idxmax()]
    print(f"\n🏆 최적의 문턱값: {best['threshold']*100}% (최종 자산: {best['final_balance']:.2f} XRP)")
    
    # 최종 결과 리포트용 그래프 생성
    best_th = best['threshold']
    run_trailing_stop_backtest(conf_threshold=best_th)
    os.rename('trailing_backtest_result.png', 'best_backtest_result.png')

if __name__ == "__main__":
    optimize_threshold()
