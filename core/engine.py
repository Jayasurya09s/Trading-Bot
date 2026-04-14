from __future__ import annotations

from collections import defaultdict, deque
from typing import Dict, Iterable, List, Optional

import pandas as pd

from api.websocket_client import PriceStreamer
from core.journal import log_trade
from core.market_data import build_live_frame, fetch_historical_data
from core.models import Signal
from core.order_manager import OrderManager
from core.portfolio import PortfolioTracker
from core.risk_engine import RiskEngine
from core.strategy import enhanced_strategy
from core.strategies import StrategyEngine
from utils.logger import get_logger


class TradingEngine:
    def __init__(self, client):
        self.client = client
        self.logger = get_logger(__name__)
        self.order_manager = OrderManager(client)
        self.portfolio = PortfolioTracker(client)
        self.risk_engine = RiskEngine()
        self.strategy_engine = StrategyEngine()

    def execute_order(
        self,
        symbol: str,
        side: str,
        order_type: str,
        quantity: float,
        price: float | None = None,
        strategy: str = "manual",
    ) -> Dict[str, object]:
        wallet_balance = None
        try:
            wallet_balance = self.portfolio.fetch_balance()
        except Exception:
            wallet_balance = None

        if wallet_balance is not None:
            effective_price = float(price) if price is not None else float(self.client.get_latest_price(symbol))
            stop_loss = effective_price * 0.99 if side.upper() == "BUY" else effective_price * 1.01
            self.risk_engine.validate_trade(wallet_balance, quantity, effective_price, stop_loss)

        order = self.order_manager.place_order(
            symbol=symbol,
            side=side,
            order_type=order_type,
            quantity=quantity,
            price=price,
            strategy=strategy,
        )

        # Persist all attempts for auditability, including failed API submissions.
        log_trade(order)

        return order

    def backtest(self, symbol: str, strategy_name: str = "ma_rsi", interval: str = "1m", limit: int = 500):
        from core.backtest import run_backtest

        return run_backtest(symbol=symbol, strategy_name=strategy_name, interval=interval, limit=limit)


class LiveTradingEngine:
    def __init__(
        self,
        client,
        symbol: str,
        strategy_name: str = "ma_rsi",
        auto_trade: bool = False,
        quantity: float | None = None,
        interval: str = "1m",
        lookback: int = 100,
    ):
        self.client = client
        self.symbol = symbol.upper()
        self.strategy_name = strategy_name
        self.auto_trade = auto_trade
        self.quantity = quantity
        self.interval = interval
        self.lookback = lookback
        self.logger = get_logger(__name__)
        self.order_manager = OrderManager(client)
        self.portfolio = PortfolioTracker(client)
        self.risk_engine = RiskEngine()
        self.strategy_engine = StrategyEngine()
        self.streamer = PriceStreamer()
        self.price_history = deque(maxlen=max(lookback, 50))
        self.last_signal = Signal.HOLD.value

    def seed_history(self) -> None:
        historical = fetch_historical_data(self.symbol, interval=self.interval, limit=self.lookback, client=self.client)
        if historical.empty:
            return

        for price in historical["close"].tolist():
            self.price_history.append(float(price))

    def _build_frame(self) -> pd.DataFrame:
        return build_live_frame(self.price_history)

    def _on_price(self, symbol: str, price: float) -> None:
        self.price_history.append(float(price))
        if len(self.price_history) < 20:
            return

        frame = self._build_frame()
        signal = self.strategy_engine.evaluate(frame, self.strategy_name)
        live_pnl = self.portfolio.live_pnl(self.symbol, price)
        self.logger.info(
            "Live update",
            extra={
                "symbol": symbol,
                "price": price,
                "signal": signal,
                "live_pnl": live_pnl,
            },
        )
        print(f"[{symbol}] price={price:.4f} signal={signal} live_pnl={live_pnl:.4f}")

        if not self.auto_trade or signal == self.last_signal or signal == Signal.HOLD.value:
            self.last_signal = signal
            return

        order_side = signal
        trade_qty = self.quantity or 0.001

        try:
            wallet_balance = self.portfolio.fetch_balance()
            stop_loss = price * 0.99 if order_side == Signal.BUY.value else price * 1.01
            trade_qty = self.risk_engine.calculate_position_size(wallet_balance, price, stop_loss)
            self.risk_engine.validate_trade(wallet_balance, trade_qty, price, stop_loss)
            order = self.order_manager.place_order(
                symbol=self.symbol,
                side=order_side,
                order_type="MARKET",
                quantity=trade_qty,
                strategy=self.strategy_name,
            )
            log_trade(order)
            print(f"auto_trade={order['status']} qty={trade_qty}")
        except Exception as exc:
            self.logger.exception("Auto-trade failed")
            print(f"auto_trade_failed={exc}")

        self.last_signal = signal

    def run(self) -> None:
        self.seed_history()
        self.streamer.start(self.symbol, self._on_price)

    def stop(self) -> None:
        self.streamer.stop()
