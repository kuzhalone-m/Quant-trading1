# BEEW QUANTUM — Module Reference Map
**Project:** Beew Quantum Autonomous Trading System  
**Blueprint Version:** v3.0 (February 2026)  
**Codebase Location:** `C:\Users\marke\OneDrive\Documents\Beew\Antigravity\Quant\`

---

## How the Blueprint Maps to Code

The Blueprint v3.0 defines a team of 5 named AI agents, plus 3 named subsystems.
Every file in this codebase corresponds directly to one of those blueprint entities.

```
Blueprint Agent/System     →    Python File(s)
─────────────────────────────────────────────────────
ORION  (Orchestrator)      →    main.py
STRATUS (Signal Engine)    →    strategy.py
QUASAR  (Sentiment/News)   →    [Phase 3 — not yet built]
ZEPHYR  (Trade Executor)   →    executor.py
NEBULA  (Strategy Evolver) →    [Phase 4 — not yet built]
KAVACH  (Risk Shield)      →    risk_engine.py
VIDYA   (Indicator Skills) →    strategy.py (indicator section)
MT5 Bridge                 →    mt5_client.py
Data/Logging Layer         →    trade_logger.py
Alert Layer                →    alert.py
Master Config              →    config.py
```

---

## File-by-File Reference

---

### `config.py` — Master Configuration
**Blueprint Reference:** Section 3 (Build Plan), Section 5 (KAVACH), Section 6 (Target Markets)

| What it stores | Value |
|---|---|
| MT5 login credentials | Login, Password, Server |
| Trading symbol & timeframes | XAUUSD, M15, H1 |
| Prop firm risk rules | Daily DD 4%, Overall DD 10% |
| Strategy parameters | EMA 9/21/50, RSI 14, ATR 14 |
| SL/TP multipliers | SL=ATR×1.5, TP=ATR×2.5 |
| Signal confidence threshold | 60% minimum |
| Telegram bot credentials | Token + Chat ID |

> **Rule:** This is the ONLY file you edit to change any parameter. Never hardcode values elsewhere.

---

### `main.py` — ORION (Central Orchestrator)
**Blueprint Reference:** Section 2.1 — *"Core brain. Connects all agents. Manages strategy selection and master ledger."*

**What it does:**
- Starts the entire system when you run `python main.py`
- Connects to MT5 and initialises all subsystems
- Runs a continuous loop — wakes up on every new M15 candle close
- Calls STRATUS (strategy.py) to generate a signal
- Calls KAVACH (risk_engine.py) to approve or block the trade
- Calls ZEPHYR (executor.py) to place the actual order
- Monitors open positions for break-even adjustment every cycle
- Logs everything and sends Telegram alerts
- Handles graceful shutdown on Ctrl+C

**Flow diagram:**
```
main.py starts
    └─► mt5_client.connect()
    └─► KavachRiskEngine(initial_balance)
    Loop every M15 candle:
        ├─► mt5_client.get_candles()          ← fetch market data
        ├─► kavach.is_trade_allowed()         ← KAVACH risk gate
        ├─► strategy.generate_signal()        ← STRATUS signal
        ├─► kavach.calculate_lot_size()       ← KAVACH position sizing
        ├─► executor.place_order()            ← ZEPHYR execution
        ├─► trade_logger.log_trade_open()     ← data layer
        └─► alert.send_telegram()             ← notifications
