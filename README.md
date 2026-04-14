# Advanced Algorithmic Trading System

Production-style Python trading platform for Binance Futures Testnet (USDT-M) with a modular execution layer, OMS, portfolio tracking, strategy engine, backtesting, live streaming, journaling, and a Bloomberg-inspired Streamlit dashboard.

## Architecture

The project is organized around clean boundaries:

```text
trading-bot/
├── cli/         # Argument-driven command line entrypoint
├── api/         # Binance REST and WebSocket integration
├── core/        # Strategy, OMS, risk, portfolio, backtest, live engine
├── dashboard/   # Streamlit analytics layer
├── utils/       # Logging, validation, retry helpers
├── data/        # Trade journal and market snapshots
├── logs/        # Structured system logs
├── docs/        # Screenshots and supporting material
└── tests/       # Unit tests
```

## Core Capabilities

The system is built as a simplified real-world quant stack with separate execution and analytics paths.

### Execution Layer

- MARKET and LIMIT order placement for BUY and SELL directions
- CLI-based workflow with argument parsing
- Retry handling for transient API failures
- Structured logging and exception capture
- In-memory OMS lifecycle tracking with PENDING, FILLED, and FAILED states

### Portfolio and Risk

- Futures balance retrieval
- Open position tracking
- Active exposure calculation
- Live PnL calculation from current market price and open positions
- Risk checks based on risk per trade
- Maximum daily loss enforcement
- Position sizing logic derived from account equity and stop-loss distance

### Strategy Engine

- MA + RSI strategy
- Breakout strategy
- Dynamic strategy selection from CLI and dashboard
- Strategy consensus support for future expansion

### Backtesting

- Historical Binance Futures candles
- Equity curve generation
- Sharpe ratio
- Maximum drawdown
- Total trades

### Real-Time Trading

- Binance WebSocket price streaming
- Optional auto-trading based on strategy signals
- Rolling live frame construction for signal generation

### Dashboard

- Streamlit dashboard with a Bloomberg-terminal style visual language
- Trade history and order history views
- Live PnL and exposure summary
- Equity curve visualization
- Multi-symbol market monitoring

## Assignment Compliance Checklist

### Must-Do Requirements

- MARKET orders: supported via CLI
- LIMIT orders: supported via CLI
- BUY and SELL: supported
- CLI inputs: symbol, side, type, quantity, price
- Output: order summary and exchange API response fields when available
- Clean structure: CLI, API, core, utils, dashboard separation
- Logging: structured logs in `logs/bot.log`
- Error handling: exception-safe execution with clear failure messages

### Deliverables

- Source code: included in this repository
- README: this file
- requirements.txt: dependency list for runtime
- Logs of one MARKET and one LIMIT order attempt: recorded in `logs/bot.log`

### Execution Evidence

- MARKET attempt log entry: `Order failed ... type=MARKET ...`
- LIMIT attempt log entry: `Order failed ... type=LIMIT ...`
- Matching journal entries for both attempts: `data/trades.csv`

Note: this workspace currently returns Binance API error `-2015` (invalid API key, IP, or permissions), so orders are logged as failed attempts until valid testnet credentials are configured.

## Setup

```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

Create a `.env` file in the project root:

```env
API_KEY=your_testnet_key
API_SECRET=your_testnet_secret
BASE_URL=https://testnet.binancefuture.com
```

## Usage

### Place a Market Order

```bash
python cli/main.py --symbol BTCUSDT --side BUY --type MARKET --qty 0.001
```

### Place a Limit Order

```bash
python cli/main.py --symbol BTCUSDT --side SELL --type LIMIT --qty 0.001 --price 60000
```

### Run a Backtest

```bash
python cli/main.py --symbol BTCUSDT --type BACKTEST --strategy ma_rsi --interval 1m --limit 500
```

### Start Live Trading

```bash
python cli/main.py --symbol BTCUSDT --type LIVE --strategy breakout --qty 0.001
```

### Start Auto-Trading

```bash
python cli/main.py --symbol BTCUSDT --type AUTO --strategy ma_rsi --qty 0.001 --auto-trade
```

### Open the Dashboard

```bash
streamlit run dashboard/app.py
```

## Screenshots

These repository assets show the intended terminal and dashboard presentation:

- [MARKET order screenshot](docs/screenshots/market-order-screenshot.svg)
- [LIMIT order screenshot](docs/screenshots/limit-order-screenshot.svg)
- [Dashboard screenshot](docs/screenshots/dashboard-screenshot.svg)

## Sample Data

- Trade journal: [data/trades.csv](data/trades.csv)
- Log sample: [logs/bot.log](logs/bot.log)

## Design Decisions

- The CLI only orchestrates workflows; it does not own trading logic.
- OMS, portfolio tracking, risk checks, and strategies are reusable core services.
- Backtesting uses the same strategy layer as live trading to keep signal behavior consistent.
- Live PnL is computed against open futures positions instead of using static placeholders.
- The dashboard emphasizes dense market information and dark-terminal styling to match a Bloomberg-style workflow.

## Assumptions

- Binance Futures Testnet credentials are available in `.env`.
- Historical candle data is available from Binance public futures endpoints.
- Live auto-trading is enabled only when the user explicitly requests it.
- The dashboard reads from local journal files and live market data, not from a separate database.

## Validation

The repository includes focused unit tests for strategy evaluation, position sizing, live PnL math, and OMS state handling.

## Future Extensions

- Persistent order storage
- Database-backed portfolio snapshots
- Multi-account support
- More strategies and signal ensembles
- Alerting and notifications
