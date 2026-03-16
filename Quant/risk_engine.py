"""
BEEW QUANTUM — KAVACH Risk Engine
The safety layer. Every trade must pass ALL checks before execution.

Based on your handwritten notes:
  - Risk per trade = Equity × 0.5% = $250 on $50K
  - Lots = Risk$ / (SL_pips × pip_value)
  - Daily DD hard stop: 4% (Pipstone 2-step)
  - Overall DD hard stop: 10% (Pipstone 2-step)
  - Max 3 concurrent trades (firm allows 4, we stay safe at 3)
"""

import logging
from config import (
    ACCOUNT_BALANCE, RISK_PER_TRADE_PCT,
    MAX_DAILY_DD_PCT, MAX_OVERALL_DD_PCT,
    MAX_CONCURRENT_TRADES
)

logger = logging.getLogger("beew.kavach")


class KavachRiskEngine:
    """
    KAVACH = Sanskrit for 'Shield / Armour'
    Every trade order passes through this engine. If ANY check fails → trade blocked.
    """

    def __init__(self, initial_balance: float = ACCOUNT_BALANCE):
        self.initial_balance  = initial_balance
        self.daily_start_equity = initial_balance  # reset at midnight

    # ── 1. Daily Drawdown Check ───────────────────────────────────────────────
    def check_daily_drawdown(self, current_equity: float) -> tuple[bool, str]:
        """Returns (is_safe, reason)."""
        daily_loss    = self.daily_start_equity - current_equity
        daily_loss_pct = daily_loss / self.daily_start_equity

        if daily_loss_pct >= MAX_DAILY_DD_PCT:
            msg = (f"DAILY DD BREACH: Lost {daily_loss:.2f} "
                   f"({daily_loss_pct*100:.2f}%) today. "
                   f"Limit is {MAX_DAILY_DD_PCT*100:.1f}%. TRADING HALTED.")
            logger.critical(msg)
            return False, msg

        remaining = (MAX_DAILY_DD_PCT - daily_loss_pct) * self.daily_start_equity
        logger.debug(f"Daily DD OK — remaining buffer: ${remaining:.2f}")
        return True, "OK"

    # ── 2. Overall (Max) Drawdown Check ──────────────────────────────────────
    def check_overall_drawdown(self, current_equity: float) -> tuple[bool, str]:
        """Checks against initial balance of the evaluation."""
        overall_loss     = self.initial_balance - current_equity
        overall_loss_pct = overall_loss / self.initial_balance

        if overall_loss_pct >= MAX_OVERALL_DD_PCT:
            msg = (f"OVERALL DD BREACH: Down {overall_loss:.2f} "
                   f"({overall_loss_pct*100:.2f}%) from start. "
                   f"Account effectively blown. STOP ALL TRADING.")
            logger.critical(msg)
            return False, msg

        remaining = (MAX_OVERALL_DD_PCT - overall_loss_pct) * self.initial_balance
        logger.debug(f"Overall DD OK — remaining buffer: ${remaining:.2f}")
        return True, "OK"

    # ── 3. Concurrent Positions Check ─────────────────────────────────────────
    def check_concurrent_positions(self, open_count: int) -> tuple[bool, str]:
        """No more than MAX_CONCURRENT_TRADES open at once."""
        if open_count >= MAX_CONCURRENT_TRADES:
            msg = f"MAX CONCURRENT TRADES reached ({open_count}/{MAX_CONCURRENT_TRADES}). No new entries."
            logger.warning(msg)
            return False, msg
        return True, "OK"

    # ── 4. Lot Size Calculator ─────────────────────────────────────────────────
    def calculate_lot_size(
        self,
        equity: float,
        sl_pips: float,
        pip_value: float,
        volume_min: float = 0.01,
        volume_step: float = 0.01,
        volume_max: float = 100.0
    ) -> float:
        """
        From your handwritten formula:
          Risk$      = Equity × risk_pct         → e.g. 50000 × 0.005 = 250
          Loss/lot   = SL_pips × pip_value        → e.g. 15 × 10 = 150
          Lots       = Risk$ / Loss_per_lot        → e.g. 250 / 150 = 1.67

        pip_value for XAUUSD ≈ $10 per pip per standard lot on most brokers.
        """
        if sl_pips <= 0 or pip_value <= 0:
            logger.error(f"Invalid SL pips ({sl_pips}) or pip_value ({pip_value})")
            return volume_min

        risk_dollars   = equity * RISK_PER_TRADE_PCT
        loss_per_lot   = sl_pips * pip_value
        raw_lots       = risk_dollars / loss_per_lot

        # Round down to volume_step precision
        steps = int(raw_lots / volume_step)
        lots  = round(steps * volume_step, 2)

        # Enforce broker min/max
        lots = max(volume_min, min(lots, volume_max))

        logger.info(
            f"Lot calc: Risk=${risk_dollars:.2f} | SL={sl_pips:.1f}pips | "
            f"pip_val=${pip_value:.2f} | Loss/lot=${loss_per_lot:.2f} | Lots={lots:.2f}"
        )
        return lots

    # ── 5. Master Gate — run all checks ───────────────────────────────────────
    def is_trade_allowed(
        self,
        current_equity: float,
        open_positions_count: int
    ) -> tuple[bool, str]:
        """
        Run every risk check in sequence.
        Returns (True, "OK") only if ALL pass.
        """
        checks = [
            self.check_daily_drawdown(current_equity),
            self.check_overall_drawdown(current_equity),
            self.check_concurrent_positions(open_positions_count),
        ]
        for passed, reason in checks:
            if not passed:
                return False, reason
        return True, "OK"

    # ── 6. Daily Reset ────────────────────────────────────────────────────────
    def reset_daily(self, current_equity: float):
        """Call this at midnight / start of each trading day."""
        self.daily_start_equity = current_equity
        logger.info(f"Daily reset. New start equity: ${current_equity:.2f}")
