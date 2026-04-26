"""Tests for TdxDataSource — delegation to DataProvider and init."""

from __future__ import annotations

from datetime import datetime
from unittest.mock import MagicMock, patch

import pandas as pd

from stablemoney.data_providers.data_provider import DataProvider
from stablemoney.data_sources.tdx_data_source import TdxDataSource
from stablemoney.indicators import MA, RSI


class TestInit:
    @patch("stablemoney.data_sources.tdx_data_source.StaticScope")
    def test_accepts_injected_provider(self, mock_scope_cls: MagicMock) -> None:
        mock_scope = MagicMock()
        mock_scope_cls.instance.return_value = mock_scope
        mock_provider = MagicMock(spec=DataProvider)

        TdxDataSource(indicators=[RSI(14)], data_provider=mock_provider)

        mock_scope.register_custom_cols.assert_called_once_with(["RSI_14"])

    @patch("stablemoney.data_sources.tdx_data_source.StaticScope")
    def test_creates_tdx_provider_when_not_injected(
        self, mock_scope_cls: MagicMock
    ) -> None:
        mock_scope = MagicMock()
        mock_scope_cls.instance.return_value = mock_scope

        mock_provider = MagicMock()
        with patch(
            "stablemoney.data_providers.tdx_data_provider.TdxDataProvider",
            return_value=mock_provider,
        ):
            ds = TdxDataSource(indicators=[], tdx_dir="/some/path")
            assert ds._data_provider is mock_provider

    @patch("stablemoney.data_sources.tdx_data_source.StaticScope")
    def test_registers_custom_columns(self, mock_scope_cls: MagicMock) -> None:
        mock_scope = MagicMock()
        mock_scope_cls.instance.return_value = mock_scope
        mock_provider = MagicMock(spec=DataProvider)

        TdxDataSource(indicators=[RSI(14), MA(20)], data_provider=mock_provider)

        mock_scope.register_custom_cols.assert_called_once_with(["RSI_14", "MA_20"])

    @patch("stablemoney.data_sources.tdx_data_source.StaticScope")
    def test_no_indicators(self, mock_scope_cls: MagicMock) -> None:
        mock_scope = MagicMock()
        mock_scope_cls.instance.return_value = mock_scope
        mock_provider = MagicMock(spec=DataProvider)

        TdxDataSource(indicators=None, data_provider=mock_provider)

        mock_scope.register_custom_cols.assert_not_called()


class TestFetchData:
    @patch("stablemoney.data_sources.tdx_data_source.StaticScope")
    def test_delegates_to_provider(self, mock_scope_cls: MagicMock) -> None:
        mock_scope = MagicMock()
        mock_scope_cls.instance.return_value = mock_scope
        mock_provider = MagicMock(spec=DataProvider)
        expected_df = pd.DataFrame(
            {"symbol": ["600519.SH"], "date": [datetime(2024, 1, 1)]}
        )
        mock_provider.fetch_stock_data.return_value = expected_df

        ds = TdxDataSource(indicators=[RSI(14)], data_provider=mock_provider)
        result = ds._fetch_data(
            symbols=frozenset(["600519.SH"]),
            start_date=datetime(2024, 1, 1),
            end_date=datetime(2024, 1, 31),
            timeframe="1d",
            adjust=None,
        )

        assert result is expected_df
        mock_provider.fetch_stock_data.assert_called_once_with(
            symbols=frozenset(["600519.SH"]),
            start_date=datetime(2024, 1, 1),
            end_date=datetime(2024, 1, 31),
            timeframe="1d",
            indicators=[RSI(14)],
        )

    @patch("stablemoney.data_sources.tdx_data_source.StaticScope")
    def test_passes_indicators(self, mock_scope_cls: MagicMock) -> None:
        mock_scope = MagicMock()
        mock_scope_cls.instance.return_value = mock_scope
        mock_provider = MagicMock(spec=DataProvider)
        mock_provider.fetch_stock_data.return_value = pd.DataFrame(
            columns=["symbol", "date"]
        )

        indicators = [RSI(14), MA(20)]
        ds = TdxDataSource(indicators=indicators, data_provider=mock_provider)
        ds._fetch_data(
            symbols=frozenset(["600519.SH"]),
            start_date=datetime(2024, 1, 1),
            end_date=datetime(2024, 1, 31),
            timeframe="1d",
            adjust=None,
        )

        call_kwargs = mock_provider.fetch_stock_data.call_args
        assert call_kwargs.kwargs["indicators"] == indicators
