"""Tests for MacdAlgo trading logic."""
from __future__ import annotations

from stablemoney.algos.macd_algo import MacdAlgo
from tests.algos.conftest import make_macd_context


class TestEarlyReturn:
    def test_nan_dif(self, macd_algo: MacdAlgo) -> None:
        ctx = make_macd_context(
            macd_dif=[float("nan"), float("nan")],
            macd_dea=[0.1, 0.1],
        )
        macd_algo(ctx)
        assert ctx.buy_shares == 0
        ctx.sell_all_shares.assert_not_called()

    def test_nan_dea(self, macd_algo: MacdAlgo) -> None:
        ctx = make_macd_context(
            macd_dif=[0.1, 0.1],
            macd_dea=[float("nan"), float("nan")],
        )
        macd_algo(ctx)
        assert ctx.buy_shares == 0
        ctx.sell_all_shares.assert_not_called()


class TestBuy:
    def test_golden_cross(self, macd_algo: MacdAlgo) -> None:
        ctx = make_macd_context(
            macd_dif=[-0.1, 0.2],
            macd_dea=[0.1, 0.1],
            close_price=10.0,
        )
        macd_algo(ctx)
        assert ctx.buy_shares >= 100
        ctx.sell_all_shares.assert_not_called()

    def test_no_cross_no_buy(self, macd_algo: MacdAlgo) -> None:
        # DIF stays above DEA, no cross
        ctx = make_macd_context(
            macd_dif=[0.2, 0.2],
            macd_dea=[0.1, 0.1],
        )
        macd_algo(ctx)
        assert ctx.buy_shares == 0

    def test_death_cross_no_buy(self, macd_algo: MacdAlgo) -> None:
        # DIF crosses below DEA, no buy
        ctx = make_macd_context(
            macd_dif=[0.2, -0.1],
            macd_dea=[0.1, 0.1],
        )
        macd_algo(ctx)
        assert ctx.buy_shares == 0

    def test_has_position_no_buy(self, macd_algo: MacdAlgo) -> None:
        ctx = make_macd_context(
            macd_dif=[-0.1, 0.2],
            macd_dea=[0.1, 0.1],
            has_position=True,
            entry_price=10.0,
        )
        macd_algo(ctx)
        assert ctx.buy_shares == 0

    def test_golden_cross_but_dif_negative(
        self, macd_algo: MacdAlgo,
    ) -> None:
        # Golden cross but DIF < 0, no buy
        ctx = make_macd_context(
            macd_dif=[-0.3, -0.1],
            macd_dea=[-0.2, -0.15],
        )
        macd_algo(ctx)
        assert ctx.buy_shares == 0

    def test_golden_cross_but_dea_negative(
        self, macd_algo: MacdAlgo,
    ) -> None:
        # Golden cross but DEA < 0, no buy
        ctx = make_macd_context(
            macd_dif=[-0.3, 0.1],
            macd_dea=[-0.2, -0.1],
        )
        macd_algo(ctx)
        assert ctx.buy_shares == 0

    def test_golden_cross_applies_risk(
        self, macd_algo_with_risk: MacdAlgo,
    ) -> None:
        ctx = make_macd_context(
            macd_dif=[-0.1, 0.2],
            macd_dea=[0.1, 0.1],
            close_price=10.0,
        )
        macd_algo_with_risk(ctx)
        assert ctx.buy_shares >= 100
        assert ctx.stop_loss_pct == 3
        assert ctx.stop_profit_pct == 10
        assert ctx.hold_bars == 20


class TestSell:
    def test_death_cross_with_position(
        self, macd_algo: MacdAlgo,
    ) -> None:
        ctx = make_macd_context(
            macd_dif=[0.2, -0.1],
            macd_dea=[0.1, 0.1],
            has_position=True,
            entry_price=10.0,
        )
        macd_algo(ctx)
        ctx.sell_all_shares.assert_called_once()
        assert ctx.buy_shares == 0

    def test_death_cross_no_position(
        self, macd_algo: MacdAlgo,
    ) -> None:
        ctx = make_macd_context(
            macd_dif=[0.2, -0.1],
            macd_dea=[0.1, 0.1],
        )
        macd_algo(ctx)
        ctx.sell_all_shares.assert_not_called()

    def test_no_cross_with_position(
        self, macd_algo: MacdAlgo,
    ) -> None:
        # DIF stays above DEA, no sell
        ctx = make_macd_context(
            macd_dif=[0.2, 0.2],
            macd_dea=[0.1, 0.1],
            has_position=True,
            entry_price=10.0,
        )
        macd_algo(ctx)
        ctx.sell_all_shares.assert_not_called()

    def test_golden_cross_no_sell(
        self, macd_algo: MacdAlgo,
    ) -> None:
        # Golden cross while holding — should not sell
        ctx = make_macd_context(
            macd_dif=[-0.1, 0.2],
            macd_dea=[0.1, 0.1],
            has_position=True,
            entry_price=10.0,
        )
        macd_algo(ctx)
        ctx.sell_all_shares.assert_not_called()
