import os
import json
import pandas as pd
import numpy as np
from datetime import datetime

class PerformanceTracker:
    def __init__(self, log_path="logs/trading_log.jsonl"):
        self.log_path = log_path
        os.makedirs(os.path.dirname(log_path), exist_ok=True)

    def log_trade(self, trade_info):
        """거래 내역을 JSONL 파일에 저장"""
        with open(self.log_path, 'a') as f:
            f.write(json.dumps(trade_info) + '\n')

    def get_performance_summary(self, window=None):
        """성과 지표 계산 (누적 수익률, 샤프 비율, MDD, 승률, 손익비)"""
        trades = []
        if not os.path.exists(self.log_path):
            return None

        with open(self.log_path, 'r') as f:
            for line in f:
                trades.append(json.loads(line))

        if not trades:
            return None

        df = pd.DataFrame(trades)
        if window:
            df = df.tail(window)

        pnl_pcts = df['pnl_pct'].values
        win_rate = len(df[df['pnl_pct'] > 0]) / len(df)
        total_return = (df['pnl_pct'] + 1).prod() - 1

        # 샤프 비율 (단순화: 1시간봉 기준 24*365 연율화)
        std = np.std(pnl_pcts)
        sharpe = np.mean(pnl_pcts) / std * np.sqrt(365 * 24) if std > 0 else 0

        # MDD
        cum_returns = (df['pnl_pct'] + 1).cumprod()
        running_max = cum_returns.cummax()
        drawdown = (cum_returns - running_max) / running_max
        mdd = drawdown.min()

        # 손익비 (Profit Factor)
        wins = df[df['pnl_pct'] > 0]['pnl_pct']
        losses = df[df['pnl_pct'] <= 0]['pnl_pct']
        profit_factor = abs(wins.mean() / losses.mean()) if len(losses) > 0 and losses.mean() != 0 else 0

        return {
            "win_rate": win_rate,
            "total_return": total_return,
            "sharpe_ratio": sharpe,
            "mdd": mdd,
            "profit_factor": profit_factor,
            "count": len(df)
        }

    def get_recent_accuracy(self, window=50):
        """최근 N봉의 정확도(승률) 반환"""
        trades = []
        if not os.path.exists(self.log_path):
            return None
        with open(self.log_path, 'r') as f:
            for line in f:
                trades.append(json.loads(line))
        if len(trades) < window:
            return None
        df = pd.DataFrame(trades).tail(window)
        accuracy = len(df[df['pnl_pct'] > 0]) / len(df)
        return accuracy
