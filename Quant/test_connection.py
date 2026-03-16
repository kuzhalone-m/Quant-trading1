"""
BEEW QUANTUM — Quick Test Script
Run this BEFORE main.py to verify everything is working correctly.

Usage:
  python test_connection.py

It will:
  1. Connect to MT5 and show account info
  2. Fetch candles and calculate indicators
  3. Run the strategy and show the current signal
  4. Show lot size calculation
  5. Run all KAVACH risk checks
  → Does NOT place any real orders
"""

import sys
import logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("test")

print("\n" + "="*60)
print("  BEEW QUANTUM — Connection & Strategy Test")
print("="*60 + "\n")

# ── Step 1: MT5 Connection ─────────────────────────────────────────────────
print("📡 Step 1: Connecting to MT5...")
import mt5_client as mt5c

if not mt5c.connect():
    print("❌ FAILED: Cannot connect to MT5.")
    print("   → Make sure MetaTrader 5 is open on your PC.")
    print("   → Enable 'Algo Trading' in MT5: Tools → Options → Expert Advisors → Allow Algo Trading")
    sys.exit(1)

account = mt5c.get_account_info()
print(f"✅ Connected!")
print(f"   Login:    {account.get('login')}")
print(f"   Balance:  ${account.get('balance', 0):,.2f}")
print(f"   Equity:   ${account.get('equity', 0):,.2f}")
print(f"   Server:   {account.get('server')}")
print(f"   Currency: {account.get('currency')}")


# ── Step 2: Fetch Candles ──────────────────────────────────────────────────
from config import SYMBOL, TIMEFRAME, HTF
print(f"\n📊 Step 2: Fetching candles for {SYMBOL}...")

df     = mt5c.get_candles(SYMBOL, TIMEFRAME, count=150)
htf_df = mt5c.get_candles(SYMBOL, HTF, count=100)

if df.empty:
    print(f"❌ FAILED: No candle data for {SYMBOL}.")
    print("   → Is the symbol available on your broker?")
    print("   → Check your internet connection.")
    sys.exit(1)

print(f"✅ Got {len(df)} candles on {TIMEFRAME} | Latest: {df.iloc[-1]['time']}")
print(f"✅ Got {len(htf_df)} candles on {HTF}")
print(f"   Latest close: {df.iloc[-1]['close']:.5f}")


# ── Step 3: Strategy Signal ────────────────────────────────────────────────
print(f"\n🧠 Step 3: Running strategy signal engine...")
from strategy import generate_signal
signal = generate_signal(df, htf_df)

print(f"   Direction:  {signal['direction']}")
print(f"   Confidence: {signal['confidence']:.0%}")
print(f"   Entry:      {signal['entry_price']:.5f}")
print(f"   SL:         {signal['sl_price']:.5f}")
print(f"   TP:         {signal['tp_price']:.5f}")
print(f"   ATR:        {signal['atr']:.5f}")
print(f"   Reasons:    {', '.join(signal['reasons']) if signal['reasons'] else 'None'}")


# ── Step 4: Lot Size Calculation ───────────────────────────────────────────
print(f"\n💰 Step 4: Lot size calculation...")
from risk_engine import KavachRiskEngine
kavach = KavachRiskEngine(initial_balance=account.get("balance", 50000))

sym_info  = mt5c.get_symbol_info(SYMBOL)
pip_value = sym_info.get("trade_tick_value", 10.0)
point     = sym_info.get("point", 0.01)
sl_pips   = signal["sl_pips"] / point if signal["sl_pips"] > 0 else 15.0

print(f"   Symbol point:     {point}")
print(f"   Pip value / lot:  ${pip_value:.2f}")
print(f"   SL in pips:       {sl_pips:.1f}")

lots = kavach.calculate_lot_size(
    equity      = account.get("equity", 50000),
    sl_pips     = sl_pips,
    pip_value   = pip_value,
    volume_min  = sym_info.get("volume_min", 0.01),
    volume_step = sym_info.get("volume_step", 0.01),
    volume_max  = sym_info.get("volume_max", 100.0),
)
print(f"   ✅ Calculated lots: {lots}")


# ── Step 5: KAVACH Risk Check ──────────────────────────────────────────────
print(f"\n🛡 Step 5: KAVACH risk checks...")
equity     = account.get("equity", 0)
open_pos   = mt5c.get_open_positions()
open_count = len(open_pos)

allowed, reason = kavach.is_trade_allowed(equity, open_count)
if allowed:
    print(f"   ✅ ALL CHECKS PASSED — trade would be allowed")
else:
    print(f"   ⛔ BLOCKED: {reason}")

print(f"   Open positions:   {open_count}")


# ── Summary ────────────────────────────────────────────────────────────────
print("\n" + "="*60)
if allowed and signal["direction"] != "NONE":
    print(f"  🟢 READY TO TRADE — run: python main.py")
elif not allowed:
    print(f"  🔴 RISK LIMIT ACTIVE — check account state before running")
else:
    print(f"  🟡 NO SIGNAL RIGHT NOW — strategy will watch and wait")
print("="*60 + "\n")

mt5c.disconnect()
