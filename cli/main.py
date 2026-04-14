from __future__ import annotations

import argparse
import sys
from collections import deque
from pathlib import Path

import pandas as pd
from rich import box
from rich.console import Console
from rich.table import Table

if __package__ is None or __package__ == "":
    sys.path.append(str(Path(__file__).resolve().parents[1]))

from api.binance_client import BinanceClient
from api.websocket_client import PriceStreamer
from core.backtest import run_backtest
from core.engine import LiveTradingEngine, TradingEngine
from core.market_data import build_live_frame
from core.strategies import StrategyEngine
from utils.logger import get_logger, setup_logger
from utils.validator import validate_order_inputs, TradingValidationError


console = Console()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Binance Futures Testnet trading bot")
    parser.add_argument("--symbol", required=True, help="Trading symbol, e.g. BTCUSDT")
    parser.add_argument("--side", help="BUY or SELL for order placement")
    parser.add_argument("--type", required=True, choices=["MARKET", "LIMIT", "BACKTEST", "LIVE", "AUTO"], help="Execution mode")
    parser.add_argument("--qty", type=float, help="Order quantity")
    parser.add_argument("--price", type=float, help="Limit price")
    parser.add_argument("--strategy", default="ma_rsi", choices=StrategyEngine().available_strategies(), help="Strategy to use")
    parser.add_argument("--interval", default="1m", help="Historical interval for backtests and live seeding")
    parser.add_argument("--limit", type=int, default=500, help="Historical bar count for backtests and live seeding")
    parser.add_argument("--risk-percent", type=float, default=0.01, help="Risk per trade as a fraction of balance")
    parser.add_argument("--max-daily-loss", type=float, default=0.05, help="Maximum daily loss as a fraction of starting balance")
    parser.add_argument("--auto-trade", action="store_true", help="Enable live auto-trading in LIVE mode")
    return parser


def print_order_summary(order: dict[str, object]) -> None:
    table = Table(title="Order Summary", box=box.SIMPLE_HEAVY)
    table.add_column("Field", style="cyan", no_wrap=True)
    table.add_column("Value", style="white")
    for key in ["id", "exchange_order_id", "symbol", "side", "order_type", "quantity", "price", "status", "strategy"]:
        table.add_row(key, str(order.get(key, "")))
    console.print(table)


def print_api_response(order: dict[str, object]) -> None:
    response = order.get("raw_response") or {}
    if not isinstance(response, dict) or not response:
        return

    table = Table(title="API Response", box=box.SIMPLE_HEAVY)
    table.add_column("Field", style="magenta", no_wrap=True)
    table.add_column("Value", style="white")

    preferred_keys = [
        "orderId",
        "clientOrderId",
        "symbol",
        "side",
        "type",
        "status",
        "price",
        "origQty",
        "executedQty",
        "timeInForce",
        "updateTime",
    ]
    rendered = set()

    for key in preferred_keys:
        if key in response:
            table.add_row(key, str(response.get(key, "")))
            rendered.add(key)

    for key, value in response.items():
        if key not in rendered:
            table.add_row(str(key), str(value))

    console.print(table)


def run_market_or_limit_trade(args, engine: TradingEngine) -> None:
    symbol, side, order_type, quantity, price = validate_order_inputs(args.symbol, args.side, args.type, args.qty, args.price)
    order = engine.execute_order(
        symbol=symbol,
        side=side,
        order_type=order_type,
        quantity=quantity,
        price=price,
        strategy=args.strategy,
    )
    print_order_summary(order)
    print_api_response(order)
    if order.get("status") == "FAILED":
        console.print(f"[red]Order failed:[/red] {order.get('error', 'unknown error')}")
    else:
        console.print(f"[green]Order state:[/green] {order.get('status')}")


def run_backtest_mode(args, engine: TradingEngine) -> None:
    result = engine.backtest(
        symbol=args.symbol,
        strategy_name=args.strategy,
        interval=args.interval,
        limit=args.limit,
    )

    metrics = result["metrics"]
    table = Table(title=f"Backtest - {args.symbol}", box=box.SIMPLE_HEAVY)
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="white")
    table.add_row("Initial Balance", f"{result['initial_balance']:.2f}")
    table.add_row("Final Balance", f"{result['final_balance']:.2f}")
    table.add_row("Sharpe Ratio", str(metrics["sharpe_ratio"]))
    table.add_row("Max Drawdown", str(metrics["max_drawdown"]))
    table.add_row("Total Return", str(metrics["total_return"]))
    table.add_row("Total Trades", str(int(metrics["total_trades"])))
    console.print(table)


def run_live_mode(args, engine: TradingEngine) -> None:
    live_engine = LiveTradingEngine(
        client=engine.client,
        symbol=args.symbol,
        strategy_name=args.strategy,
        auto_trade=args.auto_trade or args.type == "AUTO",
        quantity=args.qty,
        interval=args.interval,
        lookback=max(args.limit, 100),
    )

    try:
        console.print(f"[bold green]Starting live stream for {args.symbol} using {args.strategy}[/bold green]")
        live_engine.run()
        input("Press Enter to stop live trading...\n")
    finally:
        live_engine.stop()


def main() -> None:
    setup_logger()
    logger = get_logger(__name__)
    parser = build_parser()
    args = parser.parse_args()

    client = BinanceClient()
    engine = TradingEngine(client)

    try:
        if args.type in {"MARKET", "LIMIT"}:
            if not args.side or args.qty is None:
                raise TradingValidationError("Order placement requires --side and --qty")
            run_market_or_limit_trade(args, engine)
        elif args.type == "BACKTEST":
            run_backtest_mode(args, engine)
        elif args.type in {"LIVE", "AUTO"}:
            run_live_mode(args, engine)
        else:
            raise TradingValidationError(f"Unsupported type: {args.type}")
    except Exception as exc:
        logger.exception("Trading command failed")
        console.print(f"[red]Execution failed:[/red] {exc}")
        raise SystemExit(1) from exc


if __name__ == "__main__":
    main()