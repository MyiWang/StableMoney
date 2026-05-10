"""Tests for KDJMacdAlgo."""

from __future__ import annotations

from unittest.mock import MagicMock

import numpy as np

from stablemoney.algos.algo_config import AlgoConfig
from stablemoney.algos.kdj_macd_algo import KDJMacdAlgo


def make_kdj_macd_context(
    *,
    j_prev: float = -5.0,
    j_curr: float = -10.0,
    dif: float = 0.5,
    dea: float = 0.3,
    close: float = 15.0,
    ma20: float = 16.0,
    ma60: float = 14.0,
    has_position: bool = False,
) -> MagicMock:
    ctx = MagicMock()
    ctx.KDJ_J = np.array([j_prev, j_curr])
    ctx.MACD_DIF = np.array([dif])
    ctx.MACD_DEA = np.array([dea])
    ctx.MA_20 = np.array([ma20])
    ctx.MA_60 = np.array([ma60])
    ctx.close = np.array([close])
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


class TestKDJMacdAlgo:
    def test_buy_when_all_conditions_met(self) -> None:
        ctx = make_kdj_macd_context(
            j_prev=-5.0, j_curr=-10.0,
            dif=0.5, dea=0.3,
            close=15.0, ma20=16.0, ma60=14.0,
        )
        algo = KDJMacdAlgo()
        algo.trade(ctx)
        assert ctx.buy_shares > 0

    def test_no_buy_when_j_not_declining(self) -> None:
        ctx = make_kdj_macd_context(
            j_prev=-10.0, j_curr=-5.0,
        )
        algo = KDJMacdAlgo()
        algo.trade(ctx)
        assert ctx.buy_shares == 0

    def test_no_buy_when_j_prev_not_below_zero(self) -> None:
        ctx = make_kdj_macd_context(
            j_prev=2.0, j_curr=-1.0,
        )
        algo = KDJMacdAlgo()
        algo.trade(ctx)
        assert ctx.buy_shares == 0

    def test_no_buy_when_dif_negative(self) -> None:
        ctx = make_kdj_macd_context(dif=-0.5)
        algo = KDJMacdAlgo()
        algo.trade(ctx)
        assert ctx.buy_shares == 0

    def test_no_buy_when_close_above_ma20(self) -> None:
        ctx = make_kdj_macd_context(close=17.0, ma20=16.0)
        algo = KDJMacdAlgo()
        algo.trade(ctx)
        assert ctx.buy_shares == 0

    def test_no_buy_when_close_below_ma60(self) -> None:
        ctx = make_kdj_macd_context(close=13.0, ma60=14.0)
        algo = KDJMacdAlgo()
        algo.trade(ctx)
        assert ctx.buy_shares == 0

    def test_no_buy_with_existing_position(self) -> None:
        ctx = make_kdj_macd_context(has_position=True)
        algo = KDJMacdAlgo()
        algo.trade(ctx)
        assert ctx.buy_shares == 0

    def test_no_action_on_nan(self) -> None:
        ctx = make_kdj_macd_context()
        ctx.KDJ_J = np.array([-5.0, float("nan")])
        algo = KDJMacdAlgo()
        algo.trade(ctx)
        assert ctx.buy_shares == 0

    def test_stop_loss_applied(self) -> None:
        ctx = make_kdj_macd_context()
        algo = KDJMacdAlgo(config=AlgoConfig(stop_loss_pct=5.0))
        algo.trade(ctx)
        assert ctx.stop_loss_pct == 5.0
