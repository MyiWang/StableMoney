"""Tests for MACrossAlgo trading logic."""
from __future__ import annotations

from stablemoney.algos.ma_cross_algo import MACrossAlgo
from tests.algos.conftest import make_ma_cross_context


class TestEarlyReturn:
    def test_nan_ma_short(self, ma_cross_algo: MACrossAlgo) -> None:
        ctx = make_ma_cross_context(
            ma_short=[float("nan"), float("nan")],
            ma_long=[10.0, 10.0],
        )
        ma_cross_algo(ctx)
        assert ctx.buy_shares == 0
        ctx.sell_all_shares.assert_not_called()

    def test_nan_ma_long(self, ma_cross_algo: MACrossAlgo) -> None:
        ctx = make_ma_cross_context(
            ma_short=[10.0, 10.0],
            ma_long=[float("nan"), float("nan")],
        )
        ma_cross_algo(ctx)
        assert ctx.buy_shares == 0
        ctx.sell_all_shares.assert_not_called()


class TestBuy:
    def test_golden_cross(self, ma_cross_algo: MACrossAlgo) -> None:
        ctx = make_ma_cross_context(
            ma_short=[9.0, 11.0],
            ma_long=[10.0, 10.0],
            close_price=10.0,
        )
        ma_cross_algo(ctx)
        assert ctx.buy_shares >= 100
        ctx.sell_all_shares.assert_not_called()

    def test_no_cross_no_buy(self, ma_cross_algo: MACrossAlgo) -> None:
        ctx = make_ma_cross_context(
            ma_short=[11.0, 11.0],
            ma_long=[10.0, 10.0],
        )
        ma_cross_algo(ctx)
        assert ctx.buy_shares == 0

    def test_death_cross_no_buy(self, ma_cross_algo: MACrossAlgo) -> None:
        ctx = make_ma_cross_context(
            ma_short=[11.0, 9.0],
            ma_long=[10.0, 10.0],
        )
        ma_cross_algo(ctx)
        assert ctx.buy_shares == 0

    def test_has_position_no_buy(self, ma_cross_algo: MACrossAlgo) -> None:
        ctx = make_ma_cross_context(
            ma_short=[9.0, 11.0],
            ma_long=[10.0, 10.0],
            has_position=True,
            entry_price=10.0,
        )
        ma_cross_algo(ctx)
        assert ctx.buy_shares == 0

    def test_golden_cross_applies_risk(
        self, ma_cross_algo_with_risk: MACrossAlgo,
    ) -> None:
        ctx = make_ma_cross_context(
            ma_short=[9.0, 11.0],
            ma_long=[10.0, 10.0],
            close_price=10.0,
        )
        ma_cross_algo_with_risk(ctx)
        assert ctx.buy_shares >= 100
        assert ctx.stop_loss_pct == 3
        assert ctx.stop_profit_pct == 10
        assert ctx.hold_bars == 20


class TestSell:
    def test_death_cross_with_position(
        self, ma_cross_algo: MACrossAlgo,
    ) -> None:
        ctx = make_ma_cross_context(
            ma_short=[11.0, 9.0],
            ma_long=[10.0, 10.0],
            has_position=True,
            entry_price=10.0,
        )
        ma_cross_algo(ctx)
        ctx.sell_all_shares.assert_called_once()
        assert ctx.buy_shares == 0

    def test_death_cross_no_position(
        self, ma_cross_algo: MACrossAlgo,
    ) -> None:
        ctx = make_ma_cross_context(
            ma_short=[11.0, 9.0],
            ma_long=[10.0, 10.0],
        )
        ma_cross_algo(ctx)
        ctx.sell_all_shares.assert_not_called()

    def test_no_cross_with_position(
        self, ma_cross_algo: MACrossAlgo,
    ) -> None:
        ctx = make_ma_cross_context(
            ma_short=[11.0, 11.0],
            ma_long=[10.0, 10.0],
            has_position=True,
            entry_price=10.0,
        )
        ma_cross_algo(ctx)
        ctx.sell_all_shares.assert_not_called()

    def test_golden_cross_no_sell(
        self, ma_cross_algo: MACrossAlgo,
    ) -> None:
        ctx = make_ma_cross_context(
            ma_short=[9.0, 11.0],
            ma_long=[10.0, 10.0],
            has_position=True,
            entry_price=10.0,
        )
        ma_cross_algo(ctx)
        ctx.sell_all_shares.assert_not_called()
