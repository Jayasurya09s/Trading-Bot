from __future__ import annotations

from typing import Iterable, List

import pandas as pd

from api.binance_client import BinanceClient


def normalize_klines(raw_frame: pd.DataFrame) -> pd.DataFrame:
    if raw_frame.empty:
        return raw_frame

    frame = raw_frame.copy()
    frame = frame.rename(columns={"open_time": "timestamp"})
    frame["timestamp"] = pd.to_datetime(frame["timestamp"], utc=True)
    return frame[["timestamp", "open", "high", "low", "close", "volume"]]


def fetch_historical_data(symbol: str, interval: str = "1m", limit: int = 500, client: BinanceClient | None = None) -> pd.DataFrame:
    client = client or BinanceClient()
    raw = client.get_historical_klines(symbol=symbol, interval=interval, limit=limit)
    return normalize_klines(raw)


def build_live_frame(prices: Iterable[float]) -> pd.DataFrame:
    rows = []
    for price in prices:
        rows.append({"close": float(price)})
    frame = pd.DataFrame(rows)
    if frame.empty:
        return frame
    frame["open"] = frame["close"]
    frame["high"] = frame["close"]
    frame["low"] = frame["close"]
    return frame[["open", "high", "low", "close"]]
