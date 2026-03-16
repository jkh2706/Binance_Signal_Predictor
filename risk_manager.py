import os
import json
import pandas as pd
import numpy as np
from datetime import datetime

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

        # MDD check (Limit 15%)
        drawdown = (self.peak_balance - self.current_balance) / self.peak_balance
        if drawdown >= self.max_drawdown_stop:
            return False, f"Max Drawdown Exceeded ({drawdown:.2%})"

        # Daily loss limit check
        daily_loss = (self.daily_start_balance - self.current_balance) / self.daily_start_balance
        if daily_loss >= self.daily_loss_limit:
            return False, f"Daily Loss Limit Exceeded ({daily_loss:.2%})"

        return True, "OK"

    def update_balance(self, pnl_amount):
        self.current_balance += pnl_amount
        if self.current_balance > self.peak_balance:
            self.peak_balance = self.current_balance

    def calculate_position_size(self, current_price, stop_loss_pct):
        """1% 위함 노출 기반 포지션 사이즈 계산"""
        risk_amount = self.current_balance * self.max_risk_per_trade
        # 수량 = 리스크 금액 / (진입가 * 손절률)
        quantity = risk_amount / (current_price * stop_loss_pct)
        # 레버리지 제한 적용
        max_qty = (self.current_balance * self.max_leverage) / current_price
        return min(quantity, max_qty)
