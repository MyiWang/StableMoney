"""Tests for StrategyBuilder validation and run orchestration."""

from __future__ import annotations

import sys
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest
from pybroker.data import DataSource

from stablemoney.strategy_builder import StrategyBuilder
from stablemoney.strategy_config import BacktestConfig
from stablemoney.market_sector import MarketSector, SectorFilter


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
        # Validation should pass (TDX mock needed for run, but _validate works)
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

    @patch("stablemoney.strategy_builder._resolve_sector")
    @patch("stablemoney.strategy_builder.PyBrokerStrategy")
    @patch("stablemoney.strategy_builder.PyBrokerStrategyConfig")
    def test_sector_resolves_symbols(
        self,
        mock_config_cls: MagicMock,
        mock_strategy_cls: MagicMock,
        mock_resolve: MagicMock,
    ) -> None:
        mock_resolve.return_value = ["300001.SZ", "300002.SZ"]
        mock_strategy = MagicMock()
        mock_strategy_cls.return_value = mock_strategy
        mock_strategy.backtest.return_value = MagicMock()

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
        builder.run()

        mock_resolve.assert_called_once_with(MarketSector.CHINEXT, None)
        mock_strategy.add_execution.assert_called_once_with(
            fn=builder._exec_fn,
            symbols=["300001.SZ", "300002.SZ"],
        )

    @patch("stablemoney.strategy_builder._resolve_sector")
    @patch("stablemoney.strategy_builder.PyBrokerStrategy")
    @patch("stablemoney.strategy_builder.PyBrokerStrategyConfig")
    def test_sector_with_filter(
        self,
        mock_config_cls: MagicMock,
        mock_strategy_cls: MagicMock,
        mock_resolve: MagicMock,
    ) -> None:
        mock_resolve.return_value = ["688001.SH"]
        mock_strategy = MagicMock()
        mock_strategy_cls.return_value = mock_strategy
        mock_strategy.backtest.return_value = MagicMock()

        sf = SectorFilter(max_stocks=10, sort_by="market_cap")
        builder = StrategyBuilder()
        builder.set_data_source(_mock_data_source())
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

        mock_resolve.assert_called_once_with(MarketSector.STAR, sf)


