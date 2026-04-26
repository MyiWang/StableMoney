"""Tests for TdxDataProvider — static helpers, init, fetch, and sector resolution."""

from __future__ import annotations

import sys
from datetime import datetime
from unittest.mock import MagicMock, patch

import numpy as np
import pandas as pd
import pytest

from stablemoney.indicator_def import IndicatorDef
from stablemoney.indicators import MA, RSI
from stablemoney.market_sector import MarketSector, SectorFilter
from stablemoney.data_providers.tdx_data_provider import TdxDataProvider


# ---------------------------------------------------------------------------
# Static method tests (middle layer, pure logic)
# ---------------------------------------------------------------------------


class TestMapTimeframe:
    def test_known_values(self) -> None:
        expected = {
            "1d": "1d",
            "1w": "1w",
            "1mon": "1mon",
            "1h": "1h",
            "30m": "30m",
            "15m": "15m",
            "5m": "5m",
            "1m": "1m",
        }
        for inp, out in expected.items():
            assert TdxDataProvider._map_timeframe(inp) == out

    def test_none_returns_default(self) -> None:
        assert TdxDataProvider._map_timeframe(None) == "1d"

    def test_unknown_returns_default(self) -> None:
        assert TdxDataProvider._map_timeframe("2d") == "1d"


class TestConvertKlineToDataframe:
    def _make_kline(
        self,
        symbol: str = "600519.SH",
        n: int = 3,
    ) -> dict[str, pd.DataFrame]:
        dates = pd.date_range("2024-01-01", periods=n, freq="1D")
        return {
            "Open": pd.DataFrame({symbol: [10.0, 11.0, 12.0]}, index=dates),
            "High": pd.DataFrame({symbol: [10.5, 11.5, 12.5]}, index=dates),
            "Low": pd.DataFrame({symbol: [9.5, 10.5, 11.5]}, index=dates),
            "Close": pd.DataFrame({symbol: [10.2, 11.2, 12.2]}, index=dates),
            "Volume": pd.DataFrame({symbol: [1000, 2000, 3000]}, index=dates),
        }

    def test_basic(self) -> None:
        kline = self._make_kline()
        df = TdxDataProvider._convert_kline_to_dataframe(kline, "600519.SH")
        assert list(df.columns) == [
            "open",
            "high",
            "low",
            "close",
            "volume",
            "date",
            "symbol",
        ]
        assert len(df) == 3
        assert df["symbol"].iloc[0] == "600519.SH"
        assert df["close"].iloc[0] == 10.2

    def test_missing_volume(self) -> None:
        kline = self._make_kline()
        del kline["Volume"]
        df = TdxDataProvider._convert_kline_to_dataframe(kline, "600519.SH")
        assert "volume" not in df.columns
        assert "close" in df.columns

    def test_empty(self) -> None:
        df = TdxDataProvider._convert_kline_to_dataframe({}, "600519.SH")
        assert list(df.columns) == ["symbol", "date"]
        assert df.empty


class TestMergeIndicatorResult:
    def _make_df(self, n: int = 5) -> pd.DataFrame:
        return pd.DataFrame(
            {
                "date": pd.date_range("2024-01-01", periods=n),
                "symbol": ["600519.SH"] * n,
            }
        )

    def test_single_output(self) -> None:
        df = self._make_df(5)
        ind = IndicatorDef("RSI", {"period": 14})
        result = {"Value": {"value": ["1.0", "2.0", "3.0", "4.0", "5.0"]}}
        TdxDataProvider._merge_indicator_result(df, result, ind, bar_count=5)
        assert "RSI_14" in df.columns
        assert df["RSI_14"].tolist() == [1.0, 2.0, 3.0, 4.0, 5.0]

    def test_multi_output(self) -> None:
        df = self._make_df(3)
        ind = IndicatorDef(
            "KDJ",
            {"k_period": 9, "k_smooth": 3, "d_smooth": 3},
            outputs=("K", "D", "J"),
        )
        result = {
            "Value": {
                "K": ["10.0", "20.0", "30.0"],
                "D": ["15.0", "25.0", "35.0"],
                "J": ["5.0", "15.0", "25.0"],
            }
        }
        TdxDataProvider._merge_indicator_result(df, result, ind, bar_count=3)
        assert "KDJ_K" in df.columns
        assert "KDJ_D" in df.columns
        assert "KDJ_J" in df.columns
        assert df["KDJ_K"].tolist() == [10.0, 20.0, 30.0]

    def test_truncates_to_bar_count(self) -> None:
        df = self._make_df(3)
        ind = IndicatorDef("RSI", {"period": 14})
        result = {"Value": {"value": ["1.0", "2.0", "3.0", "4.0", "5.0"]}}
        TdxDataProvider._merge_indicator_result(df, result, ind, bar_count=3)
        assert df["RSI_14"].tolist() == [3.0, 4.0, 5.0]

    def test_none_values_become_nan(self) -> None:
        df = self._make_df(3)
        ind = IndicatorDef("RSI", {"period": 14})
        result = {"Value": {"value": ["1.0", None, "3.0"]}}
        TdxDataProvider._merge_indicator_result(df, result, ind, bar_count=3)
        assert df["RSI_14"].iloc[0] == 1.0
        assert np.isnan(df["RSI_14"].iloc[1])
        assert df["RSI_14"].iloc[2] == 3.0

    def test_empty_result(self) -> None:
        df = self._make_df(3)
        ind = IndicatorDef("RSI", {"period": 14})
        TdxDataProvider._merge_indicator_result(df, {}, ind, bar_count=3)
        assert "RSI_14" not in df.columns

    def test_no_value_key(self) -> None:
        df = self._make_df(3)
        ind = IndicatorDef("RSI", {"period": 14})
        TdxDataProvider._merge_indicator_result(
            df, {"Other": {}}, ind, bar_count=3
        )
        assert "RSI_14" not in df.columns


