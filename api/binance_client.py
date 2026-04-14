from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

import pandas as pd
from binance.client import Client
from dotenv import load_dotenv

from utils.logger import get_logger
from utils.retry import retry

load_dotenv()


class BinanceClient:
    def __init__(
        self,
        api_key: Optional[str] = None,
        api_secret: Optional[str] = None,
        testnet: bool = True,
        base_url: Optional[str] = None,
    ):
        self.logger = get_logger(__name__)
        self.api_key = api_key or os.getenv("API_KEY")
        self.api_secret = api_secret or os.getenv("API_SECRET")
        self.base_url = base_url or os.getenv("BASE_URL", "https://testnet.binancefuture.com")
        self.client = Client(self.api_key, self.api_secret, testnet=testnet)
        self.client.FUTURES_URL = self.base_url

    def _ensure_auth(self) -> None:
        if not self.api_key or not self.api_secret:
            raise RuntimeError("API_KEY and API_SECRET are required for authenticated futures operations")

    @retry
    def place_order(
        self,
        symbol: str,
        side: str,
        order_type: str,
        quantity: float,
        price: float | None = None,
        time_in_force: str = "GTC",
        reduce_only: bool = False,
    ) -> Dict[str, Any]:
        self._ensure_auth()

        params: Dict[str, Any] = {
            "symbol": symbol.upper(),
            "side": side.upper(),
            "type": order_type.upper(),
            "quantity": quantity,
        }

        if order_type.upper() == "LIMIT":
            params["price"] = price
            params["timeInForce"] = time_in_force

        if reduce_only:
            params["reduceOnly"] = True

        self.logger.info("Submitting order: %s", params)
        return self.client.futures_create_order(**params)

    @retry
    def get_account_balance(self) -> float:
        self._ensure_auth()
        balances = self.client.futures_account_balance()
        for entry in balances:
            if entry.get("asset") == "USDT":
                return float(entry.get("balance", 0.0))
        return 0.0

    @retry
    def get_positions(self) -> List[Dict[str, Any]]:
        self._ensure_auth()
        return self.client.futures_position_information()

    @retry
    def get_latest_price(self, symbol: str) -> float:
        ticker = self.client.futures_symbol_ticker(symbol=symbol.upper())
        return float(ticker["price"])

    @retry
    def get_historical_klines(self, symbol: str, interval: str = "1m", limit: int = 500) -> pd.DataFrame:
        klines = self.client.futures_klines(symbol=symbol.upper(), interval=interval, limit=limit)
        if not klines:
            return pd.DataFrame()

        frame = pd.DataFrame(
            klines,
            columns=[
                "open_time",
                "open",
                "high",
                "low",
                "close",
                "volume",
                "close_time",
                "quote_asset_volume",
                "number_of_trades",
                "taker_buy_base_asset_volume",
                "taker_buy_quote_asset_volume",
                "ignore",
            ],
        )
        numeric_columns = ["open", "high", "low", "close", "volume"]
        for column in numeric_columns:
            frame[column] = frame[column].astype(float)
        frame["open_time"] = pd.to_datetime(frame["open_time"], unit="ms", utc=True)
        frame["close_time"] = pd.to_datetime(frame["close_time"], unit="ms", utc=True)
        return frame
