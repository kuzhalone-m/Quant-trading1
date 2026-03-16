"""
BEEW QUANTUM — STRATUS Strategy Engine (v1 — EMA Cross + RSI + ATR)

Strategy Logic:
  LONG entry when:
    1. EMA_FAST > EMA_SLOW (fast crosses above slow — bullish momentum)
    2. HTF EMA_TREND: price > EMA50 on H1 (higher timeframe is bullish)
    3. RSI < 65 (not overbought — catching early momentum, not exhaustion)
    4. ATR is above average (volatility present — not flat market)

  SHORT entry when:
    1. EMA_FAST < EMA_SLOW (fast crosses below slow — bearish momentum)
    2. HTF: price < EMA50 on H1
    3. RSI > 35 (not oversold)
    4. ATR above average

  SL  = entry +/- (ATR x 1.5)     <- dynamic per volatility
  TP  = entry +/- (ATR x 2.5)     <- ~1:1.67 R:R minimum

  Confidence score: each condition adds weight, scaled 0-1.0
  Trade only executes if confidence >= MIN_CONFIDENCE (0.60)

  NOTE: All indicators use pure pandas/numpy — no external TA library.
        Compatible with Python 3.14+.
"""

import pandas as pd
import numpy as np
import logging
from config import (
    EMA_FAST, EMA_SLOW, EMA_TREND,
    RSI_PERIOD, RSI_OVERBOUGHT, RSI_OVERSOLD,
    ATR_PERIOD, ATR_SL_MULTIPLIER, ATR_TP_MULTIPLIER,
    MIN_CONFIDENCE
)

logger = logging.getLogger("beew.stratus")


# ── Pure pandas/numpy indicator functions (Python 3.14 compatible) ─────────────

def _ema(series: pd.Series, period: int) -> pd.Series:
    """Exponential Moving Average."""
    return series.ewm(span=period, adjust=False).mean()


def _rsi(series: pd.Series, period: int = 14) -> pd.Series:
    """RSI using Wilder smoothing (ewm alpha=1/period)."""
    delta    = series.diff()
    gain     = delta.clip(lower=0)
    loss     = (-delta).clip(lower=0)
    avg_gain = gain.ewm(alpha=1 / period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1 / period, adjust=False).mean()
    rs       = avg_gain / avg_loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))


