from __future__ import annotations

from dataclasses import dataclass
from datetime import date


@dataclass
class RiskEngine:
    max_risk_per_trade: float = 0.01
    max_daily_loss: float = 0.05
    max_position_pct: float = 0.20

    def __post_init__(self) -> None:
        self._day = date.today()
        self._starting_balance: float | None = None
        self._daily_realized_pnl = 0.0

    def start_session(self, balance: float) -> None:
        self._starting_balance = float(balance)
        self._day = date.today()
        self._daily_realized_pnl = 0.0

    def _ensure_session(self, balance: float) -> None:
        if self._starting_balance is None or self._day != date.today():
            self.start_session(balance)

    def position_risk_amount(self, balance: float) -> float:
        return float(balance) * float(self.max_risk_per_trade)

    def calculate_position_size(
        self,
        balance: float,
        entry_price: float,
        stop_loss_price: float | None = None,
        leverage: float = 1.0,
    ) -> float:
        balance = float(balance)
        entry_price = float(entry_price)
        self._ensure_session(balance)

        risk_amount = self.position_risk_amount(balance)
        if stop_loss_price is not None:
            stop_loss_price = float(stop_loss_price)
            per_unit_risk = abs(entry_price - stop_loss_price)
            quantity = risk_amount / per_unit_risk if per_unit_risk else 0.0
        else:
            quantity = risk_amount / entry_price

        max_notional = balance * float(self.max_position_pct) * float(leverage)
        quantity = min(quantity, max_notional / entry_price)
        return max(round(quantity, 6), 0.0)

    def validate_trade(
        self,
        balance: float,
        quantity: float,
        price: float,
        stop_loss_price: float | None = None,
        leverage: float = 1.0,
    ) -> None:
        self._ensure_session(balance)

        if self._starting_balance:
            max_daily_loss_amount = self._starting_balance * float(self.max_daily_loss)
            if abs(self._daily_realized_pnl) >= max_daily_loss_amount and self._daily_realized_pnl < 0:
                raise ValueError("Daily loss limit exceeded")

        expected_quantity = self.calculate_position_size(balance, price, stop_loss_price, leverage)
        if quantity > expected_quantity * 1.05:
            raise ValueError("Risk too high per trade")

    def record_pnl(self, pnl: float) -> None:
        self._ensure_session(self._starting_balance or 0.0)
        self._daily_realized_pnl += float(pnl)

    def remaining_daily_loss(self) -> float:
        if self._starting_balance is None:
            return 0.0
        limit = self._starting_balance * float(self.max_daily_loss)
        return max(limit + self._daily_realized_pnl, 0.0)
