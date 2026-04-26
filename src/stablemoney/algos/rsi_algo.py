"""RSI overbought/oversold algo."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import numpy as np

from stablemoney.algos.algo_config import AlgoConfig

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

        if pos is not None and pos.entries and self.config.stop_loss_pct > 0:
            entry_price = float(pos.entries[0].price)
            pnl_pct = (ctx.close[-1] - entry_price) / entry_price * 100
            if pnl_pct <= -self.config.stop_loss_pct:
                logger.info(
                    "止损卖出 %s: date=%s, entry=%.2f, close=%.2f, pnl=%.2f%%",
                    ctx.symbol, ctx.date[-1], entry_price, ctx.close[-1], pnl_pct,
                )
                ctx.sell_all_shares()  # type: ignore[no-untyped-call]
                return

        if rsi[-1] < self.oversold and pos is None:
            shares = int(ctx.config.initial_cash / ma[-1] / 10)
            ctx.buy_shares = max(shares, 100)
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
