"""Tests for TdxDataProvider."""

from __future__ import annotations

from datetime import datetime
from unittest.mock import MagicMock

import numpy as np
import pandas as pd
import pytest
from stablemoney.data_providers.tdx_data_provider import TdxDataProvider
from stablemoney.indicator_def import IndicatorDef
from stablemoney.indicators import MA, RSI
from stablemoney.market_sector import MarketSector, SectorFilter


def _make_kline(symbol: str, n: int = 5) -> dict[str, pd.DataFrame]:
    """Create minimal kline data for testing."""
    dates = pd.date_range("2024-01-01", periods=n, freq="1D")
    return {
        "Open": pd.DataFrame({symbol: np.arange(n, dtype=float) + 10}),
        "High": pd.DataFrame({symbol: np.arange(n, dtype=float) + 11}),
        "Low": pd.DataFrame({symbol: np.arange(n, dtype=float) + 9}),
        "Close": pd.DataFrame({symbol: np.arange(n, dtype=float) + 10.5}),
        "Volume": pd.DataFrame({symbol: np.arange(n, dtype=float) * 1000}),
    }


@pytest.fixture
def mock_tq() -> MagicMock:
    return MagicMock()


@pytest.fixture
def tdx_provider(mock_tq: MagicMock) -> TdxDataProvider:
    provider = TdxDataProvider.__new__(TdxDataProvider)
    provider.tq = mock_tq
    return provider


class TestMapTimeframe:
    def test_1d(self) -> None:
        assert TdxDataProvider._map_timeframe("1d") == "1d"

    def test_none(self) -> None:
        assert TdxDataProvider._map_timeframe(None) == "1d"

    def test_unknown(self) -> None:
        assert TdxDataProvider._map_timeframe("2h") == "1d"

    def test_1h(self) -> None:
        assert TdxDataProvider._map_timeframe("1h") == "1h"


class TestConvertKlineToDataFrame:
    def test_basic_conversion(self) -> None:
        kline = _make_kline("600519.SH", n=3)
        df = TdxDataProvider._convert_kline_to_dataframe(kline, "600519.SH")
        assert len(df) == 3
        assert "open" in df.columns
        assert "close" in df.columns
        assert "symbol" in df.columns
        assert "date" in df.columns
        assert (df["symbol"] == "600519.SH").all()

    def test_empty_kline(self) -> None:
        df = TdxDataProvider._convert_kline_to_dataframe({}, "600519.SH")
        assert df.empty
        assert "symbol" in df.columns


class TestMergeIndicatorResult:
    def test_single_output(self) -> None:
        df = pd.DataFrame({"close": [10.0, 11.0, 12.0]})
        ind = IndicatorDef("RSI", {"period": 14})
        result = {"Value": {"value": ["1.0", "2.0", "3.0"]}}
        TdxDataProvider._merge_indicator_result(df, result, ind, bar_count=3)
        assert "RSI_14" in df.columns
        assert df["RSI_14"].tolist() == [1.0, 2.0, 3.0]

    def test_multi_output(self) -> None:
        df = pd.DataFrame({"close": [10.0, 11.0, 12.0]})
        ind = IndicatorDef("KDJ", {"k_period": 9}, outputs=("K", "D", "J"))
        result = {"Value": {"K": ["1.0", "2.0", "3.0"], "D": ["4.0", "5.0", "6.0"], "J": ["7.0", "8.0", "9.0"]}}
        TdxDataProvider._merge_indicator_result(df, result, ind, bar_count=3)
        assert "KDJ_K" in df.columns
        assert "KDJ_D" in df.columns
        assert "KDJ_J" in df.columns

    def test_none_values_become_nan(self) -> None:
        df = pd.DataFrame({"close": [10.0, 11.0, 12.0]})
        ind = IndicatorDef("RSI", {"period": 14})
        result = {"Value": {"value": [None, "2.0", "3.0"]}}
        TdxDataProvider._merge_indicator_result(df, result, ind, bar_count=3)
        assert np.isnan(df["RSI_14"].iloc[0])
        assert df["RSI_14"].iloc[1] == 2.0

    def test_empty_result(self) -> None:
        df = pd.DataFrame({"close": [10.0]})
        ind = IndicatorDef("RSI", {"period": 14})
        TdxDataProvider._merge_indicator_result(df, {}, ind, bar_count=1)
        assert "RSI_14" not in df.columns

    def test_truncates_to_bar_count(self) -> None:
        df = pd.DataFrame({"close": [10.0, 11.0, 12.0]})
        ind = IndicatorDef("RSI", {"period": 14})
        result = {"Value": {"value": ["0.0", "1.0", "2.0", "3.0"]}}
        TdxDataProvider._merge_indicator_result(df, result, ind, bar_count=3)
        assert df["RSI_14"].tolist() == [1.0, 2.0, 3.0]