# ---------------------------------------------------------------------------
# Init tests
# ---------------------------------------------------------------------------


class TestInit:
    def test_tdx_dir_initializes_tq(self) -> None:
        mock_tq = MagicMock()
        mock_tqcenter = MagicMock()
        mock_tqcenter.tq = mock_tq
        with patch.dict(
            "sys.modules",
            {"tqcenter": mock_tqcenter, "tqcenter.tq": mock_tq},
        ):
            provider = TdxDataProvider(tdx_dir="/some/path")
            mock_tq.initialize.assert_called_once()
            assert provider._tq is mock_tq

    def test_no_tdx_dir_defers_import(self) -> None:
        provider = TdxDataProvider(tdx_dir=None)
        assert provider._tq is None

    @patch("sys.path")
    def test_tdx_dir_adds_to_sys_path(self, mock_sys_path: MagicMock) -> None:
        mock_sys_path.__contains__ = MagicMock(return_value=False)
        with patch.dict(
            "sys.modules",
            {"tqcenter": MagicMock(), "tqcenter.tq": MagicMock()},
        ):
            TdxDataProvider(tdx_dir="/some/path")
            mock_sys_path.insert.assert_called_with(0, "/some/path")


# ---------------------------------------------------------------------------
# fetch_stock_data tests (top layer, mocking bottom layer)
# ---------------------------------------------------------------------------


