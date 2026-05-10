"""KDJ + ZXTREND golden cross algo with phased exit."""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import numpy as np

from stablemoney.algos.algo_config import AlgoConfig
from stablemoney.algos.base_algo import BaseAlgo

if TYPE_CHECKING:
    from pybroker.context import ExecContext

logger = logging.getLogger(__name__)

_DEFAULT_ALGO_CONFIG = AlgoConfig()


def _has_recent_golden_cross(
    short_t: np.ndarray,
    long_t: np.ndarray,
    lookback: int,
) -> bool:
    """Check if SHORT_T crossed above LONG_T within the last *lookback* bars."""
    if len(short_t) < 2:
        return False
    max_check = min(lookback, len(short_t) - 1)
    for t in range(max_check):
        prev = -(t + 2)
        curr = -(t + 1)
        if np.isnan(short_t[prev]) or np.isnan(long_t[prev]):
            continue
        if np.isnan(short_t[curr]) or np.isnan(long_t[curr]):
            continue
        if short_t[prev] < long_t[prev] and short_t[curr] > long_t[curr]:
            return True
    return False


class KdjZxtrendAlgo(BaseAlgo):
    """Buy when KDJ.J < 0 within *lookback* bars of ZXTREND golden cross.

    Phased exit strategy:

    1. LONG_T breakdown (open & close < LONG_T) → sell all, any phase
    2. Stop loss → sell all (via PyBroker), any phase
    3. Take profit (phase 0) → sell half, advance to phase 1
    4. SHORT_T breakdown (phase 1) → sell half, advance to phase 2
    """

    def __init__(
        self,
        config: AlgoConfig = _DEFAULT_ALGO_CONFIG,
        lookback: int = 30,
        position_amount: float = 20_000.0,
        take_profit_pct: float = 10.0,
    ) -> None:
        self.config = config
        self.lookback = lookback
        self.position_amount = position_amount
        self.take_profit_pct = take_profit_pct
        self._phase: dict[str, int] = {}

    def trade(self, ctx: ExecContext) -> None:
        kdj_j = ctx.KDJ_J
        short_t = ctx.ZXTREND_SHORT_T
        long_t = ctx.ZXTREND_LONG_T

        if np.isnan(kdj_j[-1]):
            return

        pos = ctx.long_pos()

        # --- No position: check buy condition ---
        if pos is None:
            self._phase.pop(ctx.symbol, None)
            if kdj_j[-1] < 0 and _has_recent_golden_cross(
                short_t, long_t, self.lookback
            ):
                shares = int(self.position_amount / ctx.close[-1] / 100) * 100
                if shares > 0:
                    ctx.buy_shares = shares
                    if self.config.stop_loss_pct > 0:
                        ctx.stop_loss_pct = self.config.stop_loss_pct
                    logger.info(
                        "ZXTREND金叉+KDJ超卖买入 %s: date=%s J=%.2f shares=%d",
                        ctx.symbol,
                        ctx.date[-1],
                        kdj_j[-1],
                        ctx.buy_shares,
                    )
            return

        # --- Has position: check exits ---

        # 1. LONG_T breakdown → sell all (any phase)
        if ctx.open[-1] < long_t[-1] and ctx.close[-1] < long_t[-1]:
            ctx.sell_all_shares()  # type: ignore[no-untyped-call]
            self._phase.pop(ctx.symbol, None)
            logger.info(
                "LONG_T跌破全卖 %s: date=%s open=%.2f close=%.2f long_t=%.2f",
                ctx.symbol,
                ctx.date[-1],
                ctx.open[-1],
                ctx.close[-1],
                long_t[-1],
            )
            return

        # 2. Stop loss handled by PyBroker automatically

        phase = self._phase.get(ctx.symbol, 0)

        # 3. Take profit → sell half (phase 0 only)
        if phase == 0:
            entry_price = float(pos.entries[0].price)
            profit_pct = (
                (float(ctx.close[-1]) - entry_price) / entry_price * 100
            )
            if profit_pct >= self.take_profit_pct:
                sell_qty = int(pos.shares) // 2
                if sell_qty > 0:
                    ctx.sell_shares = sell_qty
                    self._phase[ctx.symbol] = 1
                    logger.info(
                        "盈利%.1f%%卖一半 %s: date=%s shares=%d→%d",
                        profit_pct,
                        ctx.symbol,
                        ctx.date[-1],
                        int(pos.shares),
                        int(pos.shares) - sell_qty,
                    )
            return

        # 4. SHORT_T breakdown → sell half (phase 1 only)
        if phase == 1 and ctx.open[-1] < short_t[-1] and ctx.close[-1] < short_t[-1]:
            sell_qty = int(pos.shares) // 2
            if sell_qty > 0:
                ctx.sell_shares = sell_qty
                self._phase[ctx.symbol] = 2
                logger.info(
                    "SHORT_T跌破卖一半 %s: date=%s shares=%d→%d",
                    ctx.symbol,
                    ctx.date[-1],
                    pos.shares,
                    pos.shares - sell_qty,
                )
