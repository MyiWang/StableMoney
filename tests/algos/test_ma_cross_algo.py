"""Tests for MACrossAlgo."""

from __future__ import annotations

from unittest.mock import MagicMock

import numpy as np

from stablemoney.algos.algo_config import AlgoConfig
from stablemoney.algos.ma_cross_algo import MACrossAlgo


def make_ma_cross_context(
    *,
    ma_short_prev: float,
    ma_short_curr: float,
    ma_long_prev: float,
    ma_long_curr: float,
    close_price: float = 10.0,
    has_position: bool = False,
) -> MagicMock:
    ctx = MagicMock()
    ctx.MA_10 = np.array([ma_short_prev, ma_short_curr])
    ctx.MA_20 = np.array([ma_long_prev, ma_long_curr])
    ctx.close = np.array([close_price])
    ctx.date = np.array([np.datetime64("2024-06-01")])
    ctx.symbol = "600519.SH"
    ctx.config = MagicMock()
    ctx.config.initial_cash = 100_000
    ctx.buy_shares = 0

    if has_position:
        pos = MagicMock()
        ctx.long_pos.return_value = pos
    else:
        ctx.long_pos.return_value = None

    return ctx


class TestMACrossAlgo:
    def test_golden_cross_buy(self) -> None:
        ctx = make_ma_cross_context(
            ma_short_prev=9.0, ma_short_curr=11.0,
            ma_long_prev=10.0, ma_long_curr=10.5,
        )
        algo = MACrossAlgo()
        algo(ctx)
        assert ctx.buy_shares > 0

    def test_no_buy_without_cross(self) -> None:
        ctx = make_ma_cross_context(
            ma_short_prev=11.0, ma_short_curr=12.0,
            ma_long_prev=10.0, ma_long_curr=10.5,
        )
        algo = MACrossAlgo()
        algo(ctx)
        assert ctx.buy_shares == 0

    def test_death_cross_sell(self) -> None:
        ctx = make_ma_cross_context(
            ma_short_prev=11.0, ma_short_curr=9.0,
            ma_long_prev=10.0, ma_long_curr=10.5,
            has_position=True,
        )
        algo = MACrossAlgo()
        algo(ctx)
        ctx.sell_all_shares.assert_called_once()

    def test_no_sell_without_cross(self) -> None:
        ctx = make_ma_cross_context(
            ma_short_prev=9.0, ma_short_curr=8.0,
            ma_long_prev=10.0, ma_long_curr=10.5,
            has_position=True,
        )
        algo = MACrossAlgo()
        algo(ctx)
        ctx.sell_all_shares.assert_not_called()

    def test_no_action_on_nan(self) -> None:
        ctx = make_ma_cross_context(
            ma_short_prev=9.0, ma_short_curr=11.0,
            ma_long_prev=10.0, ma_long_curr=10.5,
        )
        ctx.MA_10 = np.array([9.0, float("nan")])
        algo = MACrossAlgo()
        algo(ctx)
        assert ctx.buy_shares == 0

    def test_stop_loss_applied(self) -> None:
        ctx = make_ma_cross_context(
            ma_short_prev=9.0, ma_short_curr=11.0,
            ma_long_prev=10.0, ma_long_curr=10.5,
        )
        algo = MACrossAlgo(config=AlgoConfig(stop_loss_pct=5.0))
        algo(ctx)
        assert ctx.stop_loss_pct == 5.0
