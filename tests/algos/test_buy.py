"""Tests for buy.place_buy()."""

from __future__ import annotations

from unittest.mock import MagicMock

from stablemoney.algos.algo_config import AlgoConfig
from stablemoney.algos.buy import place_buy


def _make_ctx(initial_cash: float = 100_000) -> MagicMock:
    ctx = MagicMock()
    ctx.config = MagicMock()
    ctx.config.initial_cash = initial_cash
    ctx.buy_shares = 0
    return ctx


class TestPlaceBuy:
    def test_sets_buy_shares(self) -> None:
        ctx = _make_ctx()
        place_buy(ctx, 500, AlgoConfig())
        assert ctx.buy_shares == 500

    def test_minimum_100_shares(self) -> None:
        ctx = _make_ctx()
        place_buy(ctx, 50, AlgoConfig())
        assert ctx.buy_shares == 100

    def test_stop_loss_applied(self) -> None:
        ctx = _make_ctx()
        config = AlgoConfig(stop_loss_pct=5.0)
        place_buy(ctx, 500, config)
        assert ctx.stop_loss_pct == 5.0

    def test_stop_loss_not_applied_when_zero(self) -> None:
        ctx = _make_ctx()
        config = AlgoConfig(stop_loss_pct=0.0)
        place_buy(ctx, 500, config)
        assert "stop_loss_pct" not in [c[0] for c in ctx.method_calls]

    def test_take_profit_applied(self) -> None:
        ctx = _make_ctx()
        config = AlgoConfig(take_profit_pct=10.0)
        place_buy(ctx, 500, config)
        assert ctx.stop_profit_pct == 10.0

    def test_hold_bars_applied(self) -> None:
        ctx = _make_ctx()
        config = AlgoConfig(hold_bars=30)
        place_buy(ctx, 500, config)
        assert ctx.hold_bars == 30
