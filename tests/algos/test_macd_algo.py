"""Tests for MacdAlgo."""

from __future__ import annotations

from unittest.mock import MagicMock

import numpy as np

from stablemoney.algos.algo_config import AlgoConfig
from stablemoney.algos.macd_algo import MacdAlgo


def make_macd_context(
    *,
    dif_prev: float,
    dif_curr: float,
    dea_prev: float,
    dea_curr: float,
    close_price: float = 10.0,
    has_position: bool = False,
) -> MagicMock:
    ctx = MagicMock()
    ctx.MACD_DIF = np.array([dif_prev, dif_curr])
    ctx.MACD_DEA = np.array([dea_prev, dea_curr])
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


class TestMacdAlgo:
    def test_golden_cross_buy(self) -> None:
        ctx = make_macd_context(
            dif_prev=-0.1, dif_curr=0.2,
            dea_prev=0.05, dea_curr=0.15,
        )
        algo = MacdAlgo()
        algo.trade(ctx)
        assert ctx.buy_shares > 0

    def test_no_buy_without_positive_dif_dea(self) -> None:
        ctx = make_macd_context(
            dif_prev=-0.2, dif_curr=-0.05,
            dea_prev=-0.15, dea_curr=-0.1,
        )
        algo = MacdAlgo()
        algo.trade(ctx)
        assert ctx.buy_shares == 0

    def test_death_cross_sell(self) -> None:
        ctx = make_macd_context(
            dif_prev=0.2, dif_curr=-0.05,
            dea_prev=0.1, dea_curr=0.05,
            has_position=True,
        )
        algo = MacdAlgo()
        algo.trade(ctx)
        ctx.sell_all_shares.assert_called_once()

    def test_no_sell_without_position(self) -> None:
        ctx = make_macd_context(
            dif_prev=0.2, dif_curr=-0.05,
            dea_prev=0.1, dea_curr=0.05,
        )
        algo = MacdAlgo()
        algo.trade(ctx)
        ctx.sell_all_shares.assert_not_called()

    def test_no_action_on_nan(self) -> None:
        ctx = make_macd_context(
            dif_prev=-0.1, dif_curr=0.2,
            dea_prev=0.05, dea_curr=0.15,
        )
        ctx.MACD_DIF = np.array([0.1, float("nan")])
        algo = MacdAlgo()
        algo.trade(ctx)
        assert ctx.buy_shares == 0

    def test_stop_loss_applied(self) -> None:
        ctx = make_macd_context(
            dif_prev=-0.1, dif_curr=0.2,
            dea_prev=0.05, dea_curr=0.15,
        )
        algo = MacdAlgo(config=AlgoConfig(stop_loss_pct=3.0))
        algo.trade(ctx)
        assert ctx.stop_loss_pct == 3.0
