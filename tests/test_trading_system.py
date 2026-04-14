from __future__ import annotations

import pandas as pd
import pytest

from core.order_manager import OrderManager
from core.portfolio import PortfolioTracker
from core.risk_engine import RiskEngine
from core.strategies import StrategyEngine
from utils.validator import TradingValidationError, validate_order_inputs


def test_breakout_strategy_generates_buy_signal():
    frame = pd.DataFrame(
        [
            {"open": 100.0, "high": 101.0, "low": 99.5, "close": 100.5},
            {"open": 100.5, "high": 101.5, "low": 100.0, "close": 102.0},
        ]
    )

    signal = StrategyEngine().evaluate(frame, "breakout")
    assert signal == "BUY"


def test_risk_engine_limits_position_size():
    engine = RiskEngine(max_risk_per_trade=0.01, max_daily_loss=0.05, max_position_pct=0.2)
    engine.start_session(1000)

    size = engine.calculate_position_size(balance=1000, entry_price=100, stop_loss_price=98)
    assert size > 0

    engine.validate_trade(balance=1000, quantity=size, price=100, stop_loss_price=98)


def test_portfolio_live_pnl_long_and_short():
    class DummyClient:
        def get_positions(self):
            return [
                {"symbol": "BTCUSDT", "positionAmt": "0.5", "entryPrice": "100.0", "markPrice": "105.0", "unRealizedProfit": "2.5"},
                {"symbol": "ETHUSDT", "positionAmt": "-1.0", "entryPrice": "200.0", "markPrice": "190.0", "unRealizedProfit": "10.0"},
            ]

        def get_account_balance(self):
            return 1000.0

    portfolio = PortfolioTracker(DummyClient())
    assert portfolio.live_pnl("BTCUSDT", 105.0) == 2.5
    assert portfolio.live_pnl("ETHUSDT", 190.0) == 10.0
    assert portfolio.active_exposure() == 0.5 * 105.0 + 1.0 * 190.0


def test_order_manager_tracks_filled_and_pending_orders():
    class DummyClient:
        def __init__(self):
            self.calls = []

        def place_order(self, symbol, side, order_type, quantity, price=None):
            self.calls.append((symbol, side, order_type, quantity, price))
            status = "FILLED" if order_type == "MARKET" else "NEW"
            return {"orderId": 123, "status": status, "executedQty": quantity}

    manager = OrderManager(DummyClient())
    market_order = manager.place_order("BTCUSDT", "BUY", "MARKET", 0.01)
    limit_order = manager.place_order("BTCUSDT", "SELL", "LIMIT", 0.01, price=60000)

    assert market_order["status"] == "FILLED"
    assert limit_order["status"] == "PENDING"
    assert len(manager.get_order_history()) == 2


def test_order_manager_marks_failed_on_client_exception():
    class FailingClient:
        def place_order(self, symbol, side, order_type, quantity, price=None):
            raise RuntimeError("boom")

    manager = OrderManager(FailingClient())
    order = manager.place_order("BTCUSDT", "BUY", "MARKET", 0.01)
    assert order["status"] == "FAILED"
    assert "boom" in str(order.get("error", ""))


def test_validate_order_inputs_positive_case():
    symbol, side, order_type, qty, price = validate_order_inputs("btcusdt", "buy", "market", 0.01, None)
    assert symbol == "BTCUSDT"
    assert side == "BUY"
    assert order_type == "MARKET"
    assert qty == 0.01
    assert price is None


def test_validate_order_inputs_limit_requires_price_negative_case():
    with pytest.raises(TradingValidationError, match="Limit orders require a price"):
        validate_order_inputs("BTCUSDT", "SELL", "LIMIT", 0.01, None)


def test_validate_order_inputs_rejects_invalid_quantity_negative_case():
    with pytest.raises(TradingValidationError, match="Quantity must be greater than zero"):
        validate_order_inputs("BTCUSDT", "SELL", "MARKET", 0.0, None)


def test_risk_engine_blocks_trade_after_daily_loss_negative_case():
    engine = RiskEngine(max_risk_per_trade=0.01, max_daily_loss=0.05, max_position_pct=0.2)
    engine.start_session(1000)
    engine.record_pnl(-60.0)

    with pytest.raises(ValueError, match="Daily loss limit exceeded"):
        engine.validate_trade(balance=1000, quantity=0.01, price=100, stop_loss_price=99)


def test_strategy_engine_rejects_unknown_strategy_negative_case():
    frame = pd.DataFrame([{"open": 1, "high": 1, "low": 1, "close": 1}])
    with pytest.raises(ValueError, match="Unknown strategy"):
        StrategyEngine().evaluate(frame, "unknown_strategy")
