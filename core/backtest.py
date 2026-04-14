from __future__ import annotations

from math import sqrt
from typing import Dict, Tuple

import numpy as np
import pandas as pd

from api.binance_client import BinanceClient
from core.market_data import fetch_historical_data
from core.risk_engine import RiskEngine
from core.strategies import StrategyEngine


INTERVALS_PER_YEAR = {
    "1m": 365 * 24 * 60,
    "3m": 365 * 24 * 20,
    "5m": 365 * 24 * 12,
    "15m": 365 * 24 * 4,
    "30m": 365 * 24 * 2,
    "1h": 365 * 24,
    "4h": 365 * 6,
    "1d": 365,
}


def fetch_data(symbol: str = "BTCUSDT", interval: str = "1m", limit: int = 500, client: BinanceClient | None = None) -> pd.DataFrame:
    frame = fetch_historical_data(symbol=symbol, interval=interval, limit=limit, client=client)
    if frame.empty:
        raise ValueError(f"No historical data returned for {symbol}")
    return frame


def _calculate_metrics(equity_curve: pd.DataFrame, total_trades: int, interval: str) -> Dict[str, float]:
    returns = equity_curve["equity"].pct_change().dropna()
    periods_per_year = INTERVALS_PER_YEAR.get(interval, 252)
    sharpe = 0.0
    if not returns.empty and returns.std() > 0:
        sharpe = float(sqrt(periods_per_year) * returns.mean() / returns.std())

    rolling_max = equity_curve["equity"].cummax()
    drawdown = (equity_curve["equity"] - rolling_max) / rolling_max
    total_return = float(equity_curve["equity"].iloc[-1] / equity_curve["equity"].iloc[0] - 1)

    return {
        "sharpe_ratio": round(sharpe, 4),
        "max_drawdown": round(float(drawdown.min()), 4),
        "total_return": round(total_return, 4),
        "total_trades": float(total_trades),
    }


def run_backtest(
    symbol: str,
    strategy_name: str = "ma_rsi",
    interval: str = "1m",
    limit: int = 500,
    initial_balance: float = 1000.0,
    risk_per_trade: float = 0.01,
) -> Dict[str, object]:
    client = BinanceClient()
    data = fetch_data(symbol=symbol, interval=interval, limit=limit, client=client)

    strategy_engine = StrategyEngine()
    risk_engine = RiskEngine(max_risk_per_trade=risk_per_trade)
    risk_engine.start_session(initial_balance)

    balance = float(initial_balance)
    position_side = 0
    position_qty = 0.0
    entry_price = 0.0

    equity_points = []
    trade_log = []

    warmup = 30 if len(data) > 30 else 1
    for index in range(warmup, len(data)):
        window = data.iloc[: index + 1].copy()
        close_price = float(window.iloc[-1]["close"])
        signal = strategy_engine.evaluate(window, strategy_name)

        if position_side != 0:
            unrealized = position_side * position_qty * (close_price - entry_price)
            equity = balance + unrealized
        else:
            equity = balance

        equity_points.append({"timestamp": window.iloc[-1]["timestamp"], "equity": equity})

        if signal == "HOLD":
            continue

        desired_side = 1 if signal == "BUY" else -1
        if position_side == 0:
            stop_loss = close_price * (0.99 if desired_side == 1 else 1.01)
            position_qty = risk_engine.calculate_position_size(balance, close_price, stop_loss)
            if position_qty <= 0:
                continue

            position_side = desired_side
            entry_price = close_price
            trade_log.append(
                {
                    "timestamp": window.iloc[-1]["timestamp"],
                    "side": signal,
                    "price": close_price,
                    "quantity": position_qty,
                    "event": "ENTRY",
                }
            )
            continue

        if desired_side != position_side:
            pnl = position_side * position_qty * (close_price - entry_price)
            balance += pnl
            risk_engine.record_pnl(pnl)
            trade_log.append(
                {
                    "timestamp": window.iloc[-1]["timestamp"],
                    "side": "SELL" if position_side == 1 else "BUY",
                    "price": close_price,
                    "quantity": position_qty,
                    "event": "EXIT",
                    "pnl": pnl,
                }
            )
            position_side = 0
            position_qty = 0.0
            entry_price = 0.0

            stop_loss = close_price * (0.99 if desired_side == 1 else 1.01)
            position_qty = risk_engine.calculate_position_size(balance, close_price, stop_loss)
            if position_qty <= 0:
                continue

            position_side = desired_side
            entry_price = close_price
            trade_log.append(
                {
                    "timestamp": window.iloc[-1]["timestamp"],
                    "side": signal,
                    "price": close_price,
                    "quantity": position_qty,
                    "event": "ENTRY",
                }
            )

    if position_side != 0:
        final_price = float(data.iloc[-1]["close"])
        pnl = position_side * position_qty * (final_price - entry_price)
        balance += pnl
        risk_engine.record_pnl(pnl)
        trade_log.append(
            {
                "timestamp": data.iloc[-1]["timestamp"],
                "side": "SELL" if position_side == 1 else "BUY",
                "price": final_price,
                "quantity": position_qty,
                "event": "EXIT",
                "pnl": pnl,
            }
        )

        equity_points.append({"timestamp": data.iloc[-1]["timestamp"], "equity": balance})

    equity_curve = pd.DataFrame(equity_points)
    metrics = _calculate_metrics(equity_curve, len(trade_log), interval)

    return {
        "symbol": symbol,
        "strategy": strategy_name,
        "initial_balance": initial_balance,
        "final_balance": round(balance, 4),
        "equity_curve": equity_curve,
        "trades": trade_log,
        "metrics": metrics,
    }
