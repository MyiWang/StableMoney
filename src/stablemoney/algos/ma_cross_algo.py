"""MA crossover algo: golden cross (MA10 > MA20) buy, death cross sell."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import numpy as np

from stablemoney.algo_config import AlgoConfig

if TYPE_CHECKING:
    from pybroker.context import ExecContext

logger = logging.getLogger(__name__)

_DEFAULT_ALGO_CONFIG = AlgoConfig()


class MACrossAlgo:
    """MA crossover algo.

    Entry: MA(short_period) crosses above MA(long_period) (golden cross).
    Exit: MA(short_period) crosses below MA(long_period) (death cross).
    """

    def __init__(
        self,
        config: AlgoConfig = _DEFAULT_ALGO_CONFIG,
        short_period: int = 10,
        long_period: int = 20,
    ) -> None:
        self.config = config
        self._short_col = f"MA_{short_period}"
        self._long_col = f"MA_{long_period}"

    def __call__(self, ctx: ExecContext) -> None:
        ma_short = getattr(ctx, self._short_col)
        ma_long = getattr(ctx, self._long_col)

        if len(ma_short) < 2 or len(ma_long) < 2:
            return

        if np.isnan(ma_short[-1]) or np.isnan(ma_long[-1]):
            return
        if np.isnan(ma_short[-2]) or np.isnan(ma_long[-2]):
            return

        pos = ctx.long_pos()

        # Golden cross: MA_short crosses above MA_long
        if (
            pos is None
            and ma_short[-2] <= ma_long[-2]
            and ma_short[-1] > ma_long[-1]
        ):
            shares = int(ctx.config.initial_cash / ctx.close[-1] / 10)
            ctx.buy_shares = max(shares, 100)
            if self.config.stop_loss_pct > 0:
                ctx.stop_loss_pct = self.config.stop_loss_pct
            if self.config.take_profit_pct > 0:
                ctx.stop_profit_pct = self.config.take_profit_pct
            if self.config.hold_bars > 0:
                ctx.hold_bars = self.config.hold_bars
            logger.info(
                "金叉买入 %s: date=%s, %s=%.2f > %s=%.2f, shares=%d",
                ctx.symbol, ctx.date[-1],
                self._short_col, ma_short[-1],
                self._long_col, ma_long[-1],
                ctx.buy_shares,
            )

        # Death cross: MA_short crosses below MA_long
        elif (
            pos is not None
            and ma_short[-2] >= ma_long[-2]
            and ma_short[-1] < ma_long[-1]
        ):
            logger.info(
                "死叉卖出 %s: date=%s, %s=%.2f < %s=%.2f",
                ctx.symbol, ctx.date[-1],
                self._short_col, ma_short[-1],
                self._long_col, ma_long[-1],
            )
            ctx.sell_all_shares()  # type: ignore[no-untyped-call]
