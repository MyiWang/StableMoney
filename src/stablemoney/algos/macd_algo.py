"""MACD golden/death cross algo."""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import numpy as np

from stablemoney.algos.algo_config import AlgoConfig
from stablemoney.algos.base_algo import BaseAlgo
from stablemoney.algos.buy import place_buy

if TYPE_CHECKING:
    from pybroker.context import ExecContext

logger = logging.getLogger(__name__)

_DEFAULT_ALGO_CONFIG = AlgoConfig()


class MacdAlgo(BaseAlgo):
    """MACD DIF/DEA golden cross buy, death cross sell.

    Buy: DIF crosses above DEA (golden cross)
    Sell: DIF crosses below DEA (death cross)
    Risk exits: stop loss, take profit, or max hold bars
    """

    def __init__(self, config: AlgoConfig = _DEFAULT_ALGO_CONFIG) -> None:
        self.config = config

    def trade(self, ctx: ExecContext) -> None:
        dif = ctx.MACD_DIF
        dea = ctx.MACD_DEA

        if np.isnan(dif[-1]) or np.isnan(dea[-1]):
            return

        pos = ctx.long_pos()

        # Buy: MACD golden cross (DIF crosses above DEA) with DIF > 0 and DEA > 0
        if (
            pos is None
            and dif[-2] < dea[-2]
            and dif[-1] > dea[-1]
            and dif[-1] > 0
            and dea[-1] > 0
        ):
            shares = int(ctx.config.initial_cash / ctx.close[-1])
            place_buy(ctx, shares, self.config)
            logger.info(
                "MACD金叉买入 %s: date=%s DIF=%.4f DEA=%.4f "
                "shares=%d",
                ctx.symbol,
                ctx.date[-1],
                dif[-1],
                dea[-1],
                ctx.buy_shares,
            )
            return

        # Sell: MACD death cross (DIF crosses below DEA)
        if (
            pos is not None
            and dif[-2] > dea[-2]
            and dif[-1] < dea[-1]
        ):
            ctx.sell_all_shares()  # type: ignore[no-untyped-call]
            logger.info(
                "MACD死叉卖出 %s: date=%s DIF=%.4f DEA=%.4f",
                ctx.symbol,
                ctx.date[-1],
                dif[-1],
                dea[-1],
            )