```

---

### `strategy.py` — STRATUS (Signal Engine) + VIDYA Skills
**Blueprint Reference:**
- Section 2.1 — *"Generates primary signals. Analyzes multi-timeframe trends, RSI/MACD/EMA."*
- Section 8 — VIDYA Skills: Trend Detection (EMA), Volatility Regime (ATR), Multi-Timeframe Confluence

**What it does:**
- Calculates technical indicators from raw candle data using pure `pandas`/`numpy`
- Contains three private indicator functions (VIDYA skills):
  - `_ema(series, period)` — Exponential Moving Average
  - `_rsi(series, period)` — Relative Strength Index (Wilder's method)
  - `_atr(high, low, close, period)` — Average True Range
- `calculate_indicators(df)` — adds all indicators to a candle DataFrame
- `generate_signal(df, htf_df)` — analyses the last completed candle and scores confluence:

| Condition | Weight |
|---|---|
| EMA 9 crosses EMA 21 | 0.25 |
| RSI within acceptable range | 0.25 |
| H1 trend confirms direction | 0.25 |
| ATR above average (volatility present) | 0.25 |

**Returns:** A signal dict with direction, confidence (0–100%), entry, SL, TP, ATR value, and reasons.  
**Trade fires** only if confidence ≥ 60% (configurable in `config.py`).

---

### `risk_engine.py` — KAVACH (Risk Shield)
**Blueprint Reference:** Section 5 — *"Hard Stop Loss, Daily Drawdown Limit, Overall Drawdown Limit, Correlation Protection"*

**What it does:**
- Implements all prop firm risk rules as hard-coded gates
- Every trade MUST pass ALL checks or it is blocked completely
- Based directly on your handwritten notebook formulas

**The five checks:**

| Method | What it checks | Limit |
|---|---|---|
| `check_daily_drawdown()` | Today's loss vs daily start equity | 4% (Pipstone 2-step) |
| `check_overall_drawdown()` | Total loss from initial balance | 10% |
| `check_concurrent_positions()` | How many trades are open | Max 3 |
| `calculate_lot_size()` | Computes position size from risk % | 0.5% per trade |
| `is_trade_allowed()` | Master gate — runs all 3 checks | All must pass |

**Your handwritten lot formula (implemented exactly):**
```
Risk$     = Equity × 0.005         → e.g. $50,000 × 0.005 = $250
Loss/lot  = SL_pips × pip_value    → e.g. 15 pips × $10   = $150
Lots      = Risk$ / Loss_per_lot   → e.g. $250 / $150      = 1.67 lots
```

---

### `executor.py` — ZEPHYR (Trade Manager)
**Blueprint Reference:** Section 2.1 — *"Executes on MT5/cTrader. Monitors equity/drawdown. Handles trailing stops."*

**What it does:**
- `place_order()` — sends a market order to MT5 with the correct fill type for the broker
- `close_position()` — closes a specific trade by ticket number
- `close_all_positions()` — emergency close: shuts every open position (panic button)
- `move_sl_to_breakeven()` — moves stop-loss to entry price once trade is 15 pips in profit
- Auto-detects broker fill type (FOK/IOC/RETURN) — handles different broker requirements
- Uses magic number `20260316` to tag all BEEW bot orders in MT5

---

### `mt5_client.py` — MT5 Data & Connection Layer
**Blueprint Reference:** Section 3 — *"API Connectivity: Establish secure links to MT5 using MetaApi or similar bridges"*  
*(Note: We use the direct MT5 Python library here for demo; MetaApi cloud bridge comes in Phase 5 for multi-account)*

**What it does:**
- `connect()` — initialises MetaTrader 5 and logs in with credentials from config
- `disconnect()` — cleanly shuts down the MT5 connection
- `get_account_info()` — returns balance, equity, margin snapshot
- `get_candles(symbol, timeframe, count)` — fetches OHLCV candle data as a DataFrame
- `get_symbol_info(symbol)` — returns point size, pip value, lot limits for sizing
- `get_open_positions()` — lists all currently open trades
- `get_todays_history()` — fetches closed deals today (for drawdown tracking)

---

### `trade_logger.py` — Data Layer (Trade Ledger)
**Blueprint Reference:** Section 7 — *"MongoDB stores research versus actual price outcomes to train the meta-learner"*  
*(Note: We use CSV for Phase 1 demo. MongoDB integration comes in Phase 2.)*

**What it does:**
- `log_trade_open()` — writes a new trade row to `logs/trades.csv` when a trade opens
- `log_trade_close()` — updates that row with close price, P&L, WIN/LOSS when trade closes
- Creates the `logs/` directory and CSV file automatically on first run

**CSV columns stored:**
`timestamp | symbol | direction | lots | entry_price | sl_price | tp_price | sl_pips | confidence | reasons | order_id | closed_at | close_price | pnl | result`

> This file becomes your training data for NEBULA's genetic algorithm in Phase 4.

---

### `alert.py` — Telegram Notification Layer
**Blueprint Reference:** Section 7 — *"Telegram Input: COO posts research to a dedicated channel. Agents extract sentiment."*  
*(Currently outbound only — sends alerts. Inbound Telegram parsing = QUASAR, Phase 3.)*

**What it does:**
- `send_telegram(message)` — posts a message to your Telegram bot
- Silently does nothing if `TELEGRAM_BOT_TOKEN` is not set in config (won't crash the bot)
- Sends alerts for: trade open, trade blocked by KAVACH, bot start/stop, errors

---

### `test_connection.py` — Live Connection Test
**Not in Blueprint** — utility script for setup verification.

**What it does:**
- Connects to MT5 and prints account info
- Fetches candles and confirms data is live
- Runs the strategy and shows the current signal
- Calculates lot size for the current setup
- Runs all KAVACH checks
- **Does NOT place any orders**
- Run this before `main.py` every time to confirm everything is working

---

### `test_offline.py` — Offline Logic Test
**Not in Blueprint** — developer utility.

**What it does:**
- Tests all modules using synthetic (fake) price data
- No MT5 connection required — works without market hours
- Confirms indicators, signals, lot sizing, and all KAVACH checks are mathematically correct
- Run this after any code change to catch regressions

---

## What Is Still To Be Built

| Blueprint Component | Codename | Status | Phase |
|---|---|---|---|
| Sentiment & News Parser | QUASAR | Not started | Phase 3 |
| Telegram input → sentiment | QUASAR | Not started | Phase 3 |
| Genetic Algorithm optimizer | NEBULA | Not started | Phase 4 |
| Backtesting engine | NEBULA | Not started | Phase 4 |
| Multi-account fan-out | ZEPHYR v2 | Not started | Phase 5 |
| MetaApi cloud bridge | Infrastructure | Not started | Phase 5 |
| MongoDB integration | Data Layer | Not started | Phase 2 |
| Performance dashboard | Monitoring | Not started | Phase 4 |

---

## Current System Status

```
Phase 0 (Infrastructure)   ░░░░░░░░░  Pending — MT5 demo account credentials needed
Phase 1 (ORION Core)       ████████░  Complete — awaiting first demo run
Phase 2 (ZEPHYR Execution) ████████░  Complete — awaiting demo verification
Phase 3 (STRATUS Signals)  ████████░  Complete — tested offline, all checks passed
Phase 4 (Paper Trading)    ░░░░░░░░░  Not started
Phase 5 (Live Deployment)  ░░░░░░░░░  Not started
```

---

*Last updated: March 16, 2026*  
*All tests: PASSED (see test_offline.py output)*
