"""TDX (通达信) data source for PyBroker backtesting."""
from __future__ import annotations

import sys
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

    Fetches market data via ``tq.get_market_data()`` and computes
    indicators via the TDX formula engine (``formula_zb``).

    Indicators are injected via the constructor::

        ds = TdxDataSource(indicators=[RSI(14), MA(20)])
    """

    def __init__(
        self,
        indicators: list[IndicatorDef] | None = None,
        tdx_dir: str | None = None,
    ) -> None:
        super().__init__()  # type: ignore[no-untyped-call]
        self._indicators: list[IndicatorDef] = indicators or []
        self._init_tdx(tdx_dir)
        self._register_custom_columns()

    @staticmethod
    def _init_tdx(tdx_dir: str | None) -> None:
        """Add tqcenter to sys.path and initialize TDX connection."""
        if not tdx_dir:
            return
        if tdx_dir not in sys.path:
            sys.path.insert(0, tdx_dir)
        from tqcenter import tq

        tq.initialize(__file__)

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

        For each stock: fetch K-line -> convert to DataFrame ->
        compute indicators -> merge into per-stock DataFrame.
        Then concatenate all stocks into one DataFrame.
        """
        from tqcenter import tq

        period = self._map_timeframe(timeframe)
        start_str = start_date.strftime("%Y%m%d")
        end_str = end_date.strftime("%Y%m%d")

        parts: list[pd.DataFrame] = []
        for symbol in sorted(symbols):
            # Fetch K-line data
            kline_data = tq.get_market_data(
                stock_list=[symbol],
                period=period,
                start_time=start_str,
                end_time=end_str,
                dividend_type="front",
                fill_data=True,
            )

            # Convert to per-stock DataFrame
            stock_df = self._convert_kline_to_dataframe(kline_data, symbol)
            if stock_df.empty:
                continue

            # Compute indicators and merge into stock_df
            if self._indicators and "Close" in kline_data:
                bar_count = len(kline_data["Close"][symbol])
                formatted = tq.formula_format_data(kline_data)
                stock_formatted = formatted.get(symbol, [])
                if stock_formatted:
                    tq.formula_set_data(
                        stock_code=symbol,
                        stock_period=period,
                        stock_data=stock_formatted,
                        count=len(stock_formatted),
                        dividend_type=1,
                    )
                    for ind_def in self._indicators:
                        result = tq.formula_zb(
                            formula_name=ind_def.name,
                            formula_arg=ind_def.formula_arg,
                        )
                        self._merge_indicator_result(
                            stock_df, result, ind_def, bar_count,
                        )

            parts.append(stock_df)

        if not parts:
            return pd.DataFrame(columns=["symbol", "date"])

        df: pd.DataFrame = pd.concat(parts, ignore_index=True)
        df = df.sort_values(by=["date", "symbol"]).reset_index(drop=True)
        return df

    @staticmethod
    def _convert_kline_to_dataframe(
        kline_data: dict[str, pd.DataFrame],
        symbol: str,
    ) -> pd.DataFrame:
        """Convert single-stock TDX K-line data to PyBroker DataFrame."""
        field_map = {
            "Open": "open",
            "High": "high",
            "Low": "low",
            "Close": "close",
            "Volume": "volume",
        }

        data: dict[str, Any] = {}
        dates = None
        for tdx_field, pb_col in field_map.items():
            if tdx_field not in kline_data:
                continue
            series = kline_data[tdx_field][symbol]
            data[pb_col] = series.values
            if dates is None:
                dates = series.index

        if dates is None:
            return pd.DataFrame(columns=["symbol", "date"])

        data["date"] = dates
        data["symbol"] = symbol
        df: pd.DataFrame = pd.DataFrame(data)
        return df

    @staticmethod
    def _merge_indicator_result(
        df: pd.DataFrame,
        result: dict[str, Any],
        ind_def: IndicatorDef,
        bar_count: int,
    ) -> None:
        """Merge formula_zb output into a per-stock DataFrame.

        ``formula_zb`` returns ``{"Value": {"DIF": ["1.23", ...], ...}}``.
        Values are strings and include warmup bars.
        We take the last ``bar_count`` values to align with K-line data.
        """
        if not result or "Value" not in result:
            return
        value_dict: dict[str, list[str]] = result["Value"]

        def to_float(v: str | None) -> float:
            return float(v) if v is not None else float("nan")

        if len(ind_def.outputs) == 1 and ind_def.outputs[0] == "value":
            raw_values = next(iter(value_dict.values()), [])
            col_name = ind_def.column_names[0]
            df[col_name] = [to_float(v) for v in raw_values[-bar_count:]]
        else:
            for i, output_name in enumerate(ind_def.outputs):
                raw_values = value_dict.get(output_name, [])
                col_name = ind_def.column_names[i]
                df[col_name] = [to_float(v) for v in raw_values[-bar_count:]]

    @staticmethod
    def _map_timeframe(timeframe: str | None) -> str:
        """Map PyBroker timeframe to TDX period."""
        return _TIMEFRAME_MAP.get(timeframe or "1d", "1d")