def _atr(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
    """Average True Range using EWM smoothing."""
    prev_close = close.shift(1)
    tr = pd.concat([
        high - low,
        (high - prev_close).abs(),
        (low  - prev_close).abs(),
    ], axis=1).max(axis=1)
    return tr.ewm(alpha=1 / period, adjust=False).mean()


# ── Main indicator calculation ─────────────────────────────────────────────────

def calculate_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """Add all technical indicators to the candle DataFrame."""
    if df.empty or len(df) < 60:
        logger.warning("Not enough candles to calculate indicators (need >=60)")
        return df

    df = df.copy()

    # EMAs
    df[f"ema_{EMA_FAST}"]  = _ema(df["close"], EMA_FAST)
    df[f"ema_{EMA_SLOW}"]  = _ema(df["close"], EMA_SLOW)
    df[f"ema_{EMA_TREND}"] = _ema(df["close"], EMA_TREND)

    # RSI
    df["rsi"] = _rsi(df["close"], RSI_PERIOD)

    # ATR
    df["atr"]     = _atr(df["high"], df["low"], df["close"], ATR_PERIOD)
    df["atr_avg"] = df["atr"].rolling(20).mean()

    # Volatility flag
    df["high_volatility"] = df["atr"] > df["atr_avg"]

    return df


# ── Signal generation ──────────────────────────────────────────────────────────

def generate_signal(df: pd.DataFrame, htf_df: pd.DataFrame) -> dict:
    """
    Analyse the most recent completed candle and return a signal dict:
    {
      "direction":   "BUY" | "SELL" | "NONE",
      "confidence":  0.0-1.0,
      "entry_price": float,
      "sl_price":    float,
      "tp_price":    float,
      "sl_pips":     float,
      "atr":         float,
      "reasons":     [str, ...]
    }
    """
    signal = {
        "direction":   "NONE",
        "confidence":  0.0,
        "entry_price": 0.0,
        "sl_price":    0.0,
        "tp_price":    0.0,
        "sl_pips":     0.0,
        "atr":         0.0,
        "reasons":     [],
    }

    df     = calculate_indicators(df)
    htf_df = calculate_indicators(htf_df)

    if df.empty or len(df) < 3:
        signal["reasons"].append("Insufficient M15 data")
        return signal

    # Use the last COMPLETED candle (-2), since -1 is still forming
    last = df.iloc[-2]
    prev = df.iloc[-3]

    ema_f      = last[f"ema_{EMA_FAST}"]
    ema_s      = last[f"ema_{EMA_SLOW}"]
    ema_f_prev = prev[f"ema_{EMA_FAST}"]
    ema_s_prev = prev[f"ema_{EMA_SLOW}"]
    rsi        = last["rsi"]
    atr        = last["atr"]
    price      = last["close"]

    if pd.isna(ema_f) or pd.isna(ema_s) or pd.isna(rsi) or pd.isna(atr):
        signal["reasons"].append("Indicator NaN — waiting for warmup candles")
        return signal

    # HTF Trend (H1)
    htf_bullish = False
    htf_bearish = False
    if not htf_df.empty and len(htf_df) >= 2:
        htf_last = htf_df.iloc[-2]
        htf_ema  = htf_last.get(f"ema_{EMA_TREND}")
        if htf_ema is not None and not pd.isna(htf_ema):
            htf_bullish = htf_last["close"] > htf_ema
            htf_bearish = htf_last["close"] < htf_ema

    # EMA cross detection
    bullish_cross = (ema_f_prev <= ema_s_prev) and (ema_f > ema_s)
    bearish_cross = (ema_f_prev >= ema_s_prev) and (ema_f < ema_s)

    # Score conditions (each worth 0.25)
    WEIGHT = 0.25
    buy_conditions  = []
    sell_conditions = []

    if bullish_cross:
        buy_conditions.append(f"EMA {EMA_FAST}/{EMA_SLOW} bullish cross")
    if rsi < RSI_OVERBOUGHT:
        buy_conditions.append(f"RSI={rsi:.1f} < {RSI_OVERBOUGHT} (not overbought)")
    if htf_bullish:
        buy_conditions.append("H1 trend bullish (price > EMA50)")
    if last["high_volatility"]:
        buy_conditions.append(f"ATR={atr:.2f} above avg (good volatility)")

    if bearish_cross:
        sell_conditions.append(f"EMA {EMA_FAST}/{EMA_SLOW} bearish cross")
    if rsi > RSI_OVERSOLD:
        sell_conditions.append(f"RSI={rsi:.1f} > {RSI_OVERSOLD} (not oversold)")
    if htf_bearish:
        sell_conditions.append("H1 trend bearish (price < EMA50)")
    if last["high_volatility"]:
        sell_conditions.append(f"ATR={atr:.2f} above avg (good volatility)")

    buy_conf  = len(buy_conditions)  * WEIGHT
    sell_conf = len(sell_conditions) * WEIGHT

    # Determine direction
    if buy_conf >= sell_conf and buy_conf >= MIN_CONFIDENCE:
        direction  = "BUY"
        confidence = buy_conf
        reasons    = buy_conditions
        sl_price   = round(price - atr * ATR_SL_MULTIPLIER, 5)
        tp_price   = round(price + atr * ATR_TP_MULTIPLIER, 5)
    elif sell_conf > buy_conf and sell_conf >= MIN_CONFIDENCE:
        direction  = "SELL"
        confidence = sell_conf
        reasons    = sell_conditions
        sl_price   = round(price + atr * ATR_SL_MULTIPLIER, 5)
        tp_price   = round(price - atr * ATR_TP_MULTIPLIER, 5)
    else:
        all_reasons = buy_conditions + sell_conditions
        signal["confidence"] = max(buy_conf, sell_conf)
        signal["reasons"]    = all_reasons if all_reasons else ["No confluence — no trade"]
        logger.debug(f"No signal. Max confidence: {signal['confidence']:.0%}")
        return signal

    sl_pips = abs(price - sl_price)

    signal.update({
        "direction":   direction,
        "confidence":  confidence,
        "entry_price": price,
        "sl_price":    sl_price,
        "tp_price":    tp_price,
        "sl_pips":     sl_pips,
        "atr":         atr,
        "reasons":     reasons,
    })

    logger.info(
        f"SIGNAL: {direction} | Confidence={confidence:.0%} | "
        f"Entry={price:.5f} | SL={sl_price:.5f} | TP={tp_price:.5f} | "
        f"Reasons: {', '.join(reasons)}"
    )
    return signal
