from __future__ import annotations

from typing import Callable, Dict

import pandas as pd
import ta

from core.models import Signal


def ma_rsi(df: pd.DataFrame) -> str:
    frame = df.copy()
    if len(frame) < 20:
        return Signal.HOLD.value

    frame["short_ma"] = frame["close"].rolling(5).mean()
    frame["long_ma"] = frame["close"].rolling(20).mean()
    frame["rsi"] = ta.momentum.RSIIndicator(frame["close"], window=14).rsi()

    last = frame.iloc[-1]

    if pd.isna(last["short_ma"]) or pd.isna(last["long_ma"]) or pd.isna(last["rsi"]):
        return Signal.HOLD.value

    if last["short_ma"] > last["long_ma"] and last["rsi"] < 70:
        return Signal.BUY.value
    if last["short_ma"] < last["long_ma"] and last["rsi"] > 30:
        return Signal.SELL.value
    return Signal.HOLD.value


def breakout(df: pd.DataFrame) -> str:
    if len(df) < 2:
        return Signal.HOLD.value

    last = df.iloc[-1]
    prev = df.iloc[-2]

    if last["close"] > prev["high"]:
        return Signal.BUY.value
    if last["close"] < prev["low"]:
        return Signal.SELL.value
    return Signal.HOLD.value


class StrategyEngine:
    def __init__(self) -> None:
        self._strategies: Dict[str, Callable[[pd.DataFrame], str]] = {
            "ma_rsi": ma_rsi,
            "breakout": breakout,
        }

    def available_strategies(self) -> list[str]:
        return sorted(self._strategies.keys())

    def evaluate(self, df: pd.DataFrame, strategy_name: str) -> str:
        if strategy_name not in self._strategies:
            raise ValueError(f"Unknown strategy: {strategy_name}")
        return self._strategies[strategy_name](df)

    def evaluate_all(self, df: pd.DataFrame) -> Dict[str, str]:
        return {name: strategy(df) for name, strategy in self._strategies.items()}

    def consensus_signal(self, df: pd.DataFrame) -> str:
        signals = [signal for signal in self.evaluate_all(df).values() if signal != Signal.HOLD.value]
        if not signals:
            return Signal.HOLD.value
        if signals.count(Signal.BUY.value) > signals.count(Signal.SELL.value):
            return Signal.BUY.value
        if signals.count(Signal.SELL.value) > signals.count(Signal.BUY.value):
            return Signal.SELL.value
        return Signal.HOLD.value


STRATEGIES = StrategyEngine()._strategies