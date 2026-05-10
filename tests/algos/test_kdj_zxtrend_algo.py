"""Tests for KdjZxtrendAlgo — phased exit with fixed position sizing."""
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
    open_price: float | None = None,
    has_position: bool = False,
    shares: int = 1000,
    entry_price: float | None = None,
    symbol: str = "600519.SH",
) -> MagicMock:
    """Build a mock ExecContext for KdjZxtrendAlgo tests.

    Default data has a golden cross at bar index -3 (short crosses above long).
    """
    if kdj_j is None:
        kdj_j = np.array([10.0, -5.0])
    if short_t is None:
        short_t = np.array([90.0, 95.0, 100.0, 105.0, 110.0])
    if long_t is None:
        long_t = np.array([95.0, 98.0, 96.0, 100.0, 102.0])
    if open_price is None:
        open_price = close

    ctx = MagicMock()
    ctx.KDJ_J = kdj_j
    ctx.ZXTREND_SHORT_T = short_t
    ctx.ZXTREND_LONG_T = long_t
    ctx.close = np.array([close])
    ctx.open = np.array([open_price])
    ctx.date = np.array([np.datetime64("2024-06-01")])
    ctx.symbol = symbol
    ctx.buy_shares = 0
    ctx.sell_shares = 0

    if has_position:
        pos = MagicMock()
        pos.shares = shares
        entry = MagicMock()
        entry.price = entry_price if entry_price is not None else close
        pos.entries = [entry]
        ctx.long_pos.return_value = pos
    else:
        ctx.long_pos.return_value = None

    return ctx


class TestBuySignal:
    """Buy condition: KDJ.J < 0 and recent ZXTREND golden cross."""

    def test_buy_with_golden_cross_and_j_below_zero(self) -> None:
        ctx = make_context(close=20.0)
        algo = KdjZxtrendAlgo(position_amount=20_000)
        algo.trade(ctx)
        assert ctx.buy_shares == 1000  # int(20000/20/100)*100

    def test_position_sizing_rounds_to_100_lots(self) -> None:
        ctx = make_context(close=15.0)
        algo = KdjZxtrendAlgo(position_amount=20_000)
        algo.trade(ctx)
        assert ctx.buy_shares == 1300  # int(20000/15/100)*100

    def test_no_buy_when_j_above_zero(self) -> None:
        ctx = make_context(kdj_j=np.array([5.0, 10.0]))
        algo = KdjZxtrendAlgo()
        algo.trade(ctx)
        assert ctx.buy_shares == 0

    def test_no_buy_when_no_golden_cross(self) -> None:
        ctx = make_context(
            kdj_j=np.array([10.0, -5.0]),
            short_t=np.array([100.0, 105.0, 110.0, 115.0, 120.0]),
            long_t=np.array([90.0, 92.0, 94.0, 96.0, 98.0]),
        )
        algo = KdjZxtrendAlgo()
        algo.trade(ctx)
        assert ctx.buy_shares == 0

    def test_no_buy_with_existing_position(self) -> None:
        ctx = make_context(has_position=True)
        algo = KdjZxtrendAlgo()
        algo.trade(ctx)
        assert ctx.buy_shares == 0

    def test_no_action_on_nan(self) -> None:
        ctx = make_context()
        ctx.KDJ_J = np.array([10.0, float("nan")])
        algo = KdjZxtrendAlgo()
        algo.trade(ctx)
        assert ctx.buy_shares == 0

    def test_stop_loss_set_on_buy(self) -> None:
        ctx = make_context()
        algo = KdjZxtrendAlgo(config=AlgoConfig(stop_loss_pct=5.0))
        algo.trade(ctx)
        assert ctx.stop_loss_pct == 5.0

    def test_golden_cross_at_edge_of_lookback(self) -> None:
        """Golden cross exactly at lookback boundary → should still buy."""
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
        algo.trade(ctx)
        assert ctx.buy_shares > 0

    def test_no_buy_when_golden_cross_too_old(self) -> None:
        short_t = np.full(36, 100.0)
        long_t = np.full(36, 100.0)
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
        algo.trade(ctx)
        assert ctx.buy_shares == 0


class TestLongTBreakdown:
    """LONG_T breakdown (open & close < LONG_T) → sell all, any phase."""

    def test_sell_all_at_phase0(self) -> None:
        ctx = make_context(
            has_position=True,
            shares=1000,
            close=95.0,
            open_price=94.0,
            short_t=np.array([100.0, 105.0, 110.0]),
            long_t=np.array([100.0, 102.0, 100.0]),
        )
        algo = KdjZxtrendAlgo()
        algo.trade(ctx)
        ctx.sell_all_shares.assert_called_once()

    def test_sell_all_at_phase1(self) -> None:
        ctx = make_context(
            has_position=True,
            shares=500,
            close=95.0,
            open_price=94.0,
            short_t=np.array([100.0, 105.0, 110.0]),
            long_t=np.array([100.0, 102.0, 100.0]),
        )
        algo = KdjZxtrendAlgo()
        algo._phase["600519.SH"] = 1
        algo.trade(ctx)
        ctx.sell_all_shares.assert_called_once()

    def test_sell_all_at_phase2(self) -> None:
        ctx = make_context(
            has_position=True,
            shares=250,
            close=95.0,
            open_price=94.0,
            short_t=np.array([100.0, 105.0, 110.0]),
            long_t=np.array([100.0, 102.0, 100.0]),
        )
        algo = KdjZxtrendAlgo()
        algo._phase["600519.SH"] = 2
        algo.trade(ctx)
        ctx.sell_all_shares.assert_called_once()

    def test_no_sell_when_close_above_long_t(self) -> None:
        ctx = make_context(
            has_position=True,
            shares=1000,
            close=102.0,
            open_price=94.0,
            short_t=np.array([100.0, 105.0, 110.0]),
            long_t=np.array([100.0, 102.0, 100.0]),
        )
        algo = KdjZxtrendAlgo()
        algo.trade(ctx)
        ctx.sell_all_shares.assert_not_called()


class TestTakeProfitHalf:
    """10% profit at phase 0 → sell half, advance to phase 1."""

    def test_sell_half_at_take_profit(self) -> None:
        # entry=10, close=11 → 10% profit; close > long_t[-1] so no LONG_T breakdown
        ctx = make_context(
            has_position=True,
            shares=1000,
            entry_price=10.0,
            close=11.0,
            short_t=np.array([9.0, 9.5, 10.5, 11.0, 11.5]),
            long_t=np.array([8.0, 8.5, 9.0, 9.5, 10.0]),
        )
        algo = KdjZxtrendAlgo(take_profit_pct=10.0)
        algo.trade(ctx)
        assert ctx.sell_shares == 500

    def test_phase_advances_to_1(self) -> None:
        ctx = make_context(
            has_position=True,
            shares=1000,
            entry_price=10.0,
            close=11.0,
            short_t=np.array([9.0, 9.5, 10.5, 11.0, 11.5]),
            long_t=np.array([8.0, 8.5, 9.0, 9.5, 10.0]),
        )
        algo = KdjZxtrendAlgo(take_profit_pct=10.0)
        algo.trade(ctx)
        assert algo._phase.get("600519.SH") == 1

    def test_no_sell_below_take_profit(self) -> None:
        # entry=10, close=10.9 → 9% profit
        ctx = make_context(
            has_position=True,
            shares=1000,
            entry_price=10.0,
            close=10.9,
            short_t=np.array([9.0, 9.5, 10.5, 11.0, 11.5]),
            long_t=np.array([8.0, 8.5, 9.0, 9.5, 10.0]),
        )
        algo = KdjZxtrendAlgo(take_profit_pct=10.0)
        algo.trade(ctx)
        assert ctx.sell_shares == 0

    def test_no_take_profit_at_phase1(self) -> None:
        # Already sold half, profit still high → no further profit sell
        # close > short_t[-1] so SHORT_T breakdown doesn't trigger either
        ctx = make_context(
            has_position=True,
            shares=500,
            entry_price=10.0,
            close=12.0,
            short_t=np.array([9.0, 9.5, 10.5, 11.0, 11.5]),
            long_t=np.array([8.0, 8.5, 9.0, 9.5, 10.0]),
        )
        algo = KdjZxtrendAlgo(take_profit_pct=10.0)
        algo._phase["600519.SH"] = 1
        algo.trade(ctx)
        assert ctx.sell_shares == 0


class TestShortTBreakdown:
    """SHORT_T breakdown (open & close < SHORT_T) at phase 1 → sell half."""

    def test_sell_half_on_short_t_breakdown(self) -> None:
        ctx = make_context(
            has_position=True,
            shares=500,
            entry_price=10.0,
            close=104.0,
            open_price=103.0,
            short_t=np.array([100.0, 105.0, 110.0]),
            long_t=np.array([90.0, 92.0, 94.0]),
        )
        algo = KdjZxtrendAlgo()
        algo._phase["600519.SH"] = 1
        algo.trade(ctx)
        assert ctx.sell_shares == 250

    def test_phase_advances_to_2(self) -> None:
        ctx = make_context(
            has_position=True,
            shares=500,
            entry_price=10.0,
            close=104.0,
            open_price=103.0,
            short_t=np.array([100.0, 105.0, 110.0]),
            long_t=np.array([90.0, 92.0, 94.0]),
        )
        algo = KdjZxtrendAlgo()
        algo._phase["600519.SH"] = 1
        algo.trade(ctx)
        assert algo._phase.get("600519.SH") == 2

    def test_no_short_t_breakdown_at_phase0(self) -> None:
        # entry=100, close=104 → 4% profit < 99%; SHORT_T broken but phase=0
        ctx = make_context(
            has_position=True,
            shares=1000,
            entry_price=100.0,
            close=104.0,
            open_price=103.0,
            short_t=np.array([100.0, 105.0, 110.0]),
            long_t=np.array([90.0, 92.0, 94.0]),
        )
        algo = KdjZxtrendAlgo(take_profit_pct=99.0)
        algo.trade(ctx)
        assert ctx.sell_shares == 0

    def test_no_sell_when_close_above_short_t(self) -> None:
        ctx = make_context(
            has_position=True,
            shares=500,
            entry_price=10.0,
            close=112.0,
            open_price=103.0,
            short_t=np.array([100.0, 105.0, 110.0]),
            long_t=np.array([90.0, 92.0, 94.0]),
        )
        algo = KdjZxtrendAlgo()
        algo._phase["600519.SH"] = 1
        algo.trade(ctx)
        assert ctx.sell_shares == 0


class TestPhaseReset:
    """After full sell, phase resets and re-buy is possible."""

    def test_phase_resets_on_new_buy(self) -> None:
        algo = KdjZxtrendAlgo(position_amount=20_000)
        algo._phase["600519.SH"] = 1  # Leftover from previous cycle

        ctx = make_context(close=20.0)
        algo.trade(ctx)
        assert ctx.buy_shares > 0
        # Phase should have been reset
        assert "600519.SH" not in algo._phase or algo._phase.get("600519.SH") == 0
