"""KDJ + MACD combined algo."""
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


class KDJMacdAlgo(BaseAlgo):
    """KDJ oversold dip + MACD bullish + MA trend filter.

    Buy: J[-2] < 0 and J[-1] < J[-2] and DIF > 0 and DEA > 0
         and close > MA60 and close < MA20
    Sell: no active signal — exits via stop loss, take profit, or max hold bars
    """

    def __init__(self, config: AlgoConfig = _DEFAULT_ALGO_CONFIG) -> None:
        self.config = config

    def trade(self, ctx: ExecContext) -> None:
        kdj_j = ctx.KDJ_J
        macd_dif = ctx.MACD_DIF
        macd_dea = ctx.MACD_DEA
        ma_20 = ctx.MA_20
        ma_60 = ctx.MA_60

        if (
            np.isnan(kdj_j[-1])
            or np.isnan(macd_dif[-1])
            or np.isnan(macd_dea[-1])
            or np.isnan(ma_20[-1])
            or np.isnan(ma_60[-1])
        ):
            return

        pos = ctx.long_pos()

        if (
            pos is None
            and kdj_j[-2] < 0
            and kdj_j[-1] < kdj_j[-2]
            and macd_dif[-1] > 0
            and macd_dea[-1] > 0
            and ctx.close[-1] > ma_60[-1]
            and ctx.close[-1] < ma_20[-1]
        ):
            shares = int(ctx.config.initial_cash / ctx.close[-1])
            place_buy(ctx, shares, self.config)
            logger.info(
                "KDJ超卖买入 %s: date=%s J=%.2f "
                "DIF=%.4f DEA=%.4f close=%.2f "
                "MA20=%.2f MA60=%.2f shares=%d",
                ctx.symbol,
                ctx.date[-1],
                kdj_j[-1],
                macd_dif[-1],
                macd_dea[-1],
                ctx.close[-1],
                ma_20[-1],
                ma_60[-1],
                ctx.buy_shares,
            )
