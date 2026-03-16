"""
BEEW QUANTUM — ORION Main Bot Loop
The central orchestrator that ties all modules together.

Run this script to start trading on demo:
  > python main.py

The bot:
  1. Connects to MT5
  2. Every 15 minutes (end of each M15 candle): runs strategy
  3. If signal + risk check pass → places trade
  4. Continuously monitors open positions for break-even
  5. Logs everything to logs/trades.csv
  6. Sends Telegram alerts (if configured)
"""

import time
import logging
import os
import sys
from datetime import datetime, timezone

# ── Setup logging ─────────────────────────────────────────────────────────────
os.makedirs("logs", exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s — %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("logs/trading_bot.log", encoding="utf-8"),
    ]
)
logger = logging.getLogger("beew.orion")

# ── Import modules ────────────────────────────────────────────────────────────
from config import SYMBOL, TIMEFRAME, HTF
import mt5_client as mt5c
from risk_engine import KavachRiskEngine
from strategy import generate_signal
from executor import place_order, move_sl_to_breakeven
from trade_logger import log_trade_open
from alert import send_telegram


# ── Helper: wait for next candle close ───────────────────────────────────────
TIMEFRAME_SECONDS = {
    "M1":  60,   "M5":  300,  "M15": 900,
    "M30": 1800, "H1":  3600, "H4":  14400, "D1": 86400
}

def seconds_to_next_candle(timeframe: str) -> int:
    """How many seconds until the next candle opens."""
    period = TIMEFRAME_SECONDS.get(timeframe, 900)
    now    = int(datetime.now(timezone.utc).timestamp())
    return period - (now % period)


