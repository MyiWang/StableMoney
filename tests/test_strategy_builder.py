"""Tests for StrategyBuilder validation and run orchestration."""

from __future__ import annotations

from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest
from pybroker.data import DataSource

from stablemoney.data_providers.data_provider import DataProvider
from stablemoney.market_sector import MarketSector, SectorFilter
from stablemoney.strategy_builder import StrategyBuilder
from stablemoney.strategy_config import BacktestConfig


def _mock_data_source() -> MagicMock:
    return MagicMock(spec=DataSource)


def _make_config(**kwargs: object) -> BacktestConfig:
    defaults = {
        "symbols": ["600519.SH"],
        "start_date": "2024-01-01",
        "end_date": "2024-12-31",
    }
    defaults.update(kwargs)
    return BacktestConfig(**defaults)  # type: ignore[arg-type]


class TestFluentInterface:
    def test_set_data_source_returns_self(self) -> None:
        builder = StrategyBuilder()
        result = builder.set_data_source(_mock_data_source())
        assert result is builder

    def test_set_backtest_returns_self(self) -> None:
        builder = StrategyBuilder()
        result = builder.set_backtest(_make_config())
        assert result is builder

    def test_set_algo_returns_self(self) -> None:
        builder = StrategyBuilder()
        result = builder.set_algo(lambda ctx: None)
        assert result is builder

    def test_set_data_provider_returns_self(self) -> None:
        builder = StrategyBuilder()
        result = builder.set_data_provider(MagicMock(spec=DataProvider))
        assert result is builder


class TestValidation:
    def test_missing_data_source(self) -> None:
        builder = StrategyBuilder()
        builder.set_backtest(_make_config())
        builder.set_algo(lambda ctx: None)
        with pytest.raises(ValueError, match="DataSource"):
            builder.run()

    def test_missing_backtest(self) -> None:
        builder = StrategyBuilder()
        builder.set_data_source(_mock_data_source())
        builder.set_algo(lambda ctx: None)
        with pytest.raises(ValueError, match="BacktestConfig"):
            builder.run()

    def test_missing_algo(self) -> None:
        builder = StrategyBuilder()
        builder.set_data_source(_mock_data_source())
        builder.set_backtest(_make_config())
        with pytest.raises(ValueError, match="ExecuteCallback"):
            builder.run()

    def test_all_missing(self) -> None:
        builder = StrategyBuilder()
        with pytest.raises(ValueError):
            builder.run()

    def test_both_symbols_and_sector(self) -> None:
        builder = StrategyBuilder()
        builder.set_data_source(_mock_data_source())
        builder.set_backtest(
            _make_config(sector=MarketSector.CHINEXT)
        )
        builder.set_algo(lambda ctx: None)
        with pytest.raises(ValueError, match="mutually exclusive"):
            builder.run()

    def test_neither_symbols_nor_sector(self) -> None:
        builder = StrategyBuilder()
        builder.set_data_source(_mock_data_source())
        builder.set_backtest(
            BacktestConfig(
                start_date="2024-01-01",
                end_date="2024-12-31",
            )
        )
        builder.set_algo(lambda ctx: None)
        with pytest.raises(ValueError, match="Either 'symbols' or 'sector'"):
            builder.run()

    def test_sector_only_passes_validation(self) -> None:
        builder = StrategyBuilder()
        builder.set_data_source(_mock_data_source())
        builder.set_backtest(
            BacktestConfig(
                start_date="2024-01-01",
                end_date="2024-12-31",
                sector=MarketSector.CHINEXT,
            )
        )
        builder.set_algo(lambda ctx: None)
        builder._validate()


