import xgboost as xgb
from sklearn.model_selection import TimeSeriesSplit
from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA
from sklearn.metrics import classification_report, f1_score
import numpy as np
import optuna
import joblib
import os

# 추천 XGBoost 하이퍼파라미터 (XRP 특화)
BEST_PARAMS_XRP = {
    'n_estimators': 500,
    'max_depth': 4, # 과적합 방지: 3 ~ 6 권장
    'learning_rate': 0.05, # 작을수록 안정적 (0.01 ~ 0.1)
    'subsample': 0.8, # 행 샘플링 비율
    'colsample_bytree': 0.8, # 열 샘플링 비율
    'min_child_weight': 5, # 리프 노드 최소 샘플 (과적합 방지)
    'gamma': 0.1, # 분기 최소 손실 감소값
    'reg_alpha': 0.1, # L1 정규화
    'reg_lambda': 1.0, # L2 정규화
    'objective': 'multi:softprob', 
    'num_class': 3,
    'eval_metric': 'mlogloss',
    'random_state': 42,
    'n_jobs': -1, # GCP vCPU 전체 사용
    'tree_method': 'hist', # 빠른 학습
}

def optimize_hyperparams(X_train, y_train, n_trials: int = 50) -> dict:
    """
    Optuna를 이용한 자동 하이퍼파라미터 탐색
    TimeSeriesSplit으로 시계열 데이터 누수 방지
    """
    tscv = TimeSeriesSplit(n_splits=5)

    def objective(trial):
        params = {
            'n_estimators': trial.suggest_int('n_estimators', 100, 1000),
            'max_depth': trial.suggest_int('max_depth', 3, 8),
            'learning_rate': trial.suggest_float('learning_rate', 0.01, 0.3, log=True),
            'subsample': trial.suggest_float('subsample', 0.5, 1.0),
            'colsample_bytree': trial.suggest_float('colsample_bytree', 0.5, 1.0),
            'min_child_weight': trial.suggest_int('min_child_weight', 1, 20),
            'gamma': trial.suggest_float('gamma', 0.0, 1.0),
            'reg_alpha': trial.suggest_float('reg_alpha', 0.0, 2.0),
            'reg_lambda': trial.suggest_float('reg_lambda', 0.0, 2.0),
            'objective': 'multi:softprob',
            'num_class': 3,
            'random_state': 42,
            'n_jobs': -1,
            'tree_method': 'hist',
        }
        
        scores = []
        # X_train이 pandas DataFrame인 경우 처리를 위해 변환
        X_vals = X_train.values if hasattr(X_train, 'values') else X_train
        y_vals = y_train.values if hasattr(y_train, 'values') else y_train

        for train_idx, val_idx in tscv.split(X_vals):
            X_tr, X_val = X_vals[train_idx], X_vals[val_idx]
            y_tr, y_val = y_vals[train_idx], y_vals[val_idx]
            
            model = xgb.XGBClassifier(**params, early_stopping_rounds=30)
            model.fit(
                X_tr, y_tr,
                eval_set=[(X_val, y_val)],
                verbose=False
            )
            pred = model.predict(X_val)
            scores.append(f1_score(y_val, pred, average='weighted'))
            
        return np.mean(scores)

    study = optuna.create_study(direction='maximize')
    study.optimize(objective, n_trials=n_trials)
    
    print(f"최적 F1-Score: {study.best_value:.4f}")
    print(f"최적 파라미터: {study.best_params}")
    return study.best_params

def train_model(X_train, y_train, params: dict = None, use_pca: bool = True, n_components: int = 25, use_weight: bool = True) -> tuple:
    """
    전처리 + 모델 학습 파이프라인
    PCA 25개 주성분 = 분산의 약 90% 설명 (연구 결과 기반)
    use_weight=True 시 SHORT(0) 클래스에 가중치 부여 (3번 전략)
    반환값: (model, scaler, pca_transformer)
    """
    if params is None:
        params = BEST_PARAMS_XRP
    
    # 숏(0) 포지션에 가중치 1.5배 부여 (클래스 불균형 해소)
    sample_weights = None
    if use_weight:
        sample_weights = np.ones(len(y_train))
        sample_weights[y_train == 0] = 1.8 # 숏(0) 가중치 1.8배
        sample_weights[y_train == 1] = 1.0 # 롱(1) 가중치 1.0
        sample_weights[y_train == 2] = 0.8 # 중립(2) 가중치 소폭 하향 (신호 집중)

    # 스케일링
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X_train)
    
    # PCA 차원 축소
    pca = None
    if use_pca:
        pca = PCA(n_components=n_components)
        X_scaled = pca.fit_transform(X_scaled)
        explained = sum(pca.explained_variance_ratio_)
        print(f"PCA: {n_components}개 주성분, 분산 설명력 {explained:.1%}")
        
    # XGBoost 학습
    model = xgb.XGBClassifier(**params)
    model.fit(X_scaled, y_train, sample_weight=sample_weights, verbose=False)
    
    return model, scaler, pca

def predict_with_preprocessing(model, scaler, pca, X_new) -> np.ndarray:
    """ 추론 시 전처리 일관성 보장 """
    X_scaled = scaler.transform(X_new)
    if pca is not None:
        X_scaled = pca.transform(X_scaled)
    return model.predict_proba(X_scaled) # 전체 클래스 확률 반환 (0: Short, 1: Long, 2: Neutral)
