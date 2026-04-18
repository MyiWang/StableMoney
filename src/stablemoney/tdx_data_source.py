"""TDX (通达信) data source for PyBroker backtesting."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import pandas as pd
from pybroker.data import DataSource
from pybroker.scope import StaticScope

if TYPE_CHECKING:
    from datetime import datetime

    from stablemoney.indicator_def import IndicatorDef

# Timeframe mapping: PyBroker -> TDX
_TIMEFRAME_MAP: dict[str, str] = {
    "1d": "1d",
    "1w": "1w",
    "1mon": "1mon",
    "1h": "1h",
    "30m": "30m",
    "15m": "15m",
    "5m": "5m",
    "1m": "1m",
}


class TdxDataSource(DataSource):
    """TDX (通达信) data source for PyBroker.

    Fetches market data via the ``tq`` class (DLL) and computes
    indicators via the TDX formula engine (``formula_process_mul``).

    Usage::

        ds = TdxDataSource()
        ds.set_indicators([RSI(14), MA(20)])
        # Then pass to StrategyBuilder
    """

    def __init__(self) -> None:
        super().__init__()  # type: ignore[no-untyped-call]
        self._indicators: list[Any] = []

    def set_indicators(self, indicators: list[Any]) -> None:
        """Inject indicator definitions.

        Called by StrategyBuilder before running the backtest.
        Also registers indicator column names as PyBroker custom columns.
        """
        self._indicators = indicators
        scope = StaticScope.instance()
        all_columns: list[str] = []
        for ind in indicators:
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

        1. Call ``tq.get_market_data()`` for OHLCV data.
        2. For each IndicatorDef, call ``tq.formula_process_mul()``
           to compute indicators via TDX formula engine.
        3. Merge everything into a single PyBroker-format DataFrame.
        """
        from tqcenter import tq

        symbol_list = sorted(symbols)
        period = self._map_timeframe(timeframe)
        start_str = start_date.strftime("%Y%m%d")
        end_str = end_date.strftime("%Y%m%d")

        # 1. Fetch K-line data
        kline_data = tq.get_market_data(
            stock_list=symbol_list,
            period=period,
            start_time=start_str,
            end_time=end_str,
            dividend_type="front",
            fill_data=True,
        )

        df = self._convert_kline_to_dataframe(kline_data, symbol_list)

        # 2. Fetch indicator data
        for ind_def in self._indicators:
            ind_data = tq.formula_process_mul(
                formula_name=ind_def.name,
                formula_arg=ind_def.formula_arg,
                stock_list=symbol_list,
                stock_period=period,
                start_time=start_str,
                end_time=end_str,
            )
            if ind_data:
                df = self._merge_indicator_data(df, ind_data, ind_def, symbol_list)

        return df

    @staticmethod
    def _convert_kline_to_dataframe(
        kline_data: dict[str, pd.DataFrame],
        symbols: list[str],
    ) -> pd.DataFrame:
        """Convert TDX K-line data to PyBroker DataFrame format.

        TDX format::

            {"Close": DataFrame(index=DatetimeIndex, columns=["600519.SH"])}

        PyBroker format::

            DataFrame(columns=["symbol", "date", "open", "high", "low",
                                "close", "volume"])
        """
        field_map = {
            "Open": "open",
            "High": "high",
            "Low": "low",
            "Close": "close",
            "Volume": "volume",
        }

        records: list[dict[str, Any]] = []
        for symbol in symbols:
            for tdx_field, pb_col in field_map.items():
                if tdx_field not in kline_data:
                    continue
                series = kline_data[tdx_field][symbol]
                for dt, val in series.items():
                    # Check if we already have a record for this symbol+date
                    existing = _find_record(records, symbol, dt)
                    if existing is not None:
                        existing[pb_col] = float(val) if pd.notna(val) else None
                    else:
                        record: dict[str, Any] = {
                            "symbol": symbol,
                            "date": dt,
                        }
                        for col in field_map.values():
                            record[col] = None
                        record[pb_col] = float(val) if pd.notna(val) else None
                        records.append(record)

        df = pd.DataFrame(records)
        if not df.empty:
            df = df.sort_values(by=["date", "symbol"]).reset_index(drop=True)
        return df

    @staticmethod
    def _merge_indicator_data(
        df: pd.DataFrame,
        ind_data: dict[str, Any],
        ind_def: IndicatorDef,
        symbols: list[str],
    ) -> pd.DataFrame:
        """Merge TDX formula engine output into the main DataFrame.

        The structure of ``ind_data`` depends on the TDX API response
        and will be handled according to the indicator's output names.
        """
        # The exact response format of formula_process_mul needs to be
        # determined at integration time. This is a placeholder that
        # handles the common case of per-stock indicator data.
        column_names = ind_def.column_names

        for symbol in symbols:
            stock_data = ind_data.get(symbol, ind_data.get("Data", {}))
            if not stock_data:
                continue

            # Map indicator outputs to column names
            if len(column_names) == 1:
                # Single-value indicator
                values = stock_data if isinstance(stock_data, list) else []
                _merge_single_values(df, symbol, column_names[0], values)
            else:
                # Multi-value indicator
                for i, col_name in enumerate(column_names):
                    output_name = ind_def.outputs[i]
                    values = (
                        stock_data.get(output_name, [])
                        if isinstance(stock_data, dict)
                        else []
                    )
                    _merge_single_values(df, symbol, col_name, values)

        return df

    @staticmethod
    def _map_timeframe(timeframe: str | None) -> str:
        """Map PyBroker timeframe to TDX period."""
        return _TIMEFRAME_MAP.get(timeframe or "1d", "1d")


def _find_record(
    records: list[dict[str, Any]], symbol: str, date: Any
) -> dict[str, Any] | None:
    """Find an existing record for the given symbol and date."""
    for rec in records:
        if rec["symbol"] == symbol and rec["date"] == date:
            return rec
    return None


def _merge_single_values(
    df: pd.DataFrame,
    symbol: str,
    col_name: str,
    values: list[Any],
) -> None:
    """Merge a list of indicator values into the DataFrame."""
    if col_name not in df.columns:
        df[col_name] = None
    mask = df["symbol"] == symbol
    symbol_rows = df.loc[mask]
    for i, val in enumerate(values):
        if i < len(symbol_rows):
            idx = symbol_rows.index[i]
            df.at[idx, col_name] = val