class TestRun:
    @patch("stablemoney.strategy_builder.PyBrokerStrategy")
    @patch("stablemoney.strategy_builder.PyBrokerStrategyConfig")
    def test_creates_strategy_with_initial_cash(
        self,
        mock_config_cls: MagicMock,
        mock_strategy_cls: MagicMock,
    ) -> None:
        mock_strategy = MagicMock()
        mock_strategy_cls.return_value = mock_strategy
        mock_strategy.backtest.return_value = MagicMock()

        builder = StrategyBuilder()
        builder.set_data_source(_mock_data_source())
        builder.set_backtest(_make_config(initial_cash=500_000))
        builder.set_algo(lambda ctx: None)
        builder.run()

        mock_config_cls.assert_called_once_with(initial_cash=500_000)

    @patch("stablemoney.strategy_builder.PyBrokerStrategy")
    @patch("stablemoney.strategy_builder.PyBrokerStrategyConfig")
    def test_passes_dates_to_strategy(
        self,
        mock_config_cls: MagicMock,
        mock_strategy_cls: MagicMock,
    ) -> None:
        mock_strategy = MagicMock()
        mock_strategy_cls.return_value = mock_strategy
        mock_strategy.backtest.return_value = MagicMock()

        builder = StrategyBuilder()
        builder.set_data_source(_mock_data_source())
        builder.set_backtest(
            _make_config(
                start_date="2024-01-01",
                end_date="2024-12-31",
            )
        )
        builder.set_algo(lambda ctx: None)
        builder.run()

        call_kwargs = mock_strategy_cls.call_args
        assert call_kwargs.kwargs["start_date"] == datetime(2024, 1, 1)
        assert call_kwargs.kwargs["end_date"] == datetime(2024, 12, 31)

    @patch("stablemoney.strategy_builder.PyBrokerStrategy")
    @patch("stablemoney.strategy_builder.PyBrokerStrategyConfig")
    def test_calls_add_execution(
        self,
        mock_config_cls: MagicMock,
        mock_strategy_cls: MagicMock,
    ) -> None:
        def algo_fn(ctx: object) -> None:
            pass

        mock_strategy = MagicMock()
        mock_strategy_cls.return_value = mock_strategy
        mock_strategy.backtest.return_value = MagicMock()

        builder = StrategyBuilder()
        builder.set_data_source(_mock_data_source())
        builder.set_backtest(_make_config(symbols=["600519.SH", "000858.SZ"]))
        builder.set_algo(algo_fn)
        builder.run()

        mock_strategy.add_execution.assert_called_once_with(
            fn=algo_fn,
            symbols=["600519.SH", "000858.SZ"],
        )

    @patch("stablemoney.strategy_builder.PyBrokerStrategy")
    @patch("stablemoney.strategy_builder.PyBrokerStrategyConfig")
    def test_backtest_with_warmup(
        self,
        mock_config_cls: MagicMock,
        mock_strategy_cls: MagicMock,
    ) -> None:
        mock_strategy = MagicMock()
        mock_strategy_cls.return_value = mock_strategy
        mock_result = MagicMock()
        mock_strategy.backtest.return_value = mock_result

        builder = StrategyBuilder()
        builder.set_data_source(_mock_data_source())
        builder.set_backtest(_make_config(warmup=110))
        builder.set_algo(lambda ctx: None)
        result = builder.run()

        mock_strategy.backtest.assert_called_once_with(warmup=110)
        assert result is mock_result

    @patch("stablemoney.strategy_builder.PyBrokerStrategy")
    @patch("stablemoney.strategy_builder.PyBrokerStrategyConfig")
    def test_backtest_with_none_warmup(
        self,
        mock_config_cls: MagicMock,
        mock_strategy_cls: MagicMock,
    ) -> None:
        mock_strategy = MagicMock()
        mock_strategy_cls.return_value = mock_strategy
        mock_strategy.backtest.return_value = MagicMock()

        builder = StrategyBuilder()
        builder.set_data_source(_mock_data_source())
        builder.set_backtest(_make_config(warmup=None))
        builder.set_algo(lambda ctx: None)
        builder.run()

        mock_strategy.backtest.assert_called_once_with(warmup=None)

    @patch("stablemoney.strategy_builder.PyBrokerStrategy")
    @patch("stablemoney.strategy_builder.PyBrokerStrategyConfig")
    def test_returns_test_result(
        self,
        mock_config_cls: MagicMock,
        mock_strategy_cls: MagicMock,
    ) -> None:
        mock_result = MagicMock()
        mock_strategy = MagicMock()
        mock_strategy_cls.return_value = mock_strategy
        mock_strategy.backtest.return_value = mock_result

        builder = StrategyBuilder()
        builder.set_data_source(_mock_data_source())
        builder.set_backtest(_make_config())
        builder.set_algo(lambda ctx: None)
        assert builder.run() is mock_result

    @patch("stablemoney.strategy_builder.PyBrokerStrategy")
    @patch("stablemoney.strategy_builder.PyBrokerStrategyConfig")
    def test_sector_resolves_via_provider(
        self,
        mock_config_cls: MagicMock,
        mock_strategy_cls: MagicMock,
    ) -> None:
        mock_strategy = MagicMock()
        mock_strategy_cls.return_value = mock_strategy
        mock_strategy.backtest.return_value = MagicMock()

        mock_provider = MagicMock(spec=DataProvider)
        mock_provider.resolve_sector.return_value = ["300001.SZ", "300002.SZ"]

        builder = StrategyBuilder()
        builder.set_data_source(_mock_data_source())
        builder.set_data_provider(mock_provider)
        builder.set_backtest(
            BacktestConfig(
                start_date="2024-01-01",
                end_date="2024-12-31",
                sector=MarketSector.CHINEXT,
            )
        )
        builder.set_algo(lambda ctx: None)
        builder.run()

        mock_provider.resolve_sector.assert_called_once_with(
            MarketSector.CHINEXT, None
        )
        mock_strategy.add_execution.assert_called_once_with(
            fn=builder._exec_fn,
            symbols=["300001.SZ", "300002.SZ"],
        )

    @patch("stablemoney.strategy_builder.PyBrokerStrategy")
    @patch("stablemoney.strategy_builder.PyBrokerStrategyConfig")
    def test_sector_with_filter(
        self,
        mock_config_cls: MagicMock,
        mock_strategy_cls: MagicMock,
    ) -> None:
        mock_strategy = MagicMock()
        mock_strategy_cls.return_value = mock_strategy
        mock_strategy.backtest.return_value = MagicMock()

        mock_provider = MagicMock(spec=DataProvider)
        mock_provider.resolve_sector.return_value = ["688001.SH"]

        sf = SectorFilter(max_stocks=10, sort_by="market_cap")
        builder = StrategyBuilder()
        builder.set_data_source(_mock_data_source())
        builder.set_data_provider(mock_provider)
        builder.set_backtest(
            BacktestConfig(
                start_date="2024-01-01",
                end_date="2024-12-31",
                sector=MarketSector.STAR,
                sector_filter=sf,
            )
        )
        builder.set_algo(lambda ctx: None)
        builder.run()

        mock_provider.resolve_sector.assert_called_once_with(MarketSector.STAR, sf)

    def test_sector_without_provider_raises(self) -> None:
        builder = StrategyBuilder()
        builder.set_data_source(_mock_data_source())
        builder.set_backtest(
            BacktestConfig(
                start_date="2024-01-01",
                end_date="2024-12-31",
                sector=MarketSector.CHINEXT,
            )
        )
        builder.set_algo(lambda ctx: None)
        with pytest.raises(ValueError, match="DataProvider"):
            builder.run()
