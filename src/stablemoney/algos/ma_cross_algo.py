"""MA golden/death cross algo."""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import numpy as np

from stablemoney.algos.algo_config import AlgoConfig

if TYPE_CHECKING:
    from pybroker.context import ExecContext

logger = logging.getLogger(__name__)

_DEFAULT_ALGO_CONFIG = AlgoConfig()


class MACrossAlgo:
    """MA10/MA20 golden cross buy, death cross sell.

    Buy: MA10 crosses above MA20 (golden cross)
    Sell: MA10 crosses below MA20 (death cross)
    Risk exits: stop loss, take profit, or max hold bars
    """

    def __init__(self, config: AlgoConfig = _DEFAULT_ALGO_CONFIG) -> None:
        self.config = config

    def __call__(self, ctx: ExecContext) -> None:
        ma_short = ctx.MA_10
        ma_long = ctx.MA_20

        if np.isnan(ma_short[-1]) or np.isnan(ma_long[-1]):
            return

        pos = ctx.long_pos()

        # Buy: MA golden cross (MA10 crosses above MA20)
        if (
            pos is None
            and ma_short[-2] < ma_long[-2]
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
                "MA金叉买入 %s: date=%s MA10=%.4f MA20=%.4f "
                "shares=%d",
                ctx.symbol,
                ctx.date[-1],
                ma_short[-1],
                ma_long[-1],
                ctx.buy_shares,
            )
            return

        # Sell: MA death cross (MA10 crosses below MA20)
        if (
            pos is not None
            and ma_short[-2] > ma_long[-2]
            and ma_short[-1] < ma_long[-1]
        ):
            ctx.sell_all_shares()  # type: ignore[no-untyped-call]
            logger.info(
                "MA死叉卖出 %s: date=%s MA10=%.4f MA20=%.4f",
                ctx.symbol,
                ctx.date[-1],
                ma_short[-1],
                ma_long[-1],
            )
