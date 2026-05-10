"""Tests for TdxDataSource."""

from __future__ import annotations

from datetime import datetime
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest
from stablemoney.data_sources.tdx_data_source import TdxDataSource
from stablemoney.indicators import MA, RSI


@pytest.fixture
def mock_scope() -> MagicMock:
    with patch("stablemoney.data_sources.tdx_data_source.StaticScope") as mock:
        scope = MagicMock()
        mock.instance.return_value = scope
        yield scope


@pytest.fixture
def mock_provider() -> MagicMock:
    return MagicMock()


@pytest.fixture
def ds_with_rsi(mock_scope: MagicMock, mock_provider: MagicMock) -> TdxDataSource:
    return TdxDataSource(indicators=[RSI(14)], data_provider=mock_provider)


class TestInit:
    def test_registers_custom_columns(self, mock_scope: MagicMock, mock_provider: MagicMock) -> None:
        TdxDataSource(indicators=[RSI(14), MA(20)], data_provider=mock_provider)
        mock_scope.register_custom_cols.assert_called_once()
        cols = mock_scope.register_custom_cols.call_args[0][0]
        assert "RSI_14" in cols
        assert "MA_20" in cols

    def test_no_columns_without_indicators(self, mock_scope: MagicMock, mock_provider: MagicMock) -> None:
        TdxDataSource(data_provider=mock_provider)
        mock_scope.register_custom_cols.assert_not_called()


class TestFetchData:
    def test_delegates_to_provider(
        self, ds_with_rsi: TdxDataSource, mock_provider: MagicMock
    ) -> None:
        expected_df = pd.DataFrame(
            {"symbol": ["600519.SH"], "date": [datetime(2024, 1, 1)]}
        )
        mock_provider.fetch_stock_data.return_value = expected_df

        result = ds_with_rsi._fetch_data(
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