class TestFetchStockData:
    def _make_kline(self, symbol: str, n: int = 3) -> dict[str, pd.DataFrame]:
        dates = pd.date_range("2024-01-01", periods=n, freq="1D")
        return {
            "Open": pd.DataFrame({symbol: [10.0 + i for i in range(n)]}, index=dates),
            "High": pd.DataFrame({symbol: [10.5 + i for i in range(n)]}, index=dates),
            "Low": pd.DataFrame({symbol: [9.5 + i for i in range(n)]}, index=dates),
            "Close": pd.DataFrame({symbol: [10.2 + i for i in range(n)]}, index=dates),
            "Volume": pd.DataFrame(
                {symbol: [1000 * (i + 1) for i in range(n)]}, index=dates
            ),
        }

    def test_single_stock_no_indicators(self) -> None:
        provider = TdxDataProvider.__new__(TdxDataProvider)
        provider._tq = None
        kline = self._make_kline("600519.SH")

        with patch.object(provider, "_raw_get_market_data", return_value=kline):
            result = provider.fetch_stock_data(
                symbols=frozenset(["600519.SH"]),
                start_date=datetime(2024, 1, 1),
                end_date=datetime(2024, 1, 31),
                timeframe="1d",
                indicators=[],
            )

        assert len(result) == 3
        assert "symbol" in result.columns
        assert "date" in result.columns
        assert result["symbol"].iloc[0] == "600519.SH"

    def test_single_stock_with_indicators(self) -> None:
        provider = TdxDataProvider.__new__(TdxDataProvider)
        provider._tq = None
        symbol = "600519.SH"
        kline = self._make_kline(symbol, n=3)

        formatted = {symbol: list(range(3))}
        zb_result = {"Value": {"value": ["1.0", "2.0", "3.0"]}}
        ind_def = IndicatorDef("RSI", {"period": 14})

        with (
            patch.object(provider, "_raw_get_market_data", return_value=kline),
            patch.object(provider, "_raw_formula_format_data", return_value=formatted),
            patch.object(provider, "_raw_formula_set_data"),
            patch.object(provider, "_raw_formula_zb", return_value=zb_result),
        ):
            result = provider.fetch_stock_data(
                symbols=frozenset([symbol]),
                start_date=datetime(2024, 1, 1),
                end_date=datetime(2024, 1, 31),
                timeframe="1d",
                indicators=[ind_def],
            )

        assert "RSI_14" in result.columns
        assert len(result) == 3

    def test_empty_kline_returns_empty_df(self) -> None:
        provider = TdxDataProvider.__new__(TdxDataProvider)
        provider._tq = None

        with patch.object(provider, "_raw_get_market_data", return_value={}):
            result = provider.fetch_stock_data(
                symbols=frozenset(["600519.SH"]),
                start_date=datetime(2024, 1, 1),
                end_date=datetime(2024, 1, 31),
                timeframe="1d",
                indicators=[],
            )

        assert result.empty
        assert "symbol" in result.columns
        assert "date" in result.columns

    def test_multiple_stocks_concatenated(self) -> None:
        provider = TdxDataProvider.__new__(TdxDataProvider)
        provider._tq = None
        kline_a = self._make_kline("A.SH", n=2)
        kline_b = self._make_kline("B.SZ", n=2)

        with (
            patch.object(
                provider,
                "_raw_get_market_data",
                side_effect=[kline_a, kline_b],
            ),
        ):
            result = provider.fetch_stock_data(
                symbols=frozenset(["B.SZ", "A.SH"]),
                start_date=datetime(2024, 1, 1),
                end_date=datetime(2024, 1, 31),
                timeframe="1d",
                indicators=[],
            )

        assert len(result) == 4
        symbols_in_result = set(result["symbol"].unique())
        assert symbols_in_result == {"A.SH", "B.SZ"}


# ---------------------------------------------------------------------------
# resolve_sector tests (top layer, mocking bottom layer)
# ---------------------------------------------------------------------------


