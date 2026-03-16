import os
import json
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

class RiskManager:
    def __init__(self, account_balance=1000.0, max_risk_per_trade=0.01, max_leverage=5, max_drawdown_stop=0.15, daily_loss_limit=0.05):
        self.initial_balance = account_balance
        self.current_balance = account_balance
        self.max_risk_per_trade = max_risk_per_trade
        self.max_leverage = max_leverage
        self.max_drawdown_stop = max_drawdown_stop
        self.daily_loss_limit = daily_loss_limit
        self.peak_balance = account_balance
        self.daily_start_balance = account_balance
        self.last_day = datetime.now().date()

    def set_state(self, current_balance, peak_balance, daily_start_balance=None):
        self.current_balance = current_balance
        self.peak_balance = max(peak_balance, current_balance)
        
        now = datetime.now()
        if now.date() > self.last_day:
            self.daily_start_balance = self.current_balance
            self.last_day = now.date()
        elif daily_start_balance is not None:
            self.daily_start_balance = daily_start_balance
        
    def check_trading_allowed(self):
        now = datetime.now()
        if now.date() > self.last_day:
            self.daily_start_balance = self.current_balance
            self.last_day = now.date()

        # MDD check
        drawdown = (self.peak_balance - self.current_balance) / self.peak_balance
        if drawdown >= self.max_drawdown_stop:
            return False, f"Max Drawdown Exceeded: {drawdown:.2%}"

        # Daily loss limit check
        daily_loss = (self.daily_start_balance - self.current_balance) / self.daily_start_balance
        if daily_loss >= self.daily_loss_limit:
            return False, f"Daily Loss Limit Exceeded: {daily_loss:.2%}"

        return True, "OK"

    def update_balance(self, pnl_amount):
        self.current_balance += pnl_amount
        if self.current_balance > self.peak_balance:
            self.peak_balance = self.current_balance

    def calculate_position_size(self, current_price, stop_loss_pct):
        risk_amount = self.current_balance * self.max_risk_per_trade
        # 수량 = 리스크 금액 / (진입가 * 손절률)
        quantity = risk_amount / (current_price * stop_loss_pct)
        # 레버리지 제한 적용
        max_qty = (self.current_balance * self.max_leverage) / current_price
        return min(quantity, max_qty)

class PerformanceTracker:
    def __init__(self, log_path):
        self.log_path = log_path
        os.makedirs(os.path.dirname(log_path), exist_ok=True)

    def log_trade(self, trade_info):
        with open(self.log_path, 'a') as f:
            f.write(json.dumps(trade_info) + '\n')

    def get_performance_summary(self, window=None):
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

        # 샤프 지표 (단순화)
        sharpe = np.mean(pnl_pcts) / np.std(pnl_pcts) * np.sqrt(365 * 24) if np.std(pnl_pcts) > 0 else 0

        # MDD
        cum_returns = (df['pnl_pct'] + 1).cumprod()
        running_max = cum_returns.cummax()
        drawdown = (cum_returns - running_max) / running_max
        mdd = drawdown.min()

        # 손익비
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
