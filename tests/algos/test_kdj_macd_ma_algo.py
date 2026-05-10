"""Tests for KdjMacdMaAlgo."""

from __future__ import annotations

from unittest.mock import MagicMock

import numpy as np

from stablemoney.algos.algo_config import AlgoConfig
from stablemoney.algos.kdj_macd_ma_algo import KdjMacdMaAlgo


def make_kdj_macd_ma_context(
    *,
    j_curr: float = -5.0,
    dif: float = 0.5,
    dea: float = 0.3,
    ma10: float = 11.0,
    ma20: float = 10.0,
    close: float = 10.5,
    has_position: bool = False,
) -> MagicMock:
    ctx = MagicMock()
    ctx.KDJ_J = np.array([j_curr])
    ctx.MACD_DIF = np.array([dif])
    ctx.MACD_DEA = np.array([dea])
    ctx.MA_10 = np.array([ma10])
    ctx.MA_20 = np.array([ma20])
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


class TestKdjMacdMaAlgo:
    def test_buy_when_all_signals_met(self) -> None:
        ctx = make_kdj_macd_ma_context(
            j_curr=-5.0, dif=0.5, dea=0.3, ma10=11.0, ma20=10.0,
        )
        algo = KdjMacdMaAlgo()
        algo.trade(ctx)
        assert ctx.buy_shares > 0

    def test_no_buy_when_j_positive(self) -> None:
        ctx = make_kdj_macd_ma_context(j_curr=5.0)
        algo = KdjMacdMaAlgo()
        algo.trade(ctx)
        assert ctx.buy_shares == 0

    def test_no_buy_when_dif_negative(self) -> None:
        ctx = make_kdj_macd_ma_context(dif=-0.5)
        algo = KdjMacdMaAlgo()
        algo.trade(ctx)
        assert ctx.buy_shares == 0

    def test_no_buy_when_dea_negative(self) -> None:
        ctx = make_kdj_macd_ma_context(dea=-0.3)
        algo = KdjMacdMaAlgo()
        algo.trade(ctx)
        assert ctx.buy_shares == 0

    def test_no_buy_when_ma_bearish(self) -> None:
        ctx = make_kdj_macd_ma_context(ma10=9.0, ma20=10.0)
        algo = KdjMacdMaAlgo()
        algo.trade(ctx)
        assert ctx.buy_shares == 0

    def test_no_buy_with_existing_position(self) -> None:
        ctx = make_kdj_macd_ma_context(has_position=True)
        algo = KdjMacdMaAlgo()
        algo.trade(ctx)
        assert ctx.buy_shares == 0

    def test_no_action_on_nan(self) -> None:
        ctx = make_kdj_macd_ma_context()
        ctx.KDJ_J = np.array([float("nan")])
        algo = KdjMacdMaAlgo()
        algo.trade(ctx)
        assert ctx.buy_shares == 0

    def test_stop_loss_applied(self) -> None:
        ctx = make_kdj_macd_ma_context()
        algo = KdjMacdMaAlgo(config=AlgoConfig(stop_loss_pct=5.0))
        algo.trade(ctx)
        assert ctx.stop_loss_pct == 5.0
