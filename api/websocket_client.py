from __future__ import annotations

import os
from typing import Callable, Iterable, List

from binance import ThreadedWebsocketManager
from dotenv import load_dotenv

load_dotenv()


class PriceStreamer:
    def __init__(self):
        self.twm = ThreadedWebsocketManager(
            api_key=os.getenv("API_KEY"),
            api_secret=os.getenv("API_SECRET"),
        )
        self.active_symbols: List[str] = []

    def start(self, symbol_or_symbols: str | Iterable[str], callback: Callable[[str, float], None]) -> None:
        symbols = [symbol_or_symbols] if isinstance(symbol_or_symbols, str) else list(symbol_or_symbols)
        self.active_symbols = [symbol.upper() for symbol in symbols]

        self.twm.start()

        def handle_socket(message):
            event_type = message.get("e")
            if event_type not in {"aggTrade", "trade"}:
                return

            symbol = message.get("s", "").upper()
            price = float(message.get("p", message.get("c", 0.0)))
            callback(symbol, price)

        for symbol in self.active_symbols:
            self.twm.start_aggtrade_socket(symbol=symbol.lower(), callback=handle_socket)

    def stop(self) -> None:
        self.twm.stop()
from binance import ThreadedWebsocketManager
import os
from dotenv import load_dotenv

load_dotenv()

class PriceStreamer:
    def __init__(self):
        self.twm = ThreadedWebsocketManager(
            api_key=os.getenv("API_KEY"),
            api_secret=os.getenv("API_SECRET")
        )

    def start(self, symbol, callback):
        self.twm.start()

        def handle_socket(msg):
            if msg['e'] == 'aggTrade':
                price = msg['p']
                callback(price)

        self.twm.start_aggtrade_socket(
            symbol=symbol.lower(),
            callback=handle_socket
        )

    def stop(self):
        self.twm.stop()