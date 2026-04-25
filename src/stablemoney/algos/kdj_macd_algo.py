"""KDJ + MACD combined algo."""
from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np

from stablemoney.algo_config import AlgoConfig

if TYPE_CHECKING:
    from pybroker.context import ExecContext

_DEFAULT_ALGO_CONFIG = AlgoConfig()


class KDJMacdAlgo:
    """KDJ + MACD combined algo with risk management exits.

    Entry: KDJ J < 0 and MACD DIF < 0 and MACD DEA < 0
    Exit: stop loss, take profit, or max hold bars
    """

    def __init__(self, config: AlgoConfig = _DEFAULT_ALGO_CONFIG) -> None:
        self.config = config

    def __call__(self, ctx: ExecContext) -> None:
        kdj_j = ctx.KDJ_J
        macd_dif = ctx.MACD_DIF
        macd_dea = ctx.MACD_DEA

        if np.isnan(kdj_j[-1]) or np.isnan(macd_dif[-1]) or np.isnan(macd_dea[-1]):
            return

        pos = ctx.long_pos()

        if (
            pos is None
            and kdj_j[-1] < 0
            and macd_dif[-1] < 0
            and macd_dea[-1] < 0
        ):
            shares = int(ctx.config.initial_cash / ctx.close[-1] / 10)
            ctx.buy_shares = max(shares, 100)
            if self.config.stop_loss_pct > 0:
                ctx.stop_loss_pct = self.config.stop_loss_pct
            if self.config.take_profit_pct > 0:
                ctx.stop_profit_pct = self.config.take_profit_pct
            if self.config.hold_bars > 0:
                ctx.hold_bars = self.config.hold_bars
