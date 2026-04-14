from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import streamlit as st

if __package__ is None or __package__ == "":
	sys.path.append(str(Path(__file__).resolve().parents[1]))

from api.binance_client import BinanceClient
from core.backtest import run_backtest
from core.portfolio import PortfolioTracker
from core.strategies import StrategyEngine


st.set_page_config(page_title="Trading Terminal", layout="wide", initial_sidebar_state="expanded")


def inject_styles() -> None:
	st.markdown(
		"""
		<style>
		:root {
			--bg: #050607;
			--panel: #0b1110;
			--panel-2: #101817;
			--accent: #86efac;
			--accent-2: #eab308;
			--muted: #7c8a86;
			--danger: #fb7185;
		}
		.stApp {
			background:
				radial-gradient(circle at top left, rgba(134, 239, 172, 0.08), transparent 30%),
				linear-gradient(180deg, #020202 0%, #050607 100%);
			color: #eef7ef;
			font-family: "Segoe UI", "Inter", sans-serif;
		}
		section[data-testid="stSidebar"] {
			background: linear-gradient(180deg, #091110 0%, #060807 100%);
			border-right: 1px solid rgba(134, 239, 172, 0.18);
		}
		.terminal-panel {
			background: linear-gradient(180deg, rgba(16, 24, 23, 0.98), rgba(5, 6, 7, 0.98));
			border: 1px solid rgba(134, 239, 172, 0.18);
			border-radius: 16px;
			padding: 1rem 1.25rem;
			box-shadow: 0 0 24px rgba(0, 0, 0, 0.35);
		}
		.terminal-title {
			color: var(--accent);
			font-family: "Consolas", "SFMono-Regular", monospace;
			letter-spacing: 0.2em;
			text-transform: uppercase;
			margin-bottom: 0.25rem;
		}
		.ticker {
			overflow: hidden;
			white-space: nowrap;
			border-top: 1px solid rgba(134, 239, 172, 0.15);
			border-bottom: 1px solid rgba(134, 239, 172, 0.15);
			padding: 0.5rem 0;
			color: var(--accent-2);
			font-family: "Consolas", monospace;
			letter-spacing: 0.08em;
		}
		.ticker span {
			display: inline-block;
			padding-left: 100%;
			animation: ticker-scroll 28s linear infinite;
		}
		@keyframes ticker-scroll {
			0% { transform: translateX(0); }
			100% { transform: translateX(-100%); }
		}
		[data-testid="metric-container"] {
			background: rgba(7, 13, 12, 0.92);
			border: 1px solid rgba(134, 239, 172, 0.14);
			border-radius: 14px;
			padding: 0.75rem;
		}
		[data-testid="stDataFrame"] {
			border: 1px solid rgba(134, 239, 172, 0.12);
			border-radius: 12px;
			overflow: hidden;
		}
		</style>
		""",
		unsafe_allow_html=True,
	)


def load_trade_history() -> pd.DataFrame:
	file_path = Path("data/trades.csv")
	if not file_path.exists() or file_path.stat().st_size == 0:
		return pd.DataFrame(columns=["timestamp", "symbol", "side", "order_type", "quantity", "price", "status", "pnl", "strategy"])

	frame = pd.read_csv(file_path)
	if "timestamp" in frame.columns:
		frame["timestamp"] = pd.to_datetime(frame["timestamp"], errors="coerce")
	if "pnl" not in frame.columns:
		frame["pnl"] = 0.0
	return frame


def build_equity_curve(trades: pd.DataFrame) -> pd.DataFrame:
	if trades.empty:
		return pd.DataFrame({"equity": [1000.0]})

	pnl_series = pd.to_numeric(trades.get("pnl", pd.Series([0.0] * len(trades))), errors="coerce").fillna(0.0)
	equity = 1000.0 + pnl_series.cumsum()
	return pd.DataFrame({"equity": equity, "timestamp": trades.get("timestamp", pd.Series(range(len(trades))))})


