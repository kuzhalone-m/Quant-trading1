"""
BEEW QUANTUM — Trade Logger
Writes all trades to a CSV for review, analysis and later ML training.
"""

import csv
import os
import logging
from datetime import datetime
from config import TRADE_LOG

logger = logging.getLogger("beew.logger")

HEADERS = [
    "timestamp", "symbol", "direction", "lots", "entry_price",
    "sl_price", "tp_price", "sl_pips", "confidence", "reasons",
    "order_id", "closed_at", "close_price", "pnl", "result"
]


def _ensure_log_file():
    """Create logs directory and CSV file with headers if not exists."""
    os.makedirs(os.path.dirname(TRADE_LOG), exist_ok=True)
    if not os.path.exists(TRADE_LOG):
        with open(TRADE_LOG, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=HEADERS)
            writer.writeheader()


def log_trade_open(
    symbol: str, direction: str, lots: float,
    entry_price: float, sl_price: float, tp_price: float,
    sl_pips: float, confidence: float, reasons: list, order_id: int
):
    _ensure_log_file()
    row = {
        "timestamp":    datetime.now().isoformat(),
        "symbol":       symbol,
        "direction":    direction,
        "lots":         lots,
        "entry_price":  entry_price,
        "sl_price":     sl_price,
        "tp_price":     tp_price,
        "sl_pips":      round(sl_pips, 5),
        "confidence":   round(confidence, 2),
        "reasons":      " | ".join(reasons),
        "order_id":     order_id,
        "closed_at":    "",
        "close_price":  "",
        "pnl":          "",
        "result":       "OPEN",
    }
    with open(TRADE_LOG, "a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=HEADERS)
        writer.writerow(row)
    logger.info(f"Trade logged: {direction} {symbol} | order={order_id}")


def log_trade_close(order_id: int, close_price: float, pnl: float):
    """Update the open trade row with closing data."""
    _ensure_log_file()
    rows = []
    with open(TRADE_LOG, "r", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if str(row["order_id"]) == str(order_id) and row["result"] == "OPEN":
                row["closed_at"]   = datetime.now().isoformat()
                row["close_price"] = close_price
                row["pnl"]         = round(pnl, 2)
                row["result"]      = "WIN" if pnl > 0 else "LOSS"
            rows.append(row)

    with open(TRADE_LOG, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=HEADERS)
        writer.writeheader()
        writer.writerows(rows)