class TestFetchStockData:
    def test_single_stock_no_indicators(
        self, tdx_provider: TdxDataProvider, mock_tq: MagicMock
    ) -> None:
        kline = _make_kline("600519.SH", n=3)
        mock_tq.get_market_data.return_value = kline
        result = tdx_provider.fetch_stock_data(
            symbols=frozenset(["600519.SH"]),
            start_date=datetime(2024, 1, 1),
            end_date=datetime(2024, 1, 31),
            timeframe="1d",
            indicators=[],
        )
        assert len(result) == 3
        assert "close" in result.columns

    def test_single_stock_with_indicators(
        self, tdx_provider: TdxDataProvider, mock_tq: MagicMock
    ) -> None:
        symbol = "600519.SH"
        kline = _make_kline(symbol, n=3)
        formatted = {symbol: list(range(3))}
        zb_result = {"Value": {"value": ["1.0", "2.0", "3.0"]}}
        ind_def = RSI(14)

        mock_tq.get_market_data.return_value = kline
        mock_tq.formula_format_data.return_value = formatted
        mock_tq.formula_zb.return_value = zb_result

        result = tdx_provider.fetch_stock_data(
            symbols=frozenset([symbol]),
            start_date=datetime(2024, 1, 1),
            end_date=datetime(2024, 1, 31),
            timeframe="1d",
            indicators=[ind_def],
        )
        assert "RSI_14" in result.columns
        assert len(result) == 3

    def test_empty_result_on_bad_price(
        self, tdx_provider: TdxDataProvider, mock_tq: MagicMock
    ) -> None:
        symbol = "600519.SH"
        kline = {
            "Open": pd.DataFrame({symbol: [0.0]}),
            "High": pd.DataFrame({symbol: [0.0]}),
            "Low": pd.DataFrame({symbol: [0.0]}),
            "Close": pd.DataFrame({symbol: [0.0]}),
            "Volume": pd.DataFrame({symbol: [0.0]}),
        }
        mock_tq.get_market_data.return_value = kline
        result = tdx_provider.fetch_stock_data(
            symbols=frozenset([symbol]),
            start_date=datetime(2024, 1, 1),
            end_date=datetime(2024, 1, 31),
            timeframe="1d",
            indicators=[],
        )
        assert len(result) == 0


class TestResolveSector:
    def test_returns_codes_without_filter(
        self, tdx_provider: TdxDataProvider, mock_tq: MagicMock
    ) -> None:
        mock_tq.get_stock_list.return_value = ["600519.SH", "000858.SZ"]
        result = tdx_provider.resolve_sector(MarketSector.ALL)
        assert result == ["600519.SH", "000858.SZ"]

    def test_empty_sector(self, tdx_provider: TdxDataProvider, mock_tq: MagicMock) -> None:
        mock_tq.get_stock_list.return_value = []
        result = tdx_provider.resolve_sector(MarketSector.CHINEXT)
        assert result == []

    def test_max_stocks_limit(
        self, tdx_provider: TdxDataProvider, mock_tq: MagicMock
    ) -> None:
        codes = [f"60000{i}.SH" for i in range(10)]
        mock_tq.get_stock_list.return_value = codes
        result = tdx_provider.resolve_sector(
            MarketSector.ALL,
            sector_filter=SectorFilter(max_stocks=3),
        )
        assert len(result) == 3
