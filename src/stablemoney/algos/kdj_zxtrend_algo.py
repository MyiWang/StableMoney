"""KDJ + ZXTREND golden cross algo."""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import numpy as np

from stablemoney.algos.algo_config import AlgoConfig
from stablemoney.algos.buy import place_buy

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


class KdjZxtrendAlgo:
    """Buy when KDJ.J < 0 within *lookback* bars of ZXTREND golden cross.

    Buy:  ZXTREND SHORT_T crossed above LONG_T within lookback bars,
          and current J < 0
    Sell: SHORT_T drops below LONG_T (death cross), or via stop loss,
          take profit, or max hold bars
    """

    def __init__(
        self,
        config: AlgoConfig = _DEFAULT_ALGO_CONFIG,
        lookback: int = 30,
    ) -> None:
        self.config = config
        self.lookback = lookback

    def __call__(self, ctx: ExecContext) -> None:
        kdj_j = ctx.KDJ_J
        short_t = ctx.ZXTREND_SHORT_T
        long_t = ctx.ZXTREND_LONG_T

        if np.isnan(kdj_j[-1]):
            return

        pos = ctx.long_pos()

        # Sell on death cross: SHORT_T drops below LONG_T
        if (
            pos is not None
            and len(short_t) >= 2
            and short_t[-2] > long_t[-2]
            and short_t[-1] < long_t[-1]
        ):
            ctx.sell_all_shares()  # type: ignore[no-untyped-call]
            logger.info(
                "ZXTREND死叉卖出 %s: date=%s short=%.2f long=%.2f",
                ctx.symbol,
                ctx.date[-1],
                short_t[-1],
                long_t[-1],
            )
            return

        if (
            pos is None
            and kdj_j[-1] < 0
            and _has_recent_golden_cross(short_t, long_t, self.lookback)
        ):
            shares = int(ctx.config.initial_cash / ctx.close[-1])
            place_buy(ctx, shares, self.config)
            logger.info(
                "ZXTREND金叉+KDJ超卖买入 %s: date=%s J=%.2f shares=%d",
                ctx.symbol,
                ctx.date[-1],
                kdj_j[-1],
                ctx.buy_shares,
            )
