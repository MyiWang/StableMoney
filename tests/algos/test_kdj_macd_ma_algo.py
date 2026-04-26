"""Tests for KdjMacdMaAlgo trading logic."""

from __future__ import annotations

from stablemoney.algos.algo_config import AlgoConfig
from stablemoney.algos.kdj_macd_ma_algo import KdjMacdMaAlgo
from tests.algos.conftest import make_kdj_macd_ma_context


class TestEarlyReturn:
    def test_nan_kdj_j(self) -> None:
        ctx = make_kdj_macd_ma_context(
            kdj_j=float("nan"),
            macd_dif=0.1,
            macd_dea=0.1,
            ma_short=20.0,
            ma_long=15.0,
        )
        KdjMacdMaAlgo()(ctx)
        assert ctx.buy_shares == 0
        ctx.sell_all_shares.assert_not_called()

    def test_nan_macd_dif(self) -> None:
        ctx = make_kdj_macd_ma_context(
            kdj_j=-5.0,
            macd_dif=float("nan"),
            macd_dea=0.1,
            ma_short=20.0,
            ma_long=15.0,
        )
        KdjMacdMaAlgo()(ctx)
        assert ctx.buy_shares == 0

    def test_nan_macd_dea(self) -> None:
        ctx = make_kdj_macd_ma_context(
            kdj_j=-5.0,
            macd_dif=0.1,
            macd_dea=float("nan"),
            ma_short=20.0,
            ma_long=15.0,
        )
        KdjMacdMaAlgo()(ctx)
        assert ctx.buy_shares == 0

    def test_nan_ma_short(self) -> None:
        ctx = make_kdj_macd_ma_context(
            kdj_j=-5.0,
            macd_dif=0.1,
            macd_dea=0.1,
            ma_short=float("nan"),
            ma_long=15.0,
        )
        KdjMacdMaAlgo()(ctx)
        assert ctx.buy_shares == 0

    def test_nan_ma_long(self) -> None:
        ctx = make_kdj_macd_ma_context(
            kdj_j=-5.0,
            macd_dif=0.1,
            macd_dea=0.1,
            ma_short=20.0,
            ma_long=float("nan"),
        )
        KdjMacdMaAlgo()(ctx)
        assert ctx.buy_shares == 0


class TestBuy:
    def test_all_conditions_met(self) -> None:
        ctx = make_kdj_macd_ma_context(
            kdj_j=-5.0,
            macd_dif=0.5,
            macd_dea=0.3,
            ma_short=20.0,
            ma_long=15.0,
            close_price=10.0,
        )
        KdjMacdMaAlgo()(ctx)
        assert ctx.buy_shares == 10000
        ctx.sell_all_shares.assert_not_called()

    def test_j_not_negative(self) -> None:
        ctx = make_kdj_macd_ma_context(
            kdj_j=5.0,
            macd_dif=0.5,
            macd_dea=0.3,
            ma_short=20.0,
            ma_long=15.0,
        )
        KdjMacdMaAlgo()(ctx)
        assert ctx.buy_shares == 0

    def test_j_zero_no_buy(self) -> None:
        ctx = make_kdj_macd_ma_context(
            kdj_j=0.0,
            macd_dif=0.5,
            macd_dea=0.3,
            ma_short=20.0,
            ma_long=15.0,
        )
        KdjMacdMaAlgo()(ctx)
        assert ctx.buy_shares == 0

    def test_dif_negative(self) -> None:
        ctx = make_kdj_macd_ma_context(
            kdj_j=-5.0,
            macd_dif=-0.1,
            macd_dea=0.3,
            ma_short=20.0,
            ma_long=15.0,
        )
        KdjMacdMaAlgo()(ctx)
        assert ctx.buy_shares == 0

    def test_dea_negative(self) -> None:
        ctx = make_kdj_macd_ma_context(
            kdj_j=-5.0,
            macd_dif=0.5,
            macd_dea=-0.1,
            ma_short=20.0,
            ma_long=15.0,
        )
        KdjMacdMaAlgo()(ctx)
        assert ctx.buy_shares == 0

    def test_ma_bearish(self) -> None:
        ctx = make_kdj_macd_ma_context(
            kdj_j=-5.0,
            macd_dif=0.5,
            macd_dea=0.3,
            ma_short=15.0,
            ma_long=20.0,
        )
        KdjMacdMaAlgo()(ctx)
        assert ctx.buy_shares == 0

    def test_ma_equal_no_buy(self) -> None:
        ctx = make_kdj_macd_ma_context(
            kdj_j=-5.0,
            macd_dif=0.5,
            macd_dea=0.3,
            ma_short=20.0,
            ma_long=20.0,
        )
        KdjMacdMaAlgo()(ctx)
        assert ctx.buy_shares == 0

    def test_has_position_no_buy(self) -> None:
        ctx = make_kdj_macd_ma_context(
            kdj_j=-5.0,
            macd_dif=0.5,
            macd_dea=0.3,
            ma_short=20.0,
            ma_long=15.0,
            has_position=True,
            entry_price=10.0,
        )
        KdjMacdMaAlgo()(ctx)
        assert ctx.buy_shares == 0

    def test_buy_applies_risk(self) -> None:
        ctx = make_kdj_macd_ma_context(
            kdj_j=-5.0,
            macd_dif=0.5,
            macd_dea=0.3,
            ma_short=20.0,
            ma_long=15.0,
            close_price=10.0,
        )
        algo = KdjMacdMaAlgo(
            config=AlgoConfig(stop_loss_pct=5, take_profit_pct=20, hold_bars=40),
        )
        algo(ctx)
        assert ctx.buy_shares == 10000
        assert ctx.stop_loss_pct == 5
        assert ctx.stop_profit_pct == 20
        assert ctx.hold_bars == 40

    def test_shares_minimum_100(self) -> None:
        ctx = make_kdj_macd_ma_context(
            kdj_j=-5.0,
            macd_dif=0.5,
            macd_dea=0.3,
            ma_short=20.0,
            ma_long=15.0,
            close_price=500.0,
            initial_cash=1000,
        )
        KdjMacdMaAlgo()(ctx)
        assert ctx.buy_shares == 100


class TestSell:
    def test_no_active_sell_with_position(self) -> None:
        ctx = make_kdj_macd_ma_context(
            kdj_j=-5.0,
            macd_dif=0.5,
            macd_dea=0.3,
            ma_short=20.0,
            ma_long=15.0,
            has_position=True,
            entry_price=10.0,
        )
        KdjMacdMaAlgo()(ctx)
        ctx.sell_all_shares.assert_not_called()
