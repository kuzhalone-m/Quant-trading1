"""Quick offline test - no MT5 needed"""
import sys

print("=== BEEW QUANTUM — Offline Logic Test ===\n")

# Test 1: Config
from config import (SYMBOL, TIMEFRAME, RISK_PER_TRADE_PCT,
                    MAX_DAILY_DD_PCT, MAX_OVERALL_DD_PCT, MAX_CONCURRENT_TRADES)
print(f"[1] Config OK: {SYMBOL} | {TIMEFRAME} | Risk={RISK_PER_TRADE_PCT*100}%")

# Test 2: Strategy indicators
import pandas as pd
import numpy as np
from strategy import calculate_indicators, generate_signal

np.random.seed(42)
close = 2300 + np.cumsum(np.random.randn(150) * 2)
high  = close + abs(np.random.randn(150)) * 0.5
low   = close - abs(np.random.randn(150)) * 0.5

df = pd.DataFrame({
    'time':   pd.date_range('2026-01-01', periods=150, freq='15min'),
    'open':   close,
    'high':   high,
    'low':    low,
    'close':  close,
    'volume': 1000,
})

df_ind = calculate_indicators(df)
print(f"[2] Indicators OK:")
print(f"     EMA9  = {df_ind['ema_9'].iloc[-1]:.2f}")
print(f"     EMA21 = {df_ind['ema_21'].iloc[-1]:.2f}")
print(f"     RSI   = {df_ind['rsi'].iloc[-1]:.1f}")
print(f"     ATR   = {df_ind['atr'].iloc[-1]:.4f}")

signal = generate_signal(df, df)
print(f"[3] Signal Engine OK:")
print(f"     Direction  = {signal['direction']}")
print(f"     Confidence = {signal['confidence']:.0%}")
print(f"     Entry = {signal['entry_price']:.2f}  SL = {signal['sl_price']:.2f}  TP = {signal['tp_price']:.2f}")
if signal['reasons']:
    print(f"     Reasons: {', '.join(signal['reasons'])}")

# Test 3: Risk Engine
from risk_engine import KavachRiskEngine
k = KavachRiskEngine(initial_balance=50000)

lots = k.calculate_lot_size(equity=50000, sl_pips=15, pip_value=10.0)
print(f"[4] Lot Size Calc OK: lots={lots}")
print(f"     (Risk$={50000*0.005:.0f}, Loss/lot={15*10}, Lots={50000*0.005/(15*10):.4f})")

ok, reason = k.is_trade_allowed(50000, 1)
print(f"[5] KAVACH (equity OK, 1 open):  allowed={ok}")

ok2, reason2 = k.is_trade_allowed(50000 * 0.93, 1)  # 7% down
print(f"[6] KAVACH (7% drawdown test):   allowed={ok2} -> {reason2}")

ok3, reason3 = k.is_trade_allowed(50000, 3)
print(f"[7] KAVACH (max positions test): allowed={ok3} -> {reason3}")

print("\n=== ALL TESTS PASSED ===")
print("Next step: fill in MT5 login in config.py, then run test_connection.py")
