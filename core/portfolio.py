from __future__ import annotations

from typing import Dict, List, Optional

from core.models import PortfolioSnapshot


class PortfolioTracker:
    def __init__(self, client):
        self.client = client

    def fetch_balance(self) -> float:
        return float(self.client.get_account_balance())

    def fetch_positions(self) -> List[Dict[str, object]]:
        return self.client.get_positions()

    def active_positions(self) -> List[Dict[str, object]]:
        return [position for position in self.fetch_positions() if abs(float(position.get("positionAmt", 0.0))) > 0]

    def active_exposure(self) -> float:
        exposure = 0.0
        for position in self.active_positions():
            position_size = abs(float(position.get("positionAmt", 0.0)))
            mark_price = float(position.get("markPrice", position.get("entryPrice", 0.0)))
            exposure += position_size * mark_price
        return exposure

    def live_pnl(self, symbol: str, current_price: float) -> float:
        current_price = float(current_price)
        for position in self.active_positions():
            if position.get("symbol", "").upper() != symbol.upper():
                continue

            amount = float(position.get("positionAmt", 0.0))
            entry_price = float(position.get("entryPrice", 0.0))
            if amount > 0:
                return (current_price - entry_price) * amount
            if amount < 0:
                return (entry_price - current_price) * abs(amount)
        return 0.0

    def unrealized_pnl(self) -> float:
        total = 0.0
        for position in self.active_positions():
            total += float(position.get("unRealizedProfit", 0.0))
        return total

    def get_summary(self) -> Dict[str, object]:
        balance = self.fetch_balance()
        positions = self.active_positions()
        snapshot = PortfolioSnapshot(
            balance=balance,
            unrealized_pnl=self.unrealized_pnl(),
            active_exposure=self.active_exposure(),
            positions=positions,
        )
        return snapshot.to_dict()
