"""RSI overbought/oversold algo."""

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


class RSIAlgo:
    """RSI overbought/oversold algo with stop loss.

    Entry: RSI < ``oversold``
    Exit: RSI > ``overbought`` or stop loss triggered
    """

    def __init__(
        self,
        config: AlgoConfig = _DEFAULT_ALGO_CONFIG,
        oversold: int = 35,
        overbought: int = 65,
    ) -> None:
        self.config = config
        self.oversold = oversold
        self.overbought = overbought

    def __call__(self, ctx: ExecContext) -> None:
        rsi = ctx.RSI_14
        ma = ctx.MA_20

        if np.isnan(rsi[-1]) or np.isnan(ma[-1]):
            return

        logger.debug(
            "date=%s rsi=%.2f ma=%.2f", ctx.date[-1], rsi[-1], ma[-1]
        )

        pos = ctx.long_pos()

        if rsi[-1] < self.oversold and pos is None:
            shares = int(ctx.config.initial_cash / ma[-1] / 10)
            place_buy(ctx, shares, self.config)
            logger.info(
                "RSI买入 %s: date=%s, rsi=%.2f < %d, shares=%d",
                ctx.symbol, ctx.date[-1], rsi[-1], self.oversold, ctx.buy_shares,
            )

        if rsi[-1] > self.overbought and pos is not None:
            logger.info(
                "RSI卖出 %s: date=%s, rsi=%.2f > %d",
                ctx.symbol, ctx.date[-1], rsi[-1], self.overbought,
            )
            ctx.sell_all_shares()  # type: ignore[no-untyped-call]
