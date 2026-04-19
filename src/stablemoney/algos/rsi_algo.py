"""RSI overbought/oversold algo."""
from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np

if TYPE_CHECKING:
    from pybroker.context import ExecContext


class RSIAlgo:
    """RSI overbought/oversold algo with stop loss.

    Entry: RSI < ``oversold``
    Exit: RSI > ``overbought`` or stop loss triggered
    """

    def __init__(
        self,
        stop_loss_pct: float = 5.0,
        oversold: int = 35,
        overbought: int = 65,
    ) -> None:
        self.stop_loss_pct = stop_loss_pct
        self.oversold = oversold
        self.overbought = overbought

    def __call__(self, ctx: ExecContext) -> None:
        rsi = ctx.RSI_14
        ma = ctx.MA_20

        if np.isnan(rsi[-1]) or np.isnan(ma[-1]):
            return

        pos = ctx.long_pos()

        if pos is not None and pos.entries:
            entry_price = float(pos.entries[0].price)
            pnl_pct = (ctx.close[-1] - entry_price) / entry_price * 100
            if pnl_pct <= -self.stop_loss_pct:
                ctx.sell_all_shares()  # type: ignore[no-untyped-call]
                return

        if rsi[-1] < self.oversold and pos is None:
            shares = int(ctx.config.initial_cash / ma[-1] / 10)
            ctx.buy_shares = max(shares, 100)

        if rsi[-1] > self.overbought and pos is not None:
            ctx.sell_all_shares()  # type: ignore[no-untyped-call]
