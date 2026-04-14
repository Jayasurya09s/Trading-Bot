from __future__ import annotations

import csv
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Iterable, List


FILE_PATH = Path("data/trades.csv")
HEADERS = [
    "timestamp",
    "order_id",
    "symbol",
    "side",
    "order_type",
    "quantity",
    "price",
    "status",
    "pnl",
    "strategy",
    "notes",
]


def log_trade(data: Dict[str, object]) -> None:
    FILE_PATH.parent.mkdir(parents=True, exist_ok=True)
    file_exists = FILE_PATH.exists() and FILE_PATH.stat().st_size > 0

    with FILE_PATH.open("a", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=HEADERS)
        if not file_exists:
            writer.writeheader()

        writer.writerow(
            {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "order_id": data.get("order_id", ""),
                "symbol": data.get("symbol", ""),
                "side": data.get("side", ""),
                "order_type": data.get("order_type", ""),
                "quantity": data.get("quantity", ""),
                "price": data.get("price", ""),
                "status": data.get("status", ""),
                "pnl": data.get("pnl", 0.0),
                "strategy": data.get("strategy", "manual"),
                "notes": data.get("notes", ""),
            }
        )


def load_trades() -> List[Dict[str, str]]:
    if not FILE_PATH.exists() or FILE_PATH.stat().st_size == 0:
        return []

    with FILE_PATH.open("r", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))
