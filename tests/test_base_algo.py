"""Tests for BaseAlgo abstract base class."""

from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING
from unittest.mock import MagicMock

import pytest

from stablemoney.algos.base_algo import BaseAlgo

if TYPE_CHECKING:
    from pybroker.context import ExecContext


class _MinimalAlgo(BaseAlgo):
    """Minimal concrete subclass for testing."""

    def __init__(self) -> None:
        self.trade_calls: list[MagicMock] = []

    def trade(self, ctx: ExecContext) -> None:
        self.trade_calls.append(ctx)


class _AlgoWithHooks(BaseAlgo):
    """Subclass that overrides all three methods."""

    def __init__(self) -> None:
        self.before_calls: list[Mapping[str, MagicMock]] = []
        self.trade_calls: list[MagicMock] = []
        self.after_calls: list[Mapping[str, MagicMock]] = []

    def before_trade(self, ctxs: Mapping[str, ExecContext]) -> None:
        self.before_calls.append(ctxs)

    def trade(self, ctx: ExecContext) -> None:
        self.trade_calls.append(ctx)

    def after_trade(self, ctxs: Mapping[str, ExecContext]) -> None:
        self.after_calls.append(ctxs)


class TestBaseAlgoAbcEnforcement:
    """BaseAlgo cannot be instantiated directly or without trade()."""

    def test_cannot_instantiate_base_algo(self) -> None:
        with pytest.raises(TypeError):
            BaseAlgo()  # type: ignore[abstract]

    def test_subclass_without_trade_cannot_instantiate(self) -> None:
        class _Incomplete(BaseAlgo):
            pass

        with pytest.raises(TypeError):
            _Incomplete()  # type: ignore[abstract]


class TestMinimalAlgoTrade:
    """Subclass with only trade() works correctly."""

    def test_instantiation(self) -> None:
        algo = _MinimalAlgo()
        assert isinstance(algo, BaseAlgo)

    def test_trade_called(self) -> None:
        algo = _MinimalAlgo()
        ctx = MagicMock()
        algo.trade(ctx)
        assert algo.trade_calls == [ctx]

    def test_before_trade_default_is_noop(self) -> None:
        algo = _MinimalAlgo()
        ctxs: Mapping[str, MagicMock] = {"AAPL": MagicMock()}
        algo.before_trade(ctxs)  # should not raise

    def test_after_trade_default_is_noop(self) -> None:
        algo = _MinimalAlgo()
        ctxs: Mapping[str, MagicMock] = {"AAPL": MagicMock()}
        algo.after_trade(ctxs)  # should not raise


class TestAlgoWithHooks:
    """Subclass overriding all three methods."""

    def test_before_trade_receives_all_contexts(self) -> None:
        algo = _AlgoWithHooks()
        ctxs: Mapping[str, MagicMock] = {
            "AAPL": MagicMock(),
            "MSFT": MagicMock(),
        }
        algo.before_trade(ctxs)
        assert algo.before_calls == [ctxs]
        assert len(algo.before_calls[0]) == 2

    def test_trade_receives_single_context(self) -> None:
        algo = _AlgoWithHooks()
        ctx = MagicMock()
        algo.trade(ctx)
        assert algo.trade_calls == [ctx]

    def test_after_trade_receives_all_contexts(self) -> None:
        algo = _AlgoWithHooks()
        ctxs: Mapping[str, MagicMock] = {
            "AAPL": MagicMock(),
            "MSFT": MagicMock(),
        }
        algo.after_trade(ctxs)
        assert algo.after_calls == [ctxs]
