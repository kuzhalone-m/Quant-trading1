"""
BEEW QUANTUM — Configuration
All trading parameters in one place. Edit THIS file only to change behaviour.
"""

# ── MT5 Connection ─────────────────────────────────────────────────────────────
MT5_LOGIN    = 0            # ← paste your demo account number here
MT5_PASSWORD = ""           # ← paste your demo password here
MT5_SERVER   = ""           # ← e.g. "Pepperstone-Demo" or "ICMarkets-Demo01"

# ── Trading Symbol & Timeframe ─────────────────────────────────────────────────
SYMBOL     = "XAUUSD"       # Gold — our primary instrument
TIMEFRAME  = "M15"          # 15-minute candles for signal generation
HTF        = "H1"           # Higher timeframe for trend filter

# ── Prop Firm Risk Rules (Pipstone 2-Step as default) ─────────────────────────
PROP_FIRM              = "Pipstone_2Step"
ACCOUNT_BALANCE        = 50_000         # Starting evaluation balance
RISK_PER_TRADE_PCT     = 0.005          # 0.5% risk per trade (conservative)
MAX_DAILY_DD_PCT       = 0.04           # 4% daily drawdown hard stop
MAX_OVERALL_DD_PCT     = 0.10           # 10% overall drawdown hard stop
MAX_CONCURRENT_TRADES  = 3              # Max open trades at one time (firm allows 4, we use 3)
MIN_TRADE_HOLD_SECONDS = 120            # No HFT — minimum hold 2 minutes
NEWS_PAUSE_MINUTES     = 5              # Pause 5 min before/after high-impact news

# ── Strategy Parameters ────────────────────────────────────────────────────────
# EMA Trend Filter
EMA_FAST   = 9
EMA_SLOW   = 21
EMA_TREND  = 50           # HTF trend direction

# RSI Momentum Confirmation
RSI_PERIOD          = 14
RSI_OVERBOUGHT      = 65  # Slightly conservative (not 70) to catch early
RSI_OVERSOLD        = 35

# ATR for dynamic SL/TP
ATR_PERIOD          = 14
ATR_SL_MULTIPLIER   = 1.5   # SL = 1.5 × ATR
ATR_TP_MULTIPLIER   = 2.5   # TP = 2.5 × ATR  → gives 1:1.67 R:R

# London Breakout (UTC times)
LONDON_OPEN_HOUR_UTC = 8    # 8:00 AM UTC = 1:30 PM IST
LONDON_OPEN_MINUTE   = 0
LONDON_BREAKOUT_LOOKBACK_CANDLES = 4  # Range of last 4 candles before open

# Signal Confidence Threshold (0.0 to 1.0)
MIN_CONFIDENCE = 0.60       # Must have at least 60% signal confluence

# ── Logging ────────────────────────────────────────────────────────────────────
LOG_FILE    = "logs/trading_bot.log"
TRADE_LOG   = "logs/trades.csv"

# ── Telegram Alerts (optional — fill in to get trade alerts) ──────────────────
TELEGRAM_BOT_TOKEN = ""     # From @BotFather
TELEGRAM_CHAT_ID   = ""     # Your personal chat ID
