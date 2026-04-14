from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, Optional
from uuid import uuid4


class OrderStatus(str, Enum):
    PENDING = "PENDING"
    FILLED = "FILLED"
    FAILED = "FAILED"


class OrderSide(str, Enum):
    BUY = "BUY"
    SELL = "SELL"


class OrderType(str, Enum):
    MARKET = "MARKET"
    LIMIT = "LIMIT"


class Signal(str, Enum):
    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"


@dataclass
class OrderRecord:
    symbol: str
    side: str
    order_type: str
    quantity: float
    price: Optional[float] = None
    strategy: str = "manual"
    status: str = OrderStatus.PENDING.value
    id: str = field(default_factory=lambda: uuid4().hex)
    exchange_order_id: Optional[str] = None
    filled_qty: float = 0.0
    error: Optional[str] = None
    raw_response: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def mark_updated(self) -> None:
        self.updated_at = datetime.now(timezone.utc)

    def to_dict(self) -> Dict[str, Any]:
        payload = asdict(self)
        payload["created_at"] = self.created_at.isoformat()
        payload["updated_at"] = self.updated_at.isoformat()
        return payload


@dataclass
class TradeFill:
    symbol: str
    side: str
    quantity: float
    price: float
    pnl: float = 0.0
    strategy: str = "manual"
    order_id: Optional[str] = None
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> Dict[str, Any]:
        payload = asdict(self)
        payload["timestamp"] = self.timestamp.isoformat()
        return payload


@dataclass
class PortfolioSnapshot:
    balance: float
    unrealized_pnl: float
    active_exposure: float
    positions: list[Dict[str, Any]]
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> Dict[str, Any]:
        payload = asdict(self)
        payload["timestamp"] = self.timestamp.isoformat()
        return payload
