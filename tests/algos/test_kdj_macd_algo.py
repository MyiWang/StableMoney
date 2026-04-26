"""Tests for KDJMacdAlgo trading logic."""

from __future__ import annotations

from stablemoney.algos.kdj_macd_algo import KDJMacdAlgo
from tests.algos.conftest import make_kdj_macd_context


class TestEarlyReturn:
    def test_nan_kdj_k(self, kdj_macd_algo: KDJMacdAlgo) -> None:
        ctx = make_kdj_macd_context(
            kdj_k=[float("nan"), float("nan")],
            kdj_d=[50.0, 50.0],
            macd_dif=0.1,
            macd_dea=0.1,
        )
        kdj_macd_algo(ctx)
        assert ctx.buy_shares == 0
        ctx.sell_all_shares.assert_not_called()

    def test_nan_kdj_d(self, kdj_macd_algo: KDJMacdAlgo) -> None:
        ctx = make_kdj_macd_context(
            kdj_k=[50.0, 50.0],
            kdj_d=[float("nan"), float("nan")],
            macd_dif=0.1,
            macd_dea=0.1,
        )
        kdj_macd_algo(ctx)
        assert ctx.buy_shares == 0
        ctx.sell_all_shares.assert_not_called()

    def test_nan_macd_dif(self, kdj_macd_algo: KDJMacdAlgo) -> None:
        ctx = make_kdj_macd_context(
            kdj_k=[40.0, 60.0],
            kdj_d=[50.0, 50.0],
            macd_dif=float("nan"),
            macd_dea=0.1,
        )
        kdj_macd_algo(ctx)
        assert ctx.buy_shares == 0

    def test_nan_macd_dea(self, kdj_macd_algo: KDJMacdAlgo) -> None:
        ctx = make_kdj_macd_context(
            kdj_k=[40.0, 60.0],
            kdj_d=[50.0, 50.0],
            macd_dif=0.1,
            macd_dea=float("nan"),
        )
        kdj_macd_algo(ctx)
        assert ctx.buy_shares == 0


class TestBuy:
    def test_golden_cross_with_macd_filter(
        self, kdj_macd_algo: KDJMacdAlgo
    ) -> None:
        # K crosses above D, DIF>0, DEA>0
        ctx = make_kdj_macd_context(
            kdj_k=[40.0, 60.0],
            kdj_d=[50.0, 50.0],
            macd_dif=0.5,
            macd_dea=0.3,
            close_price=10.0,
        )
        kdj_macd_algo(ctx)
        assert ctx.buy_shares >= 100
        ctx.sell_all_shares.assert_not_called()

    def test_no_cross_no_buy(self, kdj_macd_algo: KDJMacdAlgo) -> None:
        # K stays above D, no cross
        ctx = make_kdj_macd_context(
            kdj_k=[60.0, 60.0],
            kdj_d=[50.0, 50.0],
            macd_dif=0.5,
            macd_dea=0.3,
        )
        kdj_macd_algo(ctx)
        assert ctx.buy_shares == 0

    def test_death_cross_no_buy(self, kdj_macd_algo: KDJMacdAlgo) -> None:
        # K crosses below D (death cross), no buy
        ctx = make_kdj_macd_context(
            kdj_k=[60.0, 40.0],
            kdj_d=[50.0, 50.0],
            macd_dif=0.5,
            macd_dea=0.3,
        )
        kdj_macd_algo(ctx)
        assert ctx.buy_shares == 0

    def test_golden_cross_but_dif_negative(
        self, kdj_macd_algo: KDJMacdAlgo
    ) -> None:
        # Golden cross but DIF<0, no buy
        ctx = make_kdj_macd_context(
            kdj_k=[40.0, 60.0],
            kdj_d=[50.0, 50.0],
            macd_dif=-0.1,
            macd_dea=0.3,
        )
        kdj_macd_algo(ctx)
        assert ctx.buy_shares == 0

    def test_golden_cross_but_dea_negative(
        self, kdj_macd_algo: KDJMacdAlgo
    ) -> None:
        # Golden cross but DEA<0, no buy
        ctx = make_kdj_macd_context(
            kdj_k=[40.0, 60.0],
            kdj_d=[50.0, 50.0],
            macd_dif=0.5,
            macd_dea=-0.1,
        )
        kdj_macd_algo(ctx)
        assert ctx.buy_shares == 0

    def test_golden_cross_but_dif_zero(
        self, kdj_macd_algo: KDJMacdAlgo
    ) -> None:
        # DIF=0 is not >0, no buy
        ctx = make_kdj_macd_context(
            kdj_k=[40.0, 60.0],
            kdj_d=[50.0, 50.0],
            macd_dif=0.0,
            macd_dea=0.3,
        )
        kdj_macd_algo(ctx)
        assert ctx.buy_shares == 0

    def test_has_position_no_buy(self, kdj_macd_algo: KDJMacdAlgo) -> None:
        ctx = make_kdj_macd_context(
            kdj_k=[40.0, 60.0],
            kdj_d=[50.0, 50.0],
            macd_dif=0.5,
            macd_dea=0.3,
            has_position=True,
            entry_price=10.0,
        )
        kdj_macd_algo(ctx)
        assert ctx.buy_shares == 0


class TestSell:
    def test_death_cross_with_position(
        self, kdj_macd_algo: KDJMacdAlgo
    ) -> None:
        # K crosses below D while holding
        ctx = make_kdj_macd_context(
            kdj_k=[60.0, 40.0],
            kdj_d=[50.0, 50.0],
            macd_dif=0.5,
            macd_dea=0.3,
            has_position=True,
            entry_price=10.0,
        )
        kdj_macd_algo(ctx)
        ctx.sell_all_shares.assert_called_once()
        assert ctx.buy_shares == 0

    def test_death_cross_no_position(
        self, kdj_macd_algo: KDJMacdAlgo
    ) -> None:
        ctx = make_kdj_macd_context(
            kdj_k=[60.0, 40.0],
            kdj_d=[50.0, 50.0],
            macd_dif=0.5,
            macd_dea=0.3,
        )
        kdj_macd_algo(ctx)
        ctx.sell_all_shares.assert_not_called()

    def test_no_cross_with_position(
        self, kdj_macd_algo: KDJMacdAlgo
    ) -> None:
        # K stays above D, no sell
        ctx = make_kdj_macd_context(
            kdj_k=[60.0, 60.0],
            kdj_d=[50.0, 50.0],
            macd_dif=0.5,
            macd_dea=0.3,
            has_position=True,
            entry_price=10.0,
        )
        kdj_macd_algo(ctx)
        ctx.sell_all_shares.assert_not_called()

    def test_sell_ignores_macd(self, kdj_macd_algo: KDJMacdAlgo) -> None:
        # Death cross sells even with negative MACD
        ctx = make_kdj_macd_context(
            kdj_k=[60.0, 40.0],
            kdj_d=[50.0, 50.0],
            macd_dif=-0.5,
            macd_dea=-0.3,
            has_position=True,
            entry_price=10.0,
        )
        kdj_macd_algo(ctx)
        ctx.sell_all_shares.assert_called_once()
