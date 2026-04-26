"""Tests for DataProvider ABC constraints."""

from unittest.mock import MagicMock

import pandas as pd
import pytest

from stablemoney.data_providers.data_provider import DataProvider


class _PartialProvider(DataProvider):
    """Only implements fetch_stock_data."""

    def fetch_stock_data(self, symbols, start_date, end_date, timeframe, indicators):
        return pd.DataFrame()

    # Missing: resolve_sector


class _FullProvider(DataProvider):
    def fetch_stock_data(self, symbols, start_date, end_date, timeframe, indicators):
        return pd.DataFrame()

    def resolve_sector(self, sector, sector_filter=None):
        return []


def test_cannot_instantiate_abc():
    with pytest.raises(TypeError):
        DataProvider()  # type: ignore[abstract]


def test_partial_subclass_raises():
    with pytest.raises(TypeError):
        _PartialProvider()  # type: ignore[abstract]


def test_full_subclass_instantiates():
    provider = _FullProvider()
    assert isinstance(provider, DataProvider)


def test_full_subclass_methods_callable():
    provider = _FullProvider()
    result_df = provider.fetch_stock_data(
        frozenset(), MagicMock(), MagicMock(), None, []
    )
    assert isinstance(result_df, pd.DataFrame)

    result_list = provider.resolve_sector(MagicMock())
    assert isinstance(result_list, list)