def current_market_snapshot(client: BinanceClient, symbols: list[str], portfolio: PortfolioTracker) -> pd.DataFrame:
	rows = []
	for symbol in symbols:
		try:
			price = client.get_latest_price(symbol)
		except Exception:
			price = float("nan")

		live_pnl = portfolio.live_pnl(symbol, price) if price == price else 0.0
		rows.append(
			{
				"symbol": symbol,
				"price": price,
				"live_pnl": live_pnl,
				"status": "ACTIVE" if abs(live_pnl) > 0 else "WATCH",
			}
		)
	return pd.DataFrame(rows)


def main() -> None:
	inject_styles()
	st.markdown('<div class="terminal-panel"><div class="terminal-title">Binance Futures Terminal</div><div class="ticker"><span>BTCUSDT  ETHUSDT  SOLUSDT  XRPUSDT  ADAUSDT  AVAXUSDT  •  LIVE PNL  RISK  OMS  BACKTEST  •  TESTNET OPERATIONS</span></div></div>', unsafe_allow_html=True)

	client = BinanceClient()
	portfolio = PortfolioTracker(client)
	strategy_engine = StrategyEngine()
	if getattr(client, "init_error", None):
		st.warning(f"Binance connectivity unavailable: {client.init_error}")

	with st.sidebar:
		st.header("Control Desk")
		symbol_input = st.text_input("Symbols", value="BTCUSDT,ETHUSDT")
		strategy_name = st.selectbox("Strategy", strategy_engine.available_strategies())
		interval = st.selectbox("Interval", ["1m", "5m", "15m", "1h", "4h", "1d"], index=0)
		limit = st.slider("History Bars", min_value=100, max_value=1000, value=500, step=50)
		st.caption("Dashboard reads from the journal and Binance testnet prices.")

	symbols = [symbol.strip().upper() for symbol in symbol_input.split(",") if symbol.strip()]
	trades = load_trade_history()
	equity_curve = build_equity_curve(trades)

	top_left, top_mid, top_right, top_four = st.columns(4)
	try:
		wallet_balance = portfolio.fetch_balance()
	except Exception:
		wallet_balance = 0.0

	try:
		open_positions = len(portfolio.active_positions())
	except Exception:
		open_positions = 0

	try:
		exposure = portfolio.active_exposure()
	except Exception:
		exposure = 0.0

	with top_left:
		st.metric("Wallet Balance", f"{wallet_balance:,.2f} USDT")
	with top_mid:
		st.metric("Open Positions", open_positions)
	with top_right:
		st.metric("Exposure", f"{exposure:,.2f}")
	with top_four:
		st.metric("Strategy", strategy_name.upper())

	snapshot = current_market_snapshot(client, symbols, portfolio)

	main_left, main_right = st.columns([1.25, 1])
	with main_left:
		st.subheader("Live Market Monitor")
		st.dataframe(snapshot, use_container_width=True, hide_index=True)
		st.subheader("Trade History")
		st.dataframe(trades.sort_values(by="timestamp", ascending=False) if "timestamp" in trades.columns and not trades.empty else trades, use_container_width=True, hide_index=True)

	with main_right:
		st.subheader("Live PnL")
		if not snapshot.empty:
			pnl_series = snapshot["live_pnl"].fillna(0.0)
			st.metric("Unrealized PnL", f"{pnl_series.sum():,.2f} USDT")
		st.subheader("Equity Curve")
		if not equity_curve.empty:
			st.line_chart(equity_curve.set_index("timestamp")["equity"] if "timestamp" in equity_curve.columns else equity_curve["equity"])

		st.subheader("Backtest Snapshot")
		try:
			backtest_result = run_backtest(symbols[0], strategy_name=strategy_name, interval=interval, limit=limit)
			metrics = backtest_result["metrics"]
			metric_table = pd.DataFrame(
				{
					"metric": ["final_balance", "sharpe_ratio", "max_drawdown", "total_return", "total_trades"],
					"value": [backtest_result["final_balance"], metrics["sharpe_ratio"], metrics["max_drawdown"], metrics["total_return"], int(metrics["total_trades"])],
				}
			)
			st.dataframe(metric_table, use_container_width=True, hide_index=True)
		except Exception as exc:
			st.info(f"Backtest unavailable: {exc}")


if __name__ == "__main__":
	main()