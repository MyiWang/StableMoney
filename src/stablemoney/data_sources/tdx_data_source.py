"""TDX (通达信) data source for PyBroker backtesting."""
from __future__ import annotations

from typing import TYPE_CHECKING, Any

from pybroker.data import DataSource
from pybroker.scope import StaticScope

if TYPE_CHECKING:
    from datetime import datetime

    import pandas as pd

    from stablemoney.data_providers.data_provider import DataProvider
    from stablemoney.indicator_def import IndicatorDef


class TdxDataSource(DataSource):
    """TDX (通达信) data source for PyBroker.

    Delegates data fetching to a ``DataProvider`` instance.
    When ``data_provider`` is not given, creates a ``TdxDataProvider``
    using ``tdx_dir`` (backward compatible).

    Example::

        ds = TdxDataSource(indicators=[RSI(14), MA(20)], data_provider=provider)
    """

    def __init__(
        self,
        indicators: list[IndicatorDef] | None = None,
        tdx_dir: str | None = None,
        data_provider: DataProvider | None = None,
    ) -> None:
        super().__init__()  # type: ignore[no-untyped-call]
        self._indicators: list[IndicatorDef] = indicators or []
        if data_provider is not None:
            self._data_provider = data_provider
        else:
            from stablemoney.data_providers.tdx_data_provider import TdxDataProvider

            self._data_provider = TdxDataProvider(tdx_dir=tdx_dir)
        self._register_custom_columns()

    def _register_custom_columns(self) -> None:
        """Register indicator column names as PyBroker custom columns."""
        if not self._indicators:
            return
        scope = StaticScope.instance()
        all_columns: list[str] = []
        for ind in self._indicators:
            all_columns.extend(ind.column_names)
        if all_columns:
            scope.register_custom_cols(all_columns)

    def _fetch_data(
        self,
        symbols: frozenset[str],
        start_date: datetime,
        end_date: datetime,
        timeframe: str | None,
        adjust: Any | None,
    ) -> pd.DataFrame:
        """Called by PyBroker to fetch data.

        Delegates entirely to the injected ``DataProvider``.
        """
        return self._data_provider.fetch_stock_data(
            symbols=symbols,
            start_date=start_date,
            end_date=end_date,
            timeframe=timeframe,
            indicators=self._indicators,
        )
