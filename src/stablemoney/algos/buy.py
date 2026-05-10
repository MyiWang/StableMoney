"""Common buy order placement with risk control."""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pybroker.context import ExecContext

    from stablemoney.algos.algo_config import AlgoConfig


def place_buy(
    ctx: ExecContext,
    shares: int,
    config: AlgoConfig,
) -> None:
    """Place a buy order with risk control parameters.

    Sets ``ctx.buy_shares`` (minimum 100) and applies stop loss,
    take profit, and max hold bars from *config* if non-zero.
    """
    ctx.buy_shares = max(shares, 100)
    if config.stop_loss_pct > 0:
        ctx.stop_loss_pct = config.stop_loss_pct
    if config.take_profit_pct > 0:
        ctx.stop_profit_pct = config.take_profit_pct
    if config.hold_bars > 0:
        ctx.hold_bars = config.hold_bars
