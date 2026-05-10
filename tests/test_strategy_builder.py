"""Tests for StrategyBuilder."""

from __future__ import annotations

from collections.abc import Mapping
from unittest.mock import MagicMock, patch
from typing import TYPE_CHECKING

import pytest
from stablemoney.algos.base_algo import BaseAlgo
from stablemoney.market_sector import MarketSector, SectorFilter
from stablemoney.strategy_builder import StrategyBuilder
from stablemoney.strategy_config import BacktestConfig

if TYPE_CHECKING:
    from pybroker.context import ExecContext


def _algo(ctx: object) -> None:
    pass


def _make_builder() -> StrategyBuilder:
    return StrategyBuilder()


class TestValidation:
    def test_missing_data_source(self) -> None:
        config = BacktestConfig(symbols=["600519.SH"], start_date="2024-01-01", end_date="2024-12-31")
        builder = _make_builder().set_backtest(config).set_algo(_algo)
        with pytest.raises(ValueError, match="DataSource"):
            builder.run()

    def test_missing_backtest(self) -> None:
        mock_ds = MagicMock()
        builder = _make_builder().set_data_source(mock_ds).set_algo(_algo)
        with pytest.raises(ValueError, match="BacktestConfig"):
            builder.run()

    def test_missing_algo(self) -> None:
        mock_ds = MagicMock()
        config = BacktestConfig(symbols=["600519.SH"], start_date="2024-01-01", end_date="2024-12-31")
        builder = _make_builder().set_data_source(mock_ds).set_backtest(config)
        with pytest.raises(ValueError, match="ExecuteCallback"):
            builder.run()

    def test_symbols_and_sector_mutually_exclusive(self) -> None:
        mock_ds = MagicMock()
        config = BacktestConfig(
            symbols=["600519.SH"],
            sector=MarketSector.ALL,
            start_date="2024-01-01",
            end_date="2024-12-31",
        )
        builder = _make_builder().set_data_source(mock_ds).set_backtest(config).set_algo(_algo)
        with pytest.raises(ValueError, match="mutually exclusive"):
            builder.run()

    def test_neither_symbols_nor_sector(self) -> None:
        mock_ds = MagicMock()
        config = BacktestConfig(start_date="2024-01-01", end_date="2024-12-31")
        builder = _make_builder().set_data_source(mock_ds).set_backtest(config).set_algo(_algo)
        with pytest.raises(ValueError, match="Either"):
            builder.run()


class TestResolveSymbols:
    def test_uses_explicit_symbols(self) -> None:
        config = BacktestConfig(symbols=["600519.SH", "000858.SZ"], start_date="2024-01-01", end_date="2024-12-31")
        builder = _make_builder().set_backtest(config)
        assert builder._resolve_symbols() == ["600519.SH", "000858.SZ"]

    def test_resolves_sector_via_provider(self) -> None:
        mock_provider = MagicMock()
        mock_provider.resolve_sector.return_value = ["600519.SH", "000858.SZ"]
        config = BacktestConfig(
            sector=MarketSector.ALL,
            start_date="2024-01-01",
            end_date="2024-12-31",
        )
        builder = (
            _make_builder()
            .set_backtest(config)
            .set_data_provider(mock_provider)
        )
        result = builder._resolve_symbols()
        mock_provider.resolve_sector.assert_called_once_with(MarketSector.ALL, None)
        assert result == ["600519.SH", "000858.SZ"]

    def test_sector_without_provider_raises(self) -> None:
        config = BacktestConfig(
            sector=MarketSector.ALL,
            start_date="2024-01-01",
            end_date="2024-12-31",
        )
        builder = _make_builder().set_backtest(config)
        with pytest.raises(ValueError, match="DataProvider"):
            builder._resolve_symbols()

    def test_sector_with_filter(self) -> None:
        mock_provider = MagicMock()
        mock_provider.resolve_sector.return_value = ["600519.SH"]
        sf = SectorFilter(max_stocks=10, sort_by="market_cap")
        config = BacktestConfig(
            sector=MarketSector.CHINEXT,
            start_date="2024-01-01",
            end_date="2024-12-31",
            sector_filter=sf,
        )
        builder = (
            _make_builder()
            .set_backtest(config)
            .set_data_provider(mock_provider)
        )
        builder._resolve_symbols()
        mock_provider.resolve_sector.assert_called_once_with(MarketSector.CHINEXT, sf)


