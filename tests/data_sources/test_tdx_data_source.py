"""Tests for TdxDataSource — static helpers and mocked init/fetch."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import numpy as np
import pandas as pd

from stablemoney.data_sources.tdx_data_source import TdxDataSource
from stablemoney.indicator_def import IndicatorDef
from stablemoney.indicators import MA, RSI

# ---------------------------------------------------------------------------
# Static method tests (pure logic, no mocking)
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
            assert TdxDataSource._map_timeframe(inp) == out

    def test_none_returns_default(self) -> None:
        assert TdxDataSource._map_timeframe(None) == "1d"

    def test_unknown_returns_default(self) -> None:
        assert TdxDataSource._map_timeframe("2d") == "1d"


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
        df = TdxDataSource._convert_kline_to_dataframe(kline, "600519.SH")
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
        df = TdxDataSource._convert_kline_to_dataframe(kline, "600519.SH")
        assert "volume" not in df.columns
        assert "close" in df.columns

    def test_empty(self) -> None:
        df = TdxDataSource._convert_kline_to_dataframe({}, "600519.SH")
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
        TdxDataSource._merge_indicator_result(df, result, ind, bar_count=5)
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
        TdxDataSource._merge_indicator_result(df, result, ind, bar_count=3)
        assert "KDJ_K" in df.columns
        assert "KDJ_D" in df.columns
        assert "KDJ_J" in df.columns
        assert df["KDJ_K"].tolist() == [10.0, 20.0, 30.0]

    def test_truncates_to_bar_count(self) -> None:
        df = self._make_df(3)
        ind = IndicatorDef("RSI", {"period": 14})
        # 5 values, but bar_count=3 -> take last 3
        result = {"Value": {"value": ["1.0", "2.0", "3.0", "4.0", "5.0"]}}
        TdxDataSource._merge_indicator_result(df, result, ind, bar_count=3)
        assert df["RSI_14"].tolist() == [3.0, 4.0, 5.0]

    def test_none_values_become_nan(self) -> None:
        df = self._make_df(3)
        ind = IndicatorDef("RSI", {"period": 14})
        result = {"Value": {"value": ["1.0", None, "3.0"]}}
        TdxDataSource._merge_indicator_result(df, result, ind, bar_count=3)
        assert df["RSI_14"].iloc[0] == 1.0
        assert np.isnan(df["RSI_14"].iloc[1])
        assert df["RSI_14"].iloc[2] == 3.0

    def test_empty_result(self) -> None:
        df = self._make_df(3)
        ind = IndicatorDef("RSI", {"period": 14})
        TdxDataSource._merge_indicator_result(df, {}, ind, bar_count=3)
        assert "RSI_14" not in df.columns

    def test_no_value_key(self) -> None:
        df = self._make_df(3)
        ind = IndicatorDef("RSI", {"period": 14})
        TdxDataSource._merge_indicator_result(df, {"Other": {}}, ind, bar_count=3)
        assert "RSI_14" not in df.columns


# ---------------------------------------------------------------------------
# Init tests (mocking StaticScope and tq)
# ---------------------------------------------------------------------------


class TestInit:
    @patch("stablemoney.data_sources.tdx_data_source.TdxDataSource._init_tdx")
    @patch("stablemoney.data_sources.tdx_data_source.StaticScope")
    def test_registers_custom_columns(
        self,
        mock_scope_cls: MagicMock,
        mock_init_tdx: MagicMock,
    ) -> None:
        mock_scope = MagicMock()
        mock_scope_cls.instance.return_value = mock_scope

        TdxDataSource(indicators=[RSI(14), MA(20)], tdx_dir=None)

        mock_scope.register_custom_cols.assert_called_once_with(["RSI_14", "MA_20"])

    @patch("stablemoney.data_sources.tdx_data_source.TdxDataSource._init_tdx")
    @patch("stablemoney.data_sources.tdx_data_source.StaticScope")
    def test_no_indicators(
        self,
        mock_scope_cls: MagicMock,
        mock_init_tdx: MagicMock,
    ) -> None:
        mock_scope = MagicMock()
        mock_scope_cls.instance.return_value = mock_scope

        TdxDataSource(indicators=None, tdx_dir=None)

        mock_scope.register_custom_cols.assert_not_called()

    @patch(
        "stablemoney.data_sources.tdx_data_source.TdxDataSource._register_custom_columns"
    )
    @patch("sys.path")
    def test_tdx_dir_adds_to_sys_path(
        self,
        mock_sys_path: MagicMock,
        mock_register: MagicMock,
    ) -> None:
        mock_sys_path.__contains__ = MagicMock(return_value=False)

        # We need to also mock tq.initialize since _init_tdx imports it
        with patch.dict(
            "sys.modules", {"tqcenter": MagicMock(), "tqcenter.tq": MagicMock()}
        ):
            TdxDataSource(indicators=[], tdx_dir="/some/path")

        mock_sys_path.insert.assert_called()

    @patch(
        "stablemoney.data_sources.tdx_data_source.TdxDataSource._register_custom_columns"
    )
    def test_tdx_dir_calls_tq_initialize(
        self,
        mock_register: MagicMock,
    ) -> None:
        mock_tq = MagicMock()
        mock_tqcenter = MagicMock()
        mock_tqcenter.tq = mock_tq
        with patch.dict(
            "sys.modules", {"tqcenter": mock_tqcenter, "tqcenter.tq": mock_tq}
        ):
            TdxDataSource(indicators=[], tdx_dir="/some/path")

        mock_tq.initialize.assert_called_once()


# ---------------------------------------------------------------------------
# _fetch_data tests (heavy TDX mocking)
# ---------------------------------------------------------------------------


class TestFetchData:
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

    @patch("stablemoney.data_sources.tdx_data_source.TdxDataSource._init_tdx")
    @patch("stablemoney.data_sources.tdx_data_source.StaticScope")
    def test_single_stock_no_indicators(
        self,
        mock_scope_cls: MagicMock,
        mock_init_tdx: MagicMock,
    ) -> None:
        mock_scope = MagicMock()
        mock_scope_cls.instance.return_value = mock_scope

        ds = TdxDataSource(indicators=[], tdx_dir=None)
        kline = self._make_kline("600519.SH")

        mock_tq = MagicMock()
        mock_tq.get_market_data.return_value = kline
        mock_tqcenter = MagicMock()
        mock_tqcenter.tq = mock_tq

        with patch.dict(
            "sys.modules", {"tqcenter": mock_tqcenter, "tqcenter.tq": mock_tq}
        ):
            from datetime import datetime

            result = ds._fetch_data(
                symbols=frozenset(["600519.SH"]),
                start_date=datetime(2024, 1, 1),
                end_date=datetime(2024, 1, 31),
                timeframe="1d",
                adjust=None,
            )

        assert len(result) == 3
        assert "symbol" in result.columns
        assert "date" in result.columns
        assert result["symbol"].iloc[0] == "600519.SH"

    @patch("stablemoney.data_sources.tdx_data_source.TdxDataSource._init_tdx")
    @patch("stablemoney.data_sources.tdx_data_source.StaticScope")
    def test_empty_result_returns_empty_df(
        self,
        mock_scope_cls: MagicMock,
        mock_init_tdx: MagicMock,
    ) -> None:
        mock_scope = MagicMock()
        mock_scope_cls.instance.return_value = mock_scope

        ds = TdxDataSource(indicators=[], tdx_dir=None)

        mock_tq = MagicMock()
        mock_tq.get_market_data.return_value = {}  # empty kline
        mock_tqcenter = MagicMock()
        mock_tqcenter.tq = mock_tq

        with patch.dict(
            "sys.modules", {"tqcenter": mock_tqcenter, "tqcenter.tq": mock_tq}
        ):
            from datetime import datetime

            result = ds._fetch_data(
                symbols=frozenset(["600519.SH"]),
                start_date=datetime(2024, 1, 1),
                end_date=datetime(2024, 1, 31),
                timeframe="1d",
                adjust=None,
            )

        assert result.empty
        assert "symbol" in result.columns
        assert "date" in result.columns
