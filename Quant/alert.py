"""
BEEW QUANTUM — Telegram Alert Module
Sends notifications when trades open/close or errors occur.
Set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID in config.py to activate.
"""

import requests
import logging
from config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID

logger = logging.getLogger("beew.alert")


def send_telegram(message: str) -> bool:
    """
    Send a message via Telegram Bot API.
    Returns True if successful, False if not configured or failed.
    """
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        logger.debug("Telegram not configured — skipping alert")
        return False

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id":    TELEGRAM_CHAT_ID,
        "text":       message,
        "parse_mode": "HTML",
    }
    try:
        resp = requests.post(url, json=payload, timeout=5)
        if resp.status_code == 200:
            return True
        logger.warning(f"Telegram error {resp.status_code}: {resp.text}")
        return False
    except Exception as e:
        logger.warning(f"Telegram send failed: {e}")
        return False