class TestFluentInterface:
    def test_set_methods_return_builder(self) -> None:
        mock_ds = MagicMock()
        mock_provider = MagicMock()
        config = BacktestConfig(symbols=["600519.SH"], start_date="2024-01-01", end_date="2024-12-31")
        builder = _make_builder()
        assert builder.set_data_source(mock_ds) is builder
        assert builder.set_backtest(config) is builder
        assert builder.set_algo(_algo) is builder
        assert builder.set_data_provider(mock_provider) is builder


class _SimpleAlgo(BaseAlgo):
    """BaseAlgo subclass without hook overrides."""

    def __init__(self) -> None:
        self.trade_calls: list[object] = []

    def trade(self, ctx: ExecContext) -> None:
        self.trade_calls.append(ctx)


class _HookedAlgo(BaseAlgo):
    """BaseAlgo subclass that overrides all three methods."""

    def __init__(self) -> None:
        self.before_calls: list[object] = []
        self.trade_calls: list[object] = []
        self.after_calls: list[object] = []

    def before_trade(self, ctxs: Mapping[str, ExecContext]) -> None:
        self.before_calls.append(ctxs)

    def trade(self, ctx: ExecContext) -> None:
        self.trade_calls.append(ctx)

    def after_trade(self, ctxs: Mapping[str, ExecContext]) -> None:
        self.after_calls.append(ctxs)


def _make_runnable_builder(algo: object) -> tuple[StrategyBuilder, MagicMock]:
    """Create a builder ready to run with mocked PyBroker Strategy."""
    mock_ds = MagicMock()
    config = BacktestConfig(
        symbols=["600519.SH"],
        start_date="2024-01-01",
        end_date="2024-12-31",
    )
    builder = _make_builder()
    builder.set_data_source(mock_ds)
    builder.set_backtest(config)
    builder.set_algo(algo)  # type: ignore[arg-type]
    return builder, mock_ds


class TestAlgoRegistration:
    """Verify StrategyBuilder registers algo correctly with PyBroker."""

    @patch("stablemoney.strategy_builder.PyBrokerStrategy")
    def test_plain_callable_passed_directly(self, mock_strategy_cls: MagicMock) -> None:
        mock_strategy = mock_strategy_cls.return_value
        mock_strategy.backtest.return_value = MagicMock()
        builder, _ = _make_runnable_builder(_algo)
        builder.run()
        call_kwargs = mock_strategy.add_execution.call_args
        assert call_kwargs.kwargs.get("fn") is _algo or call_kwargs[1].get("fn") is _algo

    @patch("stablemoney.strategy_builder.PyBrokerStrategy")
    def test_base_algo_registers_trade_method(self, mock_strategy_cls: MagicMock) -> None:
        mock_strategy = mock_strategy_cls.return_value
        mock_strategy.backtest.return_value = MagicMock()
        algo = _SimpleAlgo()
        builder, _ = _make_runnable_builder(algo)
        builder.run()
        call_kwargs = mock_strategy.add_execution.call_args
        registered_fn = call_kwargs.kwargs.get("fn") or call_kwargs[1].get("fn")
        assert registered_fn == algo.trade

    @patch("stablemoney.strategy_builder.PyBrokerStrategy")
    def test_base_algo_no_hooks_no_registration(self, mock_strategy_cls: MagicMock) -> None:
        mock_strategy = mock_strategy_cls.return_value
        mock_strategy.backtest.return_value = MagicMock()
        algo = _SimpleAlgo()
        builder, _ = _make_runnable_builder(algo)
        builder.run()
        mock_strategy.set_before_exec.assert_not_called()
        mock_strategy.set_after_exec.assert_not_called()

    @patch("stablemoney.strategy_builder.PyBrokerStrategy")
    def test_hooked_algo_registers_before_and_after(self, mock_strategy_cls: MagicMock) -> None:
        mock_strategy = mock_strategy_cls.return_value
        mock_strategy.backtest.return_value = MagicMock()
        algo = _HookedAlgo()
        builder, _ = _make_runnable_builder(algo)
        builder.run()
        mock_strategy.set_before_exec.assert_called_once_with(algo.before_trade)
        mock_strategy.set_after_exec.assert_called_once_with(algo.after_trade)