# ── Main Bot ──────────────────────────────────────────────────────────────────
def run_bot():
    logger.info("=" * 60)
    logger.info("  BEEW QUANTUM — ORION starting up")
    logger.info(f"  Symbol: {SYMBOL} | TF: {TIMEFRAME} | HTF: {HTF}")
    logger.info("=" * 60)

    # 1. Connect to MT5
    if not mt5c.connect():
        logger.critical("Cannot connect to MT5. Make sure MT5 is running. Exiting.")
        return

    # 2. Initialise risk engine
    account = mt5c.get_account_info()
    kavach  = KavachRiskEngine(initial_balance=account.get("balance", 50000))
    logger.info(f"Account loaded: Balance=${account.get('balance', 0):.2f} | Equity=${account.get('equity', 0):.2f}")
    send_telegram(f"🤖 BEEW QUANTUM started\n📊 {SYMBOL} | {TIMEFRAME}\n💰 Balance: ${account.get('balance',0):.2f}")

    # 3. Main loop
    last_candle_time = None

    try:
        while True:
            now_utc = datetime.now(timezone.utc)

            # ── Fetch latest candles ──────────────────────────────────────────
            df     = mt5c.get_candles(SYMBOL, TIMEFRAME, count=150)
            htf_df = mt5c.get_candles(SYMBOL, HTF,       count=100)

            if df.empty:
                logger.warning("No candle data received. Retrying in 60s...")
                time.sleep(60)
                continue

            # ── Check if we have a NEW candle ─────────────────────────────────
            latest_time = df.iloc[-1]["time"]
            if latest_time == last_candle_time:
                # Same candle still forming — sleep until next close
                wait = seconds_to_next_candle(TIMEFRAME)
                logger.debug(f"Waiting {wait}s for next {TIMEFRAME} candle...")
                time.sleep(min(wait, 30))
                continue

            last_candle_time = latest_time
            logger.info(f"\n{'─'*50}")
            logger.info(f"New {TIMEFRAME} candle: {latest_time}")

            # ── Get account snapshot ──────────────────────────────────────────
            account    = mt5c.get_account_info()
            equity     = account.get("equity", 0)
            open_pos   = mt5c.get_open_positions(SYMBOL)
            open_count = len(mt5c.get_open_positions())  # all symbols

            # ── Run KAVACH risk checks ─────────────────────────────────────────
            allowed, reason = kavach.is_trade_allowed(equity, open_count)
            if not allowed:
                logger.warning(f"🔴 TRADE BLOCKED: {reason}")
                send_telegram(f"🔴 KAVACH blocked trading:\n{reason}")
                wait = seconds_to_next_candle(TIMEFRAME)
                time.sleep(wait)
                continue

            # ── Only enter if no position already open for this symbol ────────
            if len(open_pos) > 0:
                logger.info(f"Position already open for {SYMBOL} — skipping entry signal")
                # Still monitor for break-even
                for pos in open_pos:
                    move_sl_to_breakeven(
                        ticket=pos["ticket"],
                        entry_price=pos["price_open"],
                        min_profit_pips=15.0
                    )
                wait = seconds_to_next_candle(TIMEFRAME)
                time.sleep(wait)
                continue

            # ── Generate trading signal ───────────────────────────────────────
            signal = generate_signal(df, htf_df)
            direction = signal["direction"]

            logger.info(
                f"Signal: {direction} | Confidence: {signal['confidence']:.0%} | "
                f"Reasons: {', '.join(signal['reasons'])}"
            )

            if direction == "NONE":
                wait = seconds_to_next_candle(TIMEFRAME)
                time.sleep(wait)
                continue

            # ── Calculate lot size ────────────────────────────────────────────
            sym_info  = mt5c.get_symbol_info(SYMBOL)
            pip_value = sym_info.get("trade_tick_value", 10.0)  # $10 per pip for XAUUSD usually
            sl_pips   = signal["sl_pips"] / sym_info.get("point", 0.01)

            lots = kavach.calculate_lot_size(
                equity      = equity,
                sl_pips     = sl_pips,
                pip_value   = pip_value,
                volume_min  = sym_info.get("volume_min",  0.01),
                volume_step = sym_info.get("volume_step", 0.01),
                volume_max  = sym_info.get("volume_max",  100.0),
            )

            # ── Place order ────────────────────────────────────────────────────
            result = place_order(
                symbol    = SYMBOL,
                direction = direction,
                lots      = lots,
                sl_price  = signal["sl_price"],
                tp_price  = signal["tp_price"],
                comment   = f"BEEW|{signal['confidence']:.0%}"
            )

            if result["success"]:
                log_trade_open(
                    symbol      = SYMBOL,
                    direction   = direction,
                    lots        = lots,
                    entry_price = result["price"],
                    sl_price    = signal["sl_price"],
                    tp_price    = signal["tp_price"],
                    sl_pips     = sl_pips,
                    confidence  = signal["confidence"],
                    reasons     = signal["reasons"],
                    order_id    = result["order_id"],
                )
                send_telegram(
                    f"✅ TRADE OPEN\n"
                    f"{'🟢 BUY' if direction=='BUY' else '🔴 SELL'} {SYMBOL}\n"
                    f"💰 Lots: {lots} | Entry: {result['price']:.5f}\n"
                    f"🛡 SL: {signal['sl_price']:.5f}\n"
                    f"🎯 TP: {signal['tp_price']:.5f}\n"
                    f"📊 Confidence: {signal['confidence']:.0%}\n"
                    f"🔍 {' | '.join(signal['reasons'])}"
                )
            else:
                logger.error(f"Order failed: {result.get('error')}")
                send_telegram(f"⚠️ Order FAILED: {result.get('error')}")

            # ── Sleep until next candle ────────────────────────────────────────
            wait = seconds_to_next_candle(TIMEFRAME)
            logger.info(f"Sleeping {wait}s until next {TIMEFRAME} candle...")
            time.sleep(wait)

    except KeyboardInterrupt:
        logger.info("\n🛑 Bot stopped by user (Ctrl+C)")
        send_telegram("🛑 BEEW QUANTUM stopped manually.")
    except Exception as e:
        logger.exception(f"💥 Unhandled exception: {e}")
        send_telegram(f"💥 BEEW QUANTUM CRASHED: {e}")
    finally:
        mt5c.disconnect()
        logger.info("MT5 disconnected. Goodbye.")


if __name__ == "__main__":
    run_bot()
