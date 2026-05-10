"""Tests for StrategyBuilder."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from stablemoney.market_sector import MarketSector, SectorFilter
from stablemoney.strategy_builder import StrategyBuilder
from stablemoney.strategy_config import BacktestConfig


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
