from __future__ import annotations

from datetime import datetime, timezone
from typing import Dict, List, Optional

from core.models import OrderRecord, OrderStatus
from utils.logger import get_logger


class OrderManager:
    def __init__(self, client):
        self.client = client
        self.logger = get_logger(__name__)
        self.orders: Dict[str, OrderRecord] = {}
        self.history: List[OrderRecord] = []

    def place_order(
        self,
        symbol: str,
        side: str,
        order_type: str,
        quantity: float,
        price: float | None = None,
        strategy: str = "manual",
    ) -> Dict[str, object]:
        record = OrderRecord(
            symbol=symbol.upper(),
            side=side.upper(),
            order_type=order_type.upper(),
            quantity=float(quantity),
            price=float(price) if price is not None else None,
            strategy=strategy,
        )
        self.orders[record.id] = record

        try:
            exchange_order = self.client.place_order(
                symbol=record.symbol,
                side=record.side,
                order_type=record.order_type,
                quantity=record.quantity,
                price=record.price,
            )

            record.raw_response = exchange_order
            record.exchange_order_id = str(exchange_order.get("orderId")) if exchange_order.get("orderId") is not None else None
            record.filled_qty = float(exchange_order.get("executedQty", 0.0) or 0.0)

            exchange_status = str(exchange_order.get("status", "")).upper()
            if exchange_status in {OrderStatus.FILLED.value, "PARTIALLY_FILLED"} or record.order_type == "MARKET":
                record.status = OrderStatus.FILLED.value
                if not record.filled_qty:
                    record.filled_qty = record.quantity
            else:
                record.status = OrderStatus.PENDING.value

            self.logger.info(
                "Order placed | local_id=%s exchange_order_id=%s symbol=%s side=%s type=%s qty=%s status=%s exchange_status=%s",
                record.id,
                record.exchange_order_id,
                record.symbol,
                record.side,
                record.order_type,
                record.quantity,
                record.status,
                exchange_status or "UNKNOWN",
            )
            self._store(record)
            return record.to_dict()
        except Exception as exc:
            record.status = OrderStatus.FAILED.value
            record.error = str(exc)
            self.logger.exception(
                "Order failed | local_id=%s symbol=%s side=%s type=%s qty=%s",
                record.id,
                record.symbol,
                record.side,
                record.order_type,
                record.quantity,
            )
            self._store(record)
            return record.to_dict()

    def update_order_status(self, order_id: str, status: str, filled_qty: float | None = None) -> Dict[str, object]:
        record = self.orders.get(order_id)
        if record is None:
            raise KeyError(f"Unknown order id: {order_id}")

        record.status = status.upper()
        if filled_qty is not None:
            record.filled_qty = float(filled_qty)
        record.mark_updated()
        self._store(record)
        return record.to_dict()

    def get_order(self, order_id: str) -> Dict[str, object] | None:
        record = self.orders.get(order_id)
        return record.to_dict() if record else None

    def get_orders(self) -> Dict[str, Dict[str, object]]:
        return {order_id: record.to_dict() for order_id, record in self.orders.items()}

    def get_active_orders(self) -> List[Dict[str, object]]:
        return [record.to_dict() for record in self.orders.values() if record.status == OrderStatus.PENDING.value]

    def get_order_history(self) -> List[Dict[str, object]]:
        return [record.to_dict() for record in self.history]

    def _store(self, record: OrderRecord) -> None:
        record.mark_updated()
        self.orders[record.id] = record
        self.history.append(record)
