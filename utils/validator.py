from __future__ import annotations

from dataclasses import dataclass

from core.models import OrderSide, OrderType


@dataclass
class TradingValidationError(ValueError):
    message: str

    def __str__(self) -> str:
        return self.message


def validate_symbol(symbol: str) -> str:
    if not symbol or not symbol.strip():
        raise TradingValidationError("Symbol is required")
    cleaned = symbol.strip().upper()
    if len(cleaned) < 6:
        raise TradingValidationError("Symbol looks invalid")
    return cleaned


def validate_side(side: str) -> str:
    if not side:
        raise TradingValidationError("Side is required")
    cleaned = side.strip().upper()
    if cleaned not in {OrderSide.BUY.value, OrderSide.SELL.value}:
        raise TradingValidationError("Side must be BUY or SELL")
    return cleaned


def validate_order_type(order_type: str) -> str:
    if not order_type:
        raise TradingValidationError("Order type is required")
    cleaned = order_type.strip().upper()
    if cleaned not in {OrderType.MARKET.value, OrderType.LIMIT.value}:
        raise TradingValidationError("Order type must be MARKET or LIMIT")
    return cleaned


def validate_quantity(quantity: float) -> float:
    if quantity is None:
        raise TradingValidationError("Quantity is required")
    quantity = float(quantity)
    if quantity <= 0:
        raise TradingValidationError("Quantity must be greater than zero")
    return quantity


def validate_price(price: float | None) -> float | None:
    if price is None:
        return None
    price = float(price)
    if price <= 0:
        raise TradingValidationError("Price must be greater than zero")
    return price


def validate_order_inputs(symbol: str, side: str, order_type: str, quantity: float, price: float | None = None) -> tuple[str, str, str, float, float | None]:
    symbol = validate_symbol(symbol)
    side = validate_side(side)
    order_type = validate_order_type(order_type)
    quantity = validate_quantity(quantity)
    price = validate_price(price)

    if order_type == OrderType.LIMIT.value and price is None:
        raise TradingValidationError("Limit orders require a price")

    return symbol, side, order_type, quantity, price