class TestResolveSector:
    def test_returns_all_codes(self) -> None:
        provider = TdxDataProvider.__new__(TdxDataProvider)
        provider._tq = None

        with (
            patch.object(
                provider,
                "_raw_get_stock_list",
                return_value=["300001.SZ", "300002.SZ", "300003.SZ"],
            ),
        ):
            result = provider.resolve_sector(MarketSector.CHINEXT, None)

        assert result == ["300001.SZ", "300002.SZ", "300003.SZ"]

    def test_max_stocks_without_sort(self) -> None:
        provider = TdxDataProvider.__new__(TdxDataProvider)
        provider._tq = None

        with (
            patch.object(
                provider,
                "_raw_get_stock_list",
                return_value=["300001.SZ", "300002.SZ", "300003.SZ", "300004.SZ"],
            ),
        ):
            sf = SectorFilter(max_stocks=2)
            result = provider.resolve_sector(MarketSector.CHINEXT, sf)

        assert result == ["300001.SZ", "300002.SZ"]

    def test_sort_and_limit(self) -> None:
        provider = TdxDataProvider.__new__(TdxDataProvider)
        provider._tq = None

        close_df = pd.DataFrame(
            {"A.SH": [10.0], "B.SZ": [5.0], "C.SH": [20.0]},
            index=pd.DatetimeIndex(["2025-01-01"]),
        )
        kline_result = {"Close": close_df}

        with (
            patch.object(
                provider, "_raw_get_stock_list", return_value=["A.SH", "B.SZ", "C.SH"]
            ),
            patch.object(
                provider, "_raw_get_market_data", return_value=kline_result
            ),
            patch.object(
                provider,
                "_raw_get_stock_info",
                side_effect=[{"J_zgb": "30000"}, {"J_zgb": "10000"}, {"J_zgb": "5000"}],
            ),
        ):
            sf = SectorFilter(max_stocks=2, sort_by="market_cap", sort_ascending=False)
            result = provider.resolve_sector(MarketSector.ALL, sf)

        # A=30亿, B=5亿, C=10亿, sorted desc: A, C, B, top 2: A, C
        assert result == ["A.SH", "C.SH"]

    def test_sort_ascending(self) -> None:
        provider = TdxDataProvider.__new__(TdxDataProvider)
        provider._tq = None

        close_df = pd.DataFrame(
            {"A.SH": [10.0], "B.SZ": [5.0]},
            index=pd.DatetimeIndex(["2025-01-01"]),
        )

        with (
            patch.object(
                provider, "_raw_get_stock_list", return_value=["A.SH", "B.SZ"]
            ),
            patch.object(
                provider,
                "_raw_get_market_data",
                return_value={"Close": close_df},
            ),
            patch.object(
                provider,
                "_raw_get_stock_info",
                side_effect=[{"J_zgb": "30000"}, {"J_zgb": "10000"}],
            ),
        ):
            sf = SectorFilter(sort_by="market_cap", sort_ascending=True)
            result = provider.resolve_sector(MarketSector.ALL, sf)

        assert result == ["B.SZ", "A.SH"]

    def test_empty_codes(self) -> None:
        provider = TdxDataProvider.__new__(TdxDataProvider)
        provider._tq = None

        with patch.object(provider, "_raw_get_stock_list", return_value=[]):
            result = provider.resolve_sector(MarketSector.BSE, None)

        assert result == []

    def test_handles_failed_stock_info(self) -> None:
        provider = TdxDataProvider.__new__(TdxDataProvider)
        provider._tq = None

        close_df = pd.DataFrame(
            {"A.SH": [10.0], "B.SZ": [5.0]},
            index=pd.DatetimeIndex(["2025-01-01"]),
        )

        with (
            patch.object(
                provider, "_raw_get_stock_list", return_value=["A.SH", "B.SZ"]
            ),
            patch.object(
                provider,
                "_raw_get_market_data",
                return_value={"Close": close_df},
            ),
            patch.object(
                provider,
                "_raw_get_stock_info",
                side_effect=[Exception("error"), {"J_zgb": "10000"}],
            ),
        ):
            sf = SectorFilter(sort_by="market_cap", sort_ascending=True)
            result = provider.resolve_sector(MarketSector.ALL, sf)

        assert result == ["B.SZ"]

    def test_market_cap_range_filter(self) -> None:
        provider = TdxDataProvider.__new__(TdxDataProvider)
        provider._tq = None

        close_df = pd.DataFrame(
            {"A.SH": [5.0], "B.SZ": [10.0], "C.SH": [20.0], "D.SZ": [50.0]},
            index=pd.DatetimeIndex(["2025-01-01"]),
        )

        with (
            patch.object(
                provider,
                "_raw_get_stock_list",
                return_value=["A.SH", "B.SZ", "C.SH", "D.SZ"],
            ),
            patch.object(
                provider,
                "_raw_get_market_data",
                return_value={"Close": close_df},
            ),
            patch.object(
                provider,
                "_raw_get_stock_info",
                side_effect=[
                    {"J_zgb": "6000"},
                    {"J_zgb": "4000"},
                    {"J_zgb": "2000"},
                    {"J_zgb": "10000"},
                ],
            ),
        ):
            sf = SectorFilter(
                sort_by="market_cap",
                sort_ascending=False,
                min_market_cap=3.5,
                max_market_cap=10.0,
            )
            result = provider.resolve_sector(MarketSector.ALL, sf)

        # Sorted desc: D=50, B=4, C=4, A=3. Range [3.5, 10]: B=4, C=4
        assert result == ["B.SZ", "C.SH"]

    def test_market_cap_range_with_max_stocks(self) -> None:
        provider = TdxDataProvider.__new__(TdxDataProvider)
        provider._tq = None

        close_df = pd.DataFrame(
            {"A.SH": [5.0], "B.SZ": [10.0], "C.SH": [20.0]},
            index=pd.DatetimeIndex(["2025-01-01"]),
        )

        with (
            patch.object(
                provider,
                "_raw_get_stock_list",
                return_value=["A.SH", "B.SZ", "C.SH"],
            ),
            patch.object(
                provider,
                "_raw_get_market_data",
                return_value={"Close": close_df},
            ),
            patch.object(
                provider,
                "_raw_get_stock_info",
                side_effect=[
                    {"J_zgb": "6000"},
                    {"J_zgb": "4000"},
                    {"J_zgb": "2000"},
                ],
            ),
        ):
            sf = SectorFilter(
                sort_by="market_cap",
                sort_ascending=False,
                min_market_cap=3.5,
                max_stocks=1,
            )
            result = provider.resolve_sector(MarketSector.ALL, sf)

        # Sorted desc: B=4, C=4, A=3. Range >=3.5: B,C. max_stocks=1: [B.SZ]
        assert result == ["B.SZ"]
