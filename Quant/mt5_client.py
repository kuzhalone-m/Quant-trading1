"""
BEEW QUANTUM — MT5 Connection Manager
Handles connecting to MetaTrader 5 and fetching market data.
"""

import MetaTrader5 as mt5
import pandas as pd
import logging
from datetime import datetime
from config import MT5_LOGIN, MT5_PASSWORD, MT5_SERVER

logger = logging.getLogger("beew.mt5")

# ── Timeframe mapping ─────────────────────────────────────────────────────────
TIMEFRAME_MAP = {
    "M1":  mt5.TIMEFRAME_M1,
    "M5":  mt5.TIMEFRAME_M5,
    "M15": mt5.TIMEFRAME_M15,
    "M30": mt5.TIMEFRAME_M30,
    "H1":  mt5.TIMEFRAME_H1,
    "H4":  mt5.TIMEFRAME_H4,
    "D1":  mt5.TIMEFRAME_D1,
}


def connect() -> bool:
    """Initialise and connect to the MT5 terminal."""
    if not mt5.initialize():
        logger.error(f"MT5 initialize() failed: {mt5.last_error()}")
        return False

    if MT5_LOGIN and MT5_PASSWORD and MT5_SERVER:
        authorized = mt5.login(
            login=MT5_LOGIN,
            password=MT5_PASSWORD,
            server=MT5_SERVER
        )
        if not authorized:
            logger.error(f"MT5 login failed: {mt5.last_error()}")
            mt5.shutdown()
            return False

    info = mt5.account_info()
    if info is None:
        logger.error("Could not retrieve account info after login.")
        mt5.shutdown()
        return False

    logger.info(
        f"Connected: Login={info.login} | Balance={info.balance:.2f} "
        f"| Server={info.server} | Demo={'YES' if info.trade_mode == 0 else 'NO'}"
    )
    return True


def disconnect():
    """Cleanly shut down MT5 connection."""
    mt5.shutdown()
    logger.info("MT5 connection closed.")


def get_account_info() -> dict:
    """Return current account snapshot."""
    info = mt5.account_info()
    if info is None:
        return {}
    return {
        "balance":  info.balance,
        "equity":   info.equity,
        "margin":   info.margin,
        "free_margin": info.margin_free,
        "profit":   info.profit,
        "login":    info.login,
        "server":   info.server,
        "currency": info.currency,
    }


def get_candles(symbol: str, timeframe: str, count: int = 200) -> pd.DataFrame:
    """
    Fetch 'count' recent OHLCV candles for a symbol & timeframe.
    Returns a DataFrame with columns: open, high, low, close, volume, time
    """
    tf = TIMEFRAME_MAP.get(timeframe)
    if tf is None:
        raise ValueError(f"Unknown timeframe: {timeframe}")

    rates = mt5.copy_rates_from_pos(symbol, tf, 0, count)
    if rates is None or len(rates) == 0:
        logger.warning(f"No candle data for {symbol} {timeframe}: {mt5.last_error()}")
        return pd.DataFrame()

    df = pd.DataFrame(rates)
    df["time"] = pd.to_datetime(df["time"], unit="s")
    df.rename(columns={"tick_volume": "volume"}, inplace=True)
    df = df[["time", "open", "high", "low", "close", "volume"]]
    return df


def get_symbol_info(symbol: str) -> dict:
    """Return pip size, point, digits, spread for the symbol."""
    info = mt5.symbol_info(symbol)
    if info is None:
        return {}
    return {
        "point":      info.point,
        "digits":     info.digits,
        "spread":     info.spread,
        "trade_tick_size":  info.trade_tick_size,
        "trade_tick_value": info.trade_tick_value,
        "volume_min":       info.volume_min,
        "volume_max":       info.volume_max,
        "volume_step":      info.volume_step,
    }


def get_open_positions(symbol: str = None) -> list:
    """Return all open positions, optionally filtered by symbol."""
    positions = mt5.positions_get(symbol=symbol) if symbol else mt5.positions_get()
    if positions is None:
        return []
    return [p._asdict() for p in positions]


def get_todays_history() -> list:
    """Return all deals closed today for drawdown calculation."""
    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    deals = mt5.history_deals_get(today, datetime.now())
    if deals is None:
        return []
    return [d._asdict() for d in deals]
