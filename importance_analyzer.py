import joblib
import pandas as pd
import matplotlib.pyplot as plt
from xgboost import plot_importance
import os

def analyze_importance(symbol='XRPUSD_PERP'):
    model_path = f"model_{symbol}_xgboost.pkl"
    if not os.path.exists(model_path):
        print("모델 파일을 찾을 수 없습니다.")
        return
    
    model = joblib.load(model_path)
    
    # 특성 중요도 추출
    importance = model.feature_importances_
    features = [
        'RSI', 'MACD', 'MACD_Signal', 'MACD_Hist',
        'SMA_20', 'EMA_20', 'BB_Upper', 'BB_Middle', 'BB_Lower',
        'OBV', 'Vol_MA_20', 'Vol_Change',
        'DXY', 'US10Y', 'Nasdaq100', 'Gold', 'VIX',
        'Oil', 'Semiconductor', 'ETH_BTC',
        'Price_Change_1h', 'Price_Change_4h', 'Price_Change_12h',
        'RSI_Lag_12', 'Vol_MA_Lag_12'
    ]
    
    # 데이터프레임 생성 및 정렬
    feat_imp = pd.DataFrame({'Feature': features, 'Importance': importance})
    feat_imp = feat_imp.sort_values(by='Importance', ascending=False)
    
    print("\n--- AI가 중요하게 생각하는 지표 순위 (TOP 10) ---")
    print(feat_imp.head(10))
    
    # 시각화 저장
    plt.figure(figsize=(10, 8))
    plt.barh(feat_imp['Feature'].head(15)[::-1], feat_imp['Importance'].head(15)[::-1])
    plt.title(f'Feature Importance: {symbol}')
    plt.xlabel('Importance Score')
    plt.grid(axis='x')
    plt.savefig('feature_importance.png')
    print("\n✅ 중요도 분석 차트 저장 완료: feature_importance.png")

if __name__ == "__main__":
    analyze_importance()
