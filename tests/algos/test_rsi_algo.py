"""Tests for RSIAlgo trading logic."""

from __future__ import annotations

from stablemoney.algos.rsi_algo import RSIAlgo
from tests.algos.conftest import make_exec_context


class TestEarlyReturn:
    def test_nan_rsi(self, default_algo: RSIAlgo) -> None:
        ctx = make_exec_context(rsi_value=float("nan"), ma_value=10.0, close_price=10.0)
        default_algo(ctx)
        assert ctx.buy_shares == 0
        ctx.sell_all_shares.assert_not_called()

    def test_nan_ma(self, default_algo: RSIAlgo) -> None:
        ctx = make_exec_context(rsi_value=50.0, ma_value=float("nan"), close_price=10.0)
        default_algo(ctx)
        assert ctx.buy_shares == 0
        ctx.sell_all_shares.assert_not_called()


class TestBuy:
    def test_oversold_no_position(self, default_algo: RSIAlgo) -> None:
        ctx = make_exec_context(rsi_value=30.0, ma_value=10.0, close_price=10.0)
        default_algo(ctx)
        assert ctx.buy_shares >= 100
        ctx.sell_all_shares.assert_not_called()

    def test_shares_calculation(self, default_algo: RSIAlgo) -> None:
        # max(int(100000 / 5.0 / 10), 100) = 2000
        ctx = make_exec_context(rsi_value=30.0, ma_value=5.0, close_price=5.0)
        default_algo(ctx)
        assert ctx.buy_shares == 2000

    def test_minimum_100_shares(self, default_algo: RSIAlgo) -> None:
        # int(100000 / 200000 / 10) = 0 -> max(0, 100) = 100
        ctx = make_exec_context(
            rsi_value=30.0,
            ma_value=200_000.0,
            close_price=200_000.0,
        )
        default_algo(ctx)
        assert ctx.buy_shares == 100

    def test_not_oversold(self, default_algo: RSIAlgo) -> None:
        ctx = make_exec_context(rsi_value=50.0, ma_value=10.0, close_price=10.0)
        default_algo(ctx)
        assert ctx.buy_shares == 0

    def test_oversold_but_has_position(self, default_algo: RSIAlgo) -> None:
        ctx = make_exec_context(
            rsi_value=30.0,
            ma_value=10.0,
            close_price=10.0,
            has_position=True,
            entry_price=10.0,
        )
        default_algo(ctx)
        assert ctx.buy_shares == 0


class TestSell:
    def test_overbought_with_position(self, default_algo: RSIAlgo) -> None:
        ctx = make_exec_context(
            rsi_value=70.0,
            ma_value=10.0,
            close_price=10.0,
            has_position=True,
            entry_price=10.0,
        )
        default_algo(ctx)
        ctx.sell_all_shares.assert_called_once()

    def test_overbought_no_position(self, default_algo: RSIAlgo) -> None:
        ctx = make_exec_context(rsi_value=70.0, ma_value=10.0, close_price=10.0)
        default_algo(ctx)
        ctx.sell_all_shares.assert_not_called()

    def test_not_overbought_with_position(self, default_algo: RSIAlgo) -> None:
        ctx = make_exec_context(
            rsi_value=50.0,
            ma_value=10.0,
            close_price=10.0,
            has_position=True,
            entry_price=10.0,
        )
        default_algo(ctx)
        ctx.sell_all_shares.assert_not_called()


class TestStopLoss:
    def test_triggered(self, stop_loss_algo: RSIAlgo) -> None:
        # entry=10.0, close=9.0 -> 10% loss > 5% threshold
        ctx = make_exec_context(
            rsi_value=50.0,
            ma_value=10.0,
            close_price=9.0,
            has_position=True,
            entry_price=10.0,
        )
        stop_loss_algo(ctx)
        ctx.sell_all_shares.assert_called_once()
        assert ctx.buy_shares == 0

    def test_exact_boundary(self, stop_loss_algo: RSIAlgo) -> None:
        # entry=10.0, close=9.5 -> exactly 5% loss, pnl <= -stop_loss_pct
        ctx = make_exec_context(
            rsi_value=50.0,
            ma_value=10.0,
            close_price=9.5,
            has_position=True,
            entry_price=10.0,
        )
        stop_loss_algo(ctx)
        ctx.sell_all_shares.assert_called_once()

    def test_not_triggered(self, stop_loss_algo: RSIAlgo) -> None:
        # entry=10.0, close=9.6 -> 4% loss < 5% threshold
        ctx = make_exec_context(
            rsi_value=50.0,
            ma_value=10.0,
            close_price=9.6,
            has_position=True,
            entry_price=10.0,
        )
        stop_loss_algo(ctx)
        ctx.sell_all_shares.assert_not_called()

    def test_zero_stop_loss_skips_branch(self, default_algo: RSIAlgo) -> None:
        # stop_loss_pct=0.0, large loss but should not trigger sell via stop loss
        ctx = make_exec_context(
            rsi_value=50.0,
            ma_value=10.0,
            close_price=5.0,
            has_position=True,
            entry_price=10.0,
        )
        default_algo(ctx)
        ctx.sell_all_shares.assert_not_called()


class TestCustomThresholds:
    def test_narrower_thresholds(self) -> None:
        algo = RSIAlgo(oversold=30, overbought=70)
        # rsi=33 is NOT < 30, no buy
        ctx = make_exec_context(rsi_value=33.0, ma_value=10.0, close_price=10.0)
        algo(ctx)
        assert ctx.buy_shares == 0

    def test_overbought_boundary(self) -> None:
        algo = RSIAlgo(oversold=30, overbought=70)
        # rsi=68 is NOT > 70
        ctx = make_exec_context(
            rsi_value=68.0,
            ma_value=10.0,
            close_price=10.0,
            has_position=True,
            entry_price=10.0,
        )
        algo(ctx)
        ctx.sell_all_shares.assert_not_called()