class TestResolveSector:
    def _mock_tq(self, mock_tq_module: MagicMock) -> MagicMock:
        """Inject mock tq module into sys.modules and return it."""
        tq_mock = MagicMock()
        mock_tq_module.tq = tq_mock
        sys.modules["tqcenter"] = mock_tq_module
        sys.modules["tqcenter.tq"] = tq_mock
        return tq_mock

    @patch.dict(sys.modules, {})
    def test_returns_all_codes(self) -> None:
        mock_tq = self._mock_tq(MagicMock())
        mock_tq.get_stock_list.return_value = ["300001.SZ", "300002.SZ", "300003.SZ"]

        from stablemoney.strategy_builder import _resolve_sector

        result = _resolve_sector(MarketSector.CHINEXT, None)
        assert result == ["300001.SZ", "300002.SZ", "300003.SZ"]
        mock_tq.get_stock_list.assert_called_once_with(market="51")

    @patch.dict(sys.modules, {})
    def test_max_stocks_without_sort(self) -> None:
        mock_tq = self._mock_tq(MagicMock())
        mock_tq.get_stock_list.return_value = [
            "300001.SZ", "300002.SZ", "300003.SZ", "300004.SZ"
        ]

        from stablemoney.strategy_builder import _resolve_sector

        sf = SectorFilter(max_stocks=2)
        result = _resolve_sector(MarketSector.CHINEXT, sf)
        assert result == ["300001.SZ", "300002.SZ"]

    @patch.dict(sys.modules, {})
    def test_sort_and_limit(self) -> None:
        import pandas as pd

        mock_tq = self._mock_tq(MagicMock())
        mock_tq.get_stock_list.return_value = ["A.SH", "B.SZ", "C.SH"]
        close_df = pd.DataFrame(
            {"A.SH": [10.0], "B.SZ": [5.0], "C.SH": [20.0]},
            index=pd.DatetimeIndex(["2025-01-01"]),
        )
        mock_tq.get_market_data.return_value = {"Close": close_df}
        # J_zgb in 万股: A=30000万(市值=10*30000/10000=30亿),
        # B=10000万(5*10000/10000=5亿), C=5000万(20*5000/10000=10亿)
        mock_tq.get_stock_info.side_effect = [
            {"J_zgb": "30000"},
            {"J_zgb": "10000"},
            {"J_zgb": "5000"},
        ]

        from stablemoney.strategy_builder import _resolve_sector

        sf = SectorFilter(max_stocks=2, sort_by="market_cap", sort_ascending=False)
        result = _resolve_sector(MarketSector.ALL, sf)
        assert result == ["A.SH", "C.SH"]

    @patch.dict(sys.modules, {})
    def test_sort_ascending(self) -> None:
        import pandas as pd

        mock_tq = self._mock_tq(MagicMock())
        mock_tq.get_stock_list.return_value = ["A.SH", "B.SZ"]
        close_df = pd.DataFrame(
            {"A.SH": [10.0], "B.SZ": [5.0]},
            index=pd.DatetimeIndex(["2025-01-01"]),
        )
        mock_tq.get_market_data.return_value = {"Close": close_df}
        # A=10*30000/10000=30亿, B=5*10000/10000=5亿
        mock_tq.get_stock_info.side_effect = [
            {"J_zgb": "30000"},
            {"J_zgb": "10000"},
        ]

        from stablemoney.strategy_builder import _resolve_sector

        sf = SectorFilter(sort_by="market_cap", sort_ascending=True)
        result = _resolve_sector(MarketSector.ALL, sf)
        assert result == ["B.SZ", "A.SH"]

    @patch.dict(sys.modules, {})
    def test_empty_codes(self) -> None:
        mock_tq = self._mock_tq(MagicMock())
        mock_tq.get_stock_list.return_value = []

        from stablemoney.strategy_builder import _resolve_sector

        result = _resolve_sector(MarketSector.BSE, None)
        assert result == []

    @patch.dict(sys.modules, {})
    def test_handles_failed_stock_info(self) -> None:
        import pandas as pd

        mock_tq = self._mock_tq(MagicMock())
        mock_tq.get_stock_list.return_value = ["A.SH", "B.SZ"]
        close_df = pd.DataFrame(
            {"A.SH": [10.0], "B.SZ": [5.0]},
            index=pd.DatetimeIndex(["2025-01-01"]),
        )
        mock_tq.get_market_data.return_value = {"Close": close_df}
        # A fails, B succeeds
        mock_tq.get_stock_info.side_effect = [
            Exception("error"),
            {"J_zgb": "10000"},
        ]

        from stablemoney.strategy_builder import _resolve_sector

        sf = SectorFilter(sort_by="market_cap", sort_ascending=True)
        result = _resolve_sector(MarketSector.ALL, sf)
        assert result == ["A.SH", "B.SZ"]  # A=0.0 < B=5.0

    @patch.dict(sys.modules, {})
    def test_market_cap_range_filter(self) -> None:
        import pandas as pd

        mock_tq = self._mock_tq(MagicMock())
        mock_tq.get_stock_list.return_value = ["A.SH", "B.SZ", "C.SH", "D.SZ"]
        close_df = pd.DataFrame(
            {"A.SH": [5.0], "B.SZ": [10.0], "C.SH": [20.0], "D.SZ": [50.0]},
            index=pd.DatetimeIndex(["2025-01-01"]),
        )
        mock_tq.get_market_data.return_value = {"Close": close_df}
        # 市值(亿): A=5*6000/10000=3, B=10*4000/10000=4,
        # C=20*2000/10000=4, D=50*10000/10000=50
        mock_tq.get_stock_info.side_effect = [
            {"J_zgb": "6000"},
            {"J_zgb": "4000"},
            {"J_zgb": "2000"},
            {"J_zgb": "10000"},
        ]

        from stablemoney.strategy_builder import _resolve_sector

        sf = SectorFilter(
            sort_by="market_cap",
            sort_ascending=False,
            min_market_cap=3.5,
            max_market_cap=10.0,
        )
        result = _resolve_sector(MarketSector.ALL, sf)
        # Sorted desc: D=50亿, B=4亿, C=4亿, A=3亿
        # Range [3.5, 10]: B=4, C=4
        assert result == ["B.SZ", "C.SH"]

    @patch.dict(sys.modules, {})
    def test_market_cap_range_with_max_stocks(self) -> None:
        import pandas as pd

        mock_tq = self._mock_tq(MagicMock())
        mock_tq.get_stock_list.return_value = ["A.SH", "B.SZ", "C.SH"]
        close_df = pd.DataFrame(
            {"A.SH": [5.0], "B.SZ": [10.0], "C.SH": [20.0]},
            index=pd.DatetimeIndex(["2025-01-01"]),
        )
        mock_tq.get_market_data.return_value = {"Close": close_df}
        # A=5*6000/10000=3亿, B=10*4000/10000=4亿, C=20*2000/10000=4亿
        mock_tq.get_stock_info.side_effect = [
            {"J_zgb": "6000"},
            {"J_zgb": "4000"},
            {"J_zgb": "2000"},
        ]

        from stablemoney.strategy_builder import _resolve_sector

        sf = SectorFilter(
            sort_by="market_cap",
            sort_ascending=False,
            min_market_cap=3.5,
            max_stocks=1,
        )
        result = _resolve_sector(MarketSector.ALL, sf)
        # Sorted desc: B=4, C=4, A=3. Range >=3.5: B,C. max_stocks=1: [B.SZ]
        assert result == ["B.SZ"]
