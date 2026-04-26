"""KDJ + MACD combined algo."""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import numpy as np

from stablemoney.algos.algo_config import AlgoConfig

if TYPE_CHECKING:
    from pybroker.context import ExecContext

logger = logging.getLogger(__name__)

_DEFAULT_ALGO_CONFIG = AlgoConfig()


class KDJMacdAlgo:
    """KDJ golden/death cross with MACD trend filter.

    Buy: KDJ golden cross (K crosses above D) and MACD DIF > 0 and DEA > 0
    Sell: KDJ death cross (K crosses below D)
    Risk exits: stop loss, take profit, or max hold bars
    """

    def __init__(self, config: AlgoConfig = _DEFAULT_ALGO_CONFIG) -> None:
        self.config = config

    def __call__(self, ctx: ExecContext) -> None:
        kdj_k = ctx.KDJ_K
        kdj_d = ctx.KDJ_D
        macd_dif = ctx.MACD_DIF
        macd_dea = ctx.MACD_DEA

        if (
            np.isnan(kdj_k[-1])
            or np.isnan(kdj_d[-1])
            or np.isnan(macd_dif[-1])
            or np.isnan(macd_dea[-1])
        ):
            return

        pos = ctx.long_pos()

        # Buy: KDJ golden cross + MACD DIF > 0 and DEA > 0
        if (
            pos is None
            and kdj_k[-2] < kdj_d[-2]
            and kdj_k[-1] > kdj_d[-1]
            and macd_dif[-1] > 0
            and macd_dea[-1] > 0
        ):
            shares = int(ctx.config.initial_cash / ctx.close[-1])
            ctx.buy_shares = max(shares, 100)
            if self.config.stop_loss_pct > 0:
                ctx.stop_loss_pct = self.config.stop_loss_pct
            if self.config.take_profit_pct > 0:
                ctx.stop_profit_pct = self.config.take_profit_pct
            if self.config.hold_bars > 0:
                ctx.hold_bars = self.config.hold_bars
            logger.info(
                "KDJ金叉买入 %s: date=%s K=%.2f D=%.2f "
                "DIF=%.4f DEA=%.4f shares=%d",
                ctx.symbol,
                ctx.date[-1],
                kdj_k[-1],
                kdj_d[-1],
                macd_dif[-1],
                macd_dea[-1],
                ctx.buy_shares,
            )
            return

        # Sell: KDJ death cross
        if (
            pos is not None
            and kdj_k[-2] > kdj_d[-2]
            and kdj_k[-1] < kdj_d[-1]
        ):
            ctx.sell_all_shares()  # type: ignore[no-untyped-call]
            logger.info(
                "KDJ死叉卖出 %s: date=%s, K=%.2f, D=%.2f",
                ctx.symbol,
                ctx.date[-1],
                kdj_k[-1],
                kdj_d[-1],
            )
