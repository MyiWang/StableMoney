"""Tests for KDJMacdAlgo trading logic."""

from __future__ import annotations

from typing import TYPE_CHECKING

from tests.algos.conftest import make_kdj_macd_context

if TYPE_CHECKING:
    from stablemoney.algos.kdj_macd_algo import KDJMacdAlgo

# Default test values: all buy conditions met
# J[-2]=-10 (<0), J[-1]=-15 (<J[-2]), DIF=0.5 (>0), DEA=0.3 (>0)
# close=15 (>MA60=12), close=15 (<MA20=16)
_J_BUY = [-10.0, -15.0]
_DIF_BUY = 0.5
_DEA_BUY = 0.3
_MA20_BUY = 16.0
_MA60_BUY = 12.0
_CLOSE_BUY = 15.0


class TestEarlyReturn:
    def test_nan_kdj_j(self, kdj_macd_algo: KDJMacdAlgo) -> None:
        ctx = make_kdj_macd_context(
            kdj_j=[float("nan"), float("nan")],
            macd_dif=_DIF_BUY,
            macd_dea=_DEA_BUY,
            ma_20=_MA20_BUY,
            ma_60=_MA60_BUY,
        )
        kdj_macd_algo(ctx)
        assert ctx.buy_shares == 0
        ctx.sell_all_shares.assert_not_called()

    def test_nan_macd_dif(self, kdj_macd_algo: KDJMacdAlgo) -> None:
        ctx = make_kdj_macd_context(
            kdj_j=_J_BUY,
            macd_dif=float("nan"),
            macd_dea=_DEA_BUY,
            ma_20=_MA20_BUY,
            ma_60=_MA60_BUY,
        )
        kdj_macd_algo(ctx)
        assert ctx.buy_shares == 0

    def test_nan_macd_dea(self, kdj_macd_algo: KDJMacdAlgo) -> None:
        ctx = make_kdj_macd_context(
            kdj_j=_J_BUY,
            macd_dif=_DIF_BUY,
            macd_dea=float("nan"),
            ma_20=_MA20_BUY,
            ma_60=_MA60_BUY,
        )
        kdj_macd_algo(ctx)
        assert ctx.buy_shares == 0

    def test_nan_ma20(self, kdj_macd_algo: KDJMacdAlgo) -> None:
        ctx = make_kdj_macd_context(
            kdj_j=_J_BUY,
            macd_dif=_DIF_BUY,
            macd_dea=_DEA_BUY,
            ma_20=float("nan"),
            ma_60=_MA60_BUY,
        )
        kdj_macd_algo(ctx)
        assert ctx.buy_shares == 0

    def test_nan_ma60(self, kdj_macd_algo: KDJMacdAlgo) -> None:
        ctx = make_kdj_macd_context(
            kdj_j=_J_BUY,
            macd_dif=_DIF_BUY,
            macd_dea=_DEA_BUY,
            ma_20=_MA20_BUY,
            ma_60=float("nan"),
        )
        kdj_macd_algo(ctx)
        assert ctx.buy_shares == 0


class TestBuy:
    def test_all_conditions_met_buy(self, kdj_macd_algo: KDJMacdAlgo) -> None:
        ctx = make_kdj_macd_context(
            kdj_j=_J_BUY,
            macd_dif=_DIF_BUY,
            macd_dea=_DEA_BUY,
            ma_20=_MA20_BUY,
            ma_60=_MA60_BUY,
            close_price=_CLOSE_BUY,
        )
        kdj_macd_algo(ctx)
        assert ctx.buy_shares >= 100
        ctx.sell_all_shares.assert_not_called()

    def test_j_prev_positive_no_buy(self, kdj_macd_algo: KDJMacdAlgo) -> None:
        # J[-2] > 0, condition J[-2] < 0 not met
        ctx = make_kdj_macd_context(
            kdj_j=[5.0, -15.0],
            macd_dif=_DIF_BUY,
            macd_dea=_DEA_BUY,
            ma_20=_MA20_BUY,
            ma_60=_MA60_BUY,
            close_price=_CLOSE_BUY,
        )
        kdj_macd_algo(ctx)
        assert ctx.buy_shares == 0

    def test_j_rising_no_buy(self, kdj_macd_algo: KDJMacdAlgo) -> None:
        # J[-1] > J[-2], condition J[-1] < J[-2] not met
        ctx = make_kdj_macd_context(
            kdj_j=[-15.0, -10.0],
            macd_dif=_DIF_BUY,
            macd_dea=_DEA_BUY,
            ma_20=_MA20_BUY,
            ma_60=_MA60_BUY,
            close_price=_CLOSE_BUY,
        )
        kdj_macd_algo(ctx)
        assert ctx.buy_shares == 0

    def test_dif_negative_no_buy(self, kdj_macd_algo: KDJMacdAlgo) -> None:
        ctx = make_kdj_macd_context(
            kdj_j=_J_BUY,
            macd_dif=-0.5,
            macd_dea=_DEA_BUY,
            ma_20=_MA20_BUY,
            ma_60=_MA60_BUY,
            close_price=_CLOSE_BUY,
        )
        kdj_macd_algo(ctx)
        assert ctx.buy_shares == 0

    def test_dea_negative_no_buy(self, kdj_macd_algo: KDJMacdAlgo) -> None:
        ctx = make_kdj_macd_context(
            kdj_j=_J_BUY,
            macd_dif=_DIF_BUY,
            macd_dea=-0.3,
            ma_20=_MA20_BUY,
            ma_60=_MA60_BUY,
            close_price=_CLOSE_BUY,
        )
        kdj_macd_algo(ctx)
        assert ctx.buy_shares == 0

    def test_close_below_ma60_no_buy(self, kdj_macd_algo: KDJMacdAlgo) -> None:
        # close=10 < MA60=12, condition close > MA60 not met
        ctx = make_kdj_macd_context(
            kdj_j=_J_BUY,
            macd_dif=_DIF_BUY,
            macd_dea=_DEA_BUY,
            ma_20=_MA20_BUY,
            ma_60=_MA60_BUY,
            close_price=10.0,
        )
        kdj_macd_algo(ctx)
        assert ctx.buy_shares == 0

    def test_close_above_ma20_no_buy(self, kdj_macd_algo: KDJMacdAlgo) -> None:
        # close=17 > MA20=16, condition close < MA20 not met
        ctx = make_kdj_macd_context(
            kdj_j=_J_BUY,
            macd_dif=_DIF_BUY,
            macd_dea=_DEA_BUY,
            ma_20=_MA20_BUY,
            ma_60=_MA60_BUY,
            close_price=17.0,
        )
        kdj_macd_algo(ctx)
        assert ctx.buy_shares == 0

    def test_has_position_no_buy(self, kdj_macd_algo: KDJMacdAlgo) -> None:
        ctx = make_kdj_macd_context(
            kdj_j=_J_BUY,
            macd_dif=_DIF_BUY,
            macd_dea=_DEA_BUY,
            ma_20=_MA20_BUY,
            ma_60=_MA60_BUY,
            close_price=_CLOSE_BUY,
            has_position=True,
            entry_price=14.0,
        )
        kdj_macd_algo(ctx)
        assert ctx.buy_shares == 0
