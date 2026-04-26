"""KDJ + MACD + MA combined algo."""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import numpy as np

from stablemoney.algo_config import AlgoConfig

if TYPE_CHECKING:
    from pybroker.context import ExecContext

logger = logging.getLogger(__name__)

_DEFAULT_ALGO_CONFIG = AlgoConfig()


class KdjMacdMaAlgo:
    """KDJ oversold + MACD bullish + MA bullish alignment.

    Buy: KDJ.J < 0 and MACD DIF > 0 and DEA > 0 and MA10 > MA20
    Sell: no active signal — exits via stop loss, take profit, or max hold bars
    """

    def __init__(self, config: AlgoConfig = _DEFAULT_ALGO_CONFIG) -> None:
        self.config = config

    def __call__(self, ctx: ExecContext) -> None:
        kdj_j = ctx.KDJ_J
        macd_dif = ctx.MACD_DIF
        macd_dea = ctx.MACD_DEA
        ma_short = ctx.MA_10
        ma_long = ctx.MA_20

        if (
            np.isnan(kdj_j[-1])
            or np.isnan(macd_dif[-1])
            or np.isnan(macd_dea[-1])
            or np.isnan(ma_short[-1])
            or np.isnan(ma_long[-1])
        ):
            return

        pos = ctx.long_pos()

        if (
            pos is None
            and kdj_j[-1] < 0
            and macd_dif[-1] > 0
            and macd_dea[-1] > 0
            and ma_short[-1] > ma_long[-1]
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
                "三信号买入 %s: date=%s J=%.2f DIF=%.4f DEA=%.4f "
                "MA10=%.2f MA20=%.2f shares=%d",
                ctx.symbol,
                ctx.date[-1],
                kdj_j[-1],
                macd_dif[-1],
                macd_dea[-1],
                ma_short[-1],
                ma_long[-1],
                ctx.buy_shares,
            )
