import os
import time
from datetime import datetime, timedelta
from train_xrp_v4 import train_xrp_xgboost_model_v4
from model_training import optimize_hyperparams

class WFOPipeline:
    def __init__(self, cycle_hours=168, threshold_degradation=0.1, use_optuna=True):
        self.cycle_hours = cycle_hours
        self.threshold_degradation = threshold_degradation
        self.use_optuna = use_optuna
        self.last_train_time = None
        self.last_accuracy = 0.0

    def should_retrain(self, current_accuracy=None):
        """재학습 필요 여부 판단 (시간 주기 + 성능 저하)"""
        now = datetime.now()
        
        # 1. 시간 주기 체크 (168시간 = 1주일)
        if self.last_train_time is None or (now - self.last_train_time) > timedelta(hours=self.cycle_hours):
            print(f"⏰ [WFO] 학습 주기({self.cycle_hours}h) 도달. 재학습을 시작합니다.")
            return True
            
        # 2. 성능 저하 체크
        if current_accuracy is not None and self.last_accuracy > 0:
            degradation = (self.last_accuracy - current_accuracy) / self.last_accuracy
            if degradation >= self.threshold_degradation:
                print(f"📉 [WFO] 성능 저하({degradation:.2%}) 감지. 즉시 재학습을 시작합니다.")
                return True
                
        return False

    def execute(self):
        """학습 실행 및 메타데이터 업데이트"""
        print(f"🚀 [WFO] 파이프라인 실행 중... ({datetime.now()})")
        model = train_xrp_xgboost_model_v4(use_optuna=self.use_optuna)
        if model:
            self.last_train_time = datetime.now()
            # 정확도는 로그에서 파싱하거나 별도 리턴값이 필요함 (현재 v4는 model만 리턴)
            print("✅ [WFO] 학습 파이프라인 완료.")
            return True
        return False

if __name__ == "__main__":
    wfo = WFOPipeline()
    if wfo.should_retrain():
        wfo.execute()
