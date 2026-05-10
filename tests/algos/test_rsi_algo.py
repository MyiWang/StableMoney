"""Tests for RSIAlgo."""

from __future__ import annotations

import numpy as np

from stablemoney.algos.algo_config import AlgoConfig
from stablemoney.algos.rsi_algo import RSIAlgo

from .conftest import make_exec_context


class TestRSIAlgo:
    def test_buy_when_oversold(self) -> None:
        ctx = make_exec_context(rsi_value=25.0, ma_value=15.0, close_price=14.0)
        algo = RSIAlgo()
        algo.trade(ctx)
        assert ctx.buy_shares > 0

    def test_no_buy_when_normal(self) -> None:
        ctx = make_exec_context(rsi_value=50.0, ma_value=15.0, close_price=14.0)
        algo = RSIAlgo()
        algo.trade(ctx)
        assert ctx.buy_shares == 0

    def test_no_buy_when_overbought(self) -> None:
        ctx = make_exec_context(rsi_value=70.0, ma_value=15.0, close_price=14.0)
        algo = RSIAlgo()
        algo.trade(ctx)
        assert ctx.buy_shares == 0

    def test_sell_when_overbought_with_position(self) -> None:
        ctx = make_exec_context(
            rsi_value=70.0, ma_value=15.0, close_price=14.0,
            has_position=True, entry_price=10.0,
        )
        algo = RSIAlgo()
        algo.trade(ctx)
        ctx.sell_all_shares.assert_called_once()

    def test_no_sell_when_overbought_no_position(self) -> None:
        ctx = make_exec_context(rsi_value=70.0, ma_value=15.0, close_price=14.0)
        algo = RSIAlgo()
        algo.trade(ctx)
        ctx.sell_all_shares.assert_not_called()

    def test_no_action_on_nan_rsi(self) -> None:
        ctx = make_exec_context(rsi_value=25.0, ma_value=15.0, close_price=14.0)
        ctx.RSI_14 = np.array([float("nan")])
        algo = RSIAlgo()
        algo.trade(ctx)
        assert ctx.buy_shares == 0

    def test_no_action_on_nan_ma(self) -> None:
        ctx = make_exec_context(rsi_value=25.0, ma_value=15.0, close_price=14.0)
        ctx.MA_20 = np.array([float("nan")])
        algo = RSIAlgo()
        algo.trade(ctx)
        assert ctx.buy_shares == 0

    def test_custom_thresholds(self) -> None:
        ctx = make_exec_context(rsi_value=25.0, ma_value=15.0, close_price=14.0)
        algo = RSIAlgo(oversold=30, overbought=70)
        algo.trade(ctx)
        assert ctx.buy_shares > 0

    def test_stop_loss_applied(self) -> None:
        ctx = make_exec_context(rsi_value=25.0, ma_value=15.0, close_price=14.0)
        algo = RSIAlgo(config=AlgoConfig(stop_loss_pct=5.0))
        algo.trade(ctx)
        assert ctx.stop_loss_pct == 5.0

    def test_no_double_buy(self) -> None:
        ctx = make_exec_context(
            rsi_value=25.0, ma_value=15.0, close_price=14.0,
            has_position=True, entry_price=14.0,
        )
        algo = RSIAlgo()
        algo.trade(ctx)
        assert ctx.buy_shares == 0
