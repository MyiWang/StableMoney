"""Tests for KdjZxtrendAlgo."""

from __future__ import annotations

from unittest.mock import MagicMock

import numpy as np

from stablemoney.algos.algo_config import AlgoConfig
from stablemoney.algos.kdj_zxtrend_algo import KdjZxtrendAlgo


def make_context(
    *,
    kdj_j: np.ndarray | None = None,
    short_t: np.ndarray | None = None,
    long_t: np.ndarray | None = None,
    close: float = 15.0,
    has_position: bool = False,
) -> MagicMock:
    """Build a mock ExecContext with ZXTREND golden cross at bar -2."""
    if kdj_j is None:
        kdj_j = np.array([10.0, -5.0])
    if short_t is None:
        # Golden cross at bar -1: short crosses above long
        short_t = np.array([90.0, 95.0, 100.0, 105.0, 110.0])
    if long_t is None:
        long_t = np.array([95.0, 98.0, 96.0, 100.0, 102.0])

    ctx = MagicMock()
    ctx.KDJ_J = kdj_j
    ctx.ZXTREND_SHORT_T = short_t
    ctx.ZXTREND_LONG_T = long_t
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


class TestKdjZxtrendAlgo:
    def test_buy_when_golden_cross_and_j_below_zero(self) -> None:
        """Buy when ZXTREND golden cross within lookback and J < 0."""
        # short[-3]=95 < long[-3]=98, short[-2]=100 > long[-2]=96 → golden cross
        ctx = make_context(
            kdj_j=np.array([10.0, -5.0]),
            short_t=np.array([90.0, 95.0, 100.0, 105.0, 110.0]),
            long_t=np.array([95.0, 98.0, 96.0, 100.0, 102.0]),
        )
        algo = KdjZxtrendAlgo()
        algo(ctx)
        assert ctx.buy_shares > 0

    def test_no_buy_when_j_above_zero(self) -> None:
        ctx = make_context(
            kdj_j=np.array([5.0, 10.0]),
        )
        algo = KdjZxtrendAlgo()
        algo(ctx)
        assert ctx.buy_shares == 0

    def test_no_buy_when_no_golden_cross(self) -> None:
        """short always above long → no cross → no buy."""
        ctx = make_context(
            kdj_j=np.array([10.0, -5.0]),
            short_t=np.array([100.0, 105.0, 110.0, 115.0, 120.0]),
            long_t=np.array([90.0, 92.0, 94.0, 96.0, 98.0]),
        )
        algo = KdjZxtrendAlgo()
        algo(ctx)
        assert ctx.buy_shares == 0

    def test_no_buy_when_golden_cross_too_old(self) -> None:
        """Golden cross beyond lookback window → no buy."""
        # 35 bars: golden cross at bar 0 (too old for lookback=30)
        short_t = np.full(36, 100.0)
        long_t = np.full(36, 100.0)
        # Golden cross at bar index 0 (35 bars ago)
        short_t[0] = 90.0
        long_t[0] = 95.0
        short_t[1] = 105.0
        long_t[1] = 95.0
        ctx = make_context(
            kdj_j=np.array([10.0, -5.0]),
            short_t=short_t,
            long_t=long_t,
        )
        algo = KdjZxtrendAlgo(lookback=30)
        algo(ctx)
        assert ctx.buy_shares == 0

    def test_no_buy_with_existing_position(self) -> None:
        ctx = make_context(has_position=True)
        algo = KdjZxtrendAlgo()
        algo(ctx)
        assert ctx.buy_shares == 0

    def test_no_action_on_nan(self) -> None:
        ctx = make_context()
        ctx.KDJ_J = np.array([10.0, float("nan")])
        algo = KdjZxtrendAlgo()
        algo(ctx)
        assert ctx.buy_shares == 0

    def test_stop_loss_applied(self) -> None:
        ctx = make_context()
        algo = KdjZxtrendAlgo(config=AlgoConfig(stop_loss_pct=5.0))
        algo(ctx)
        assert ctx.stop_loss_pct == 5.0

    def test_take_profit_applied(self) -> None:
        ctx = make_context()
        algo = KdjZxtrendAlgo(config=AlgoConfig(take_profit_pct=15.0))
        algo(ctx)
        assert ctx.stop_profit_pct == 15.0

    def test_hold_bars_applied(self) -> None:
        ctx = make_context()
        algo = KdjZxtrendAlgo(config=AlgoConfig(hold_bars=40))
        algo(ctx)
        assert ctx.hold_bars == 40

    def test_sell_on_death_cross(self) -> None:
        """Sell all shares when SHORT_T drops below LONG_T (death cross)."""
        # short[-2]=100 > long[-2]=98, short[-1]=90 < long[-1]=95 → death cross
        ctx = make_context(
            has_position=True,
            short_t=np.array([110.0, 105.0, 100.0, 90.0]),
            long_t=np.array([100.0, 102.0, 98.0, 95.0]),
        )
        algo = KdjZxtrendAlgo()
        algo(ctx)
        ctx.sell_all_shares.assert_called_once()

    def test_no_sell_without_death_cross(self) -> None:
        """No sell when SHORT_T stays above LONG_T."""
        ctx = make_context(
            has_position=True,
            short_t=np.array([100.0, 105.0, 110.0, 115.0]),
            long_t=np.array([90.0, 92.0, 94.0, 96.0]),
        )
        algo = KdjZxtrendAlgo()
        algo(ctx)
        ctx.sell_all_shares.assert_not_called()

    def test_golden_cross_at_edge_of_lookback(self) -> None:
        """Golden cross exactly at lookback boundary → should still buy."""
        # 31 bars total, golden cross at bar index 1 (30 bars ago)
        short_t = np.full(31, 100.0)
        long_t = np.full(31, 100.0)
        short_t[0] = 90.0
        long_t[0] = 95.0
        short_t[1] = 105.0
        long_t[1] = 95.0
        ctx = make_context(
            kdj_j=np.array([10.0, -5.0]),
            short_t=short_t,
            long_t=long_t,
        )
        algo = KdjZxtrendAlgo(lookback=30)
        algo(ctx)
        assert ctx.buy_shares > 0
