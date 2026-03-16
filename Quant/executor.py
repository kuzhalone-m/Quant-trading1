"""
BEEW QUANTUM — ZEPHYR Trade Executor
Places, monitors, and manages orders on MT5.
"""

import MetaTrader5 as mt5
import logging
import time
from datetime import datetime
from config import MIN_TRADE_HOLD_SECONDS

logger = logging.getLogger("beew.zephyr")


def _get_fill_type(symbol: str):
    """Automatically choose the right fill type for the broker."""
    info = mt5.symbol_info(symbol)
    if info is None:
        return mt5.ORDER_FILLING_IOC
    filling_mode = info.filling_mode
    if filling_mode & mt5.ORDER_FILLING_FOK:
        return mt5.ORDER_FILLING_FOK
    elif filling_mode & mt5.ORDER_FILLING_IOC:
        return mt5.ORDER_FILLING_IOC
    return mt5.ORDER_FILLING_RETURN


def place_order(
    symbol: str,
    direction: str,       # "BUY" or "SELL"
    lots: float,
    sl_price: float,
    tp_price: float,
    comment: str = "BEEW-QUANTUM"
) -> dict:
    """
    Send a market order to MT5.
    Returns a result dict with { success, order_id, price, error }.
    """
    order_type = mt5.ORDER_TYPE_BUY if direction == "BUY" else mt5.ORDER_TYPE_SELL

    tick = mt5.symbol_info_tick(symbol)
    if tick is None:
        logger.error(f"Cannot get tick for {symbol}")
        return {"success": False, "error": "No tick data"}

    entry_price = tick.ask if direction == "BUY" else tick.bid

    request = {
        "action":    mt5.TRADE_ACTION_DEAL,
        "symbol":    symbol,
        "volume":    lots,
        "type":      order_type,
        "price":     entry_price,
        "sl":        sl_price,
        "tp":        tp_price,
        "deviation": 20,               # max slippage in points
        "magic":     20260316,         # BEEW magic number — identifies our bot's trades
        "comment":   comment,
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": _get_fill_type(symbol),
    }

    logger.info(
        f"Placing {direction} order: {symbol} {lots} lots | "
        f"SL={sl_price:.5f} | TP={tp_price:.5f}"
    )

    result = mt5.order_send(request)

    if result is None:
        error = str(mt5.last_error())
        logger.error(f"order_send returned None: {error}")
        return {"success": False, "error": error}

    if result.retcode != mt5.TRADE_RETCODE_DONE:
        logger.error(
            f"Order FAILED: retcode={result.retcode} | comment={result.comment}"
        )
        return {
            "success": False,
            "error": f"retcode={result.retcode}: {result.comment}",
            "retcode": result.retcode,
        }

    logger.info(
        f"✅ Order PLACED: ticket={result.order} | "
        f"price={result.price:.5f} | vol={result.volume}"
    )
    return {
        "success":   True,
        "order_id":  result.order,
        "price":     result.price,
        "volume":    result.volume,
        "symbol":    symbol,
        "direction": direction,
        "sl":        sl_price,
        "tp":        tp_price,
        "timestamp": datetime.now().isoformat(),
    }


def close_position(ticket: int, symbol: str, lots: float, direction: str) -> dict:
    """Close a specific position by ticket number."""
    close_type = mt5.ORDER_TYPE_SELL if direction == "BUY" else mt5.ORDER_TYPE_BUY

    tick = mt5.symbol_info_tick(symbol)
    if tick is None:
        return {"success": False, "error": "No tick data for close"}

    close_price = tick.bid if direction == "BUY" else tick.ask

    request = {
        "action":     mt5.TRADE_ACTION_DEAL,
        "symbol":     symbol,
        "volume":     lots,
        "type":       close_type,
        "position":   ticket,
        "price":      close_price,
        "deviation":  20,
        "magic":      20260316,
        "comment":    "BEEW-CLOSE",
        "type_time":  mt5.ORDER_TIME_GTC,
        "type_filling": _get_fill_type(symbol),
    }

    result = mt5.order_send(request)
    if result is None or result.retcode != mt5.TRADE_RETCODE_DONE:
        err = mt5.last_error() if result is None else result.comment
        logger.error(f"Close FAILED for ticket {ticket}: {err}")
        return {"success": False, "error": str(err)}

    logger.info(f"✅ Position CLOSED: ticket={ticket} at {close_price:.5f}")
    return {"success": True, "ticket": ticket, "close_price": close_price}


def close_all_positions(symbol: str = None) -> list:
    """Emergency: close every open position (optional: for one symbol only)."""
    positions = mt5.positions_get(symbol=symbol) if symbol else mt5.positions_get()
    if not positions:
        return []

    results = []
    for pos in positions:
        direction = "BUY" if pos.type == mt5.ORDER_TYPE_BUY else "SELL"
        r = close_position(pos.ticket, pos.symbol, pos.volume, direction)
        results.append(r)
        time.sleep(0.2)  # small delay between close orders

    return results


def move_sl_to_breakeven(ticket: int, entry_price: float, min_profit_pips: float = 10.0) -> bool:
    """
    Move stop-loss to break-even once price has moved 'min_profit_pips' in our favour.
    Returns True if modified, False if not applicable.
    """
    position = None
    positions = mt5.positions_get()
    if positions:
        for p in positions:
            if p.ticket == ticket:
                position = p
                break

    if position is None:
        return False

    symbol_info = mt5.symbol_info(position.symbol)
    if symbol_info is None:
        return False

    point     = symbol_info.point
    is_buy    = position.type == mt5.ORDER_TYPE_BUY
    current   = mt5.symbol_info_tick(position.symbol)
    if current is None:
        return False

    current_price = current.bid if is_buy else current.ask
    profit_pips   = (current_price - entry_price) / point if is_buy else (entry_price - current_price) / point

    if profit_pips < min_profit_pips:
        return False  # Not enough profit yet

    new_sl = entry_price + (5 * point) if is_buy else entry_price - (5 * point)

    # Only move SL if it improves the current sl
    if is_buy and new_sl <= position.sl:
        return False
    if not is_buy and new_sl >= position.sl:
        return False

    request = {
        "action":   mt5.TRADE_ACTION_SLTP,
        "position": ticket,
        "sl":       new_sl,
        "tp":       position.tp,
    }
    result = mt5.order_send(request)
    if result and result.retcode == mt5.TRADE_RETCODE_DONE:
        logger.info(f"📦 Break-even set for ticket={ticket} | New SL={new_sl:.5f}")
        return True

    return False
