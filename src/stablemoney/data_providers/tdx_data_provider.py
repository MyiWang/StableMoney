"""TDX (通达信) implementation of DataProvider."""
from __future__ import annotations

import logging
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Any

import pandas as pd

from stablemoney.data_providers.data_provider import DataProvider

if TYPE_CHECKING:
    from datetime import datetime

    from stablemoney.indicator_def import IndicatorDef
    from stablemoney.market_sector import MarketSector, SectorFilter

logger = logging.getLogger(__name__)

_TDX_DUMP_DIR = Path("tmp/tdx_debug")

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


def _dump_stock_csv(
    symbol: str,
    stock_df: pd.DataFrame,
    tag: str,
) -> Path:
    """Dump stock DataFrame to CSV for TDX issue reporting."""
    _TDX_DUMP_DIR.mkdir(parents=True, exist_ok=True)
    safe_symbol = symbol.replace(".", "_")
    path = _TDX_DUMP_DIR / f"{safe_symbol}_{tag}.csv"
    stock_df.to_csv(path, index=False)
    return path


class TdxDataProvider(DataProvider):
    """TDX implementation of DataProvider.

    Three-layer architecture:

    - Bottom layer (``_raw_*``): 1:1 wrappers around ``tq.*`` calls
    - Middle layer (``_convert_*``, ``_merge_*``): data transformation
    - Top layer (``fetch_stock_data``, ``resolve_sector``): business methods
    """

    def __init__(self, tdx_dir: str | None = None) -> None:
        self._tq: Any = self._init_tdx(tdx_dir)

    # ------------------------------------------------------------------
    # Initialization
    # ------------------------------------------------------------------

    @staticmethod
    def _init_tdx(tdx_dir: str | None) -> Any:
        """Initialize TDX connection. Returns the tq module reference."""
        if not tdx_dir:
            return None
        if tdx_dir not in sys.path:
            sys.path.insert(0, tdx_dir)
        from tqcenter import tq

        tq.initialize(__file__)
        return tq

    @property
    def tq(self) -> Any:
        """Lazy tq accessor -- imports on first use if not initialized."""
        if self._tq is None:
            from tqcenter import tq

            self._tq = tq
        return self._tq

    # ------------------------------------------------------------------
    # Bottom layer: raw TDX API wrappers
    # ------------------------------------------------------------------

    def _raw_get_market_data(self, **kwargs: Any) -> dict[str, pd.DataFrame]:
        return dict(self.tq.get_market_data(**kwargs))

    def _raw_get_stock_list(self, market: str) -> list[str]:
        return list(self.tq.get_stock_list(market=market))

    def _raw_get_stock_info(
        self, stock_code: str, field_list: list[str]
    ) -> dict[str, Any]:
        return dict(
            self.tq.get_stock_info(
                stock_code=stock_code, field_list=field_list
            )
        )

    def _raw_formula_format_data(
        self, kline_data: dict[str, pd.DataFrame]
    ) -> dict[str, list[Any]]:
        return dict(self.tq.formula_format_data(kline_data))

    def _raw_formula_set_data(self, **kwargs: Any) -> None:
        self.tq.formula_set_data(**kwargs)

    def _raw_formula_zb(
        self, formula_name: str, formula_arg: str
    ) -> dict[str, Any]:
        return dict(
            self.tq.formula_zb(
                formula_name=formula_name, formula_arg=formula_arg
            )
        )

    # ------------------------------------------------------------------
    # Middle layer: data conversion
    # ------------------------------------------------------------------

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
        """Merge formula_zb output into a per-stock DataFrame."""
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

    def _fetch_market_cap(
        self,
        codes: list[str],
        *,
        use_float: bool = False,
    ) -> list[tuple[str, float]]:
        """Calculate real market cap (亿元) for each stock."""
        cap_type = "流通市值" if use_float else "总市值"
        share_field = "ActiveCapital" if use_float else "J_zgb"
        logger.info("[sector] 正在计算 %d 只股票的%s...", len(codes), cap_type)

        data = self._raw_get_market_data(
            field_list=["Close"],
            stock_list=codes,
            period="1d",
            start_time="19900101",
            count=1,
            dividend_type="none",
            fill_data=True,
        )
        close_df = data.get("Close")
        if close_df is None or close_df.empty:
            logger.warning("[sector] 收盘价数据为空，无法计算市值")
            return [(code, 0.0) for code in codes]

        last_row = close_df.iloc[-1]

        result: list[tuple[str, float]] = []
        skipped = 0
        for code in codes:
            try:
                price = float(last_row[code])
                info = self._raw_get_stock_info(
                    stock_code=code, field_list=[share_field]
                )
                shares_wan = float(info.get(share_field, 0))
            except Exception as e:
                logger.debug("[sector] %s: 跳过，原因: %s", code, e)
                logger.error("[sector] %s: 计算市值失败", code)
                skipped += 1
                continue

            mcap = price * shares_wan / 10000
            result.append((code, mcap))

        valid = len(result)
        logger.info("[sector] 成功计算 %d/%d 只股票的%s", valid, len(codes), cap_type)
        if skipped:
            logger.info("[sector] 跳过 %d 只（价格异常或缺数据）", skipped)
        logger.debug("[sector] 市值明细: %s", result)
        return result

    # ------------------------------------------------------------------
    # Top layer: business methods (DataProvider interface)
    # ------------------------------------------------------------------

    def fetch_stock_data(
        self,
        symbols: frozenset[str],
        start_date: datetime,
        end_date: datetime,
        timeframe: str | None,
        indicators: list[IndicatorDef],
    ) -> pd.DataFrame:
        """Fetch OHLCV + indicators for multiple stocks."""
        period = self._map_timeframe(timeframe)
        start_str = start_date.strftime("%Y%m%d")
        end_str = end_date.strftime("%Y%m%d")

        parts: list[pd.DataFrame] = []
        for symbol in sorted(symbols):
            logger.info("[TDX] 开始获取 %s 的 K 线数据", symbol)
            kline_data = self._raw_get_market_data(
                stock_list=[symbol],
                period=period,
                start_time=start_str,
                end_time=end_str,
                dividend_type="front",
                fill_data=True,
            )

            stock_df = self._convert_kline_to_dataframe(kline_data, symbol)
            if stock_df.empty:
                logger.debug("[TDX] %s: K线数据为空，跳过", symbol)
                continue

            logger.info(
                "[TDX] %s: 获取到 %d 条 K 线, 日期范围 %s ~ %s",
                symbol,
                len(stock_df),
                stock_df["date"].iloc[0],
                stock_df["date"].iloc[-1],
            )

            bad_mask = stock_df["close"] <= 0
            if bad_mask.any():
                bad_prices = stock_df[bad_mask]
                first_date = (
                    bad_prices["date"].iloc[0]
                    if "date" in bad_prices.columns
                    else "N/A"
                )
                last_date = (
                    bad_prices["date"].iloc[-1]
                    if "date" in bad_prices.columns
                    else "N/A"
                )
                logger.warning(
                    "[TDX] %s: K线存在非正收盘价, 共 %d 条, "
                    "最小值=%.4f, 日期范围=%s ~ %s, "
                    "已导出到 %s",
                    symbol,
                    len(bad_prices),
                    stock_df["close"].min(),
                    first_date,
                    last_date,
                    _dump_stock_csv(symbol, stock_df, "bad_price"),
                )
                continue

            if indicators and "Close" in kline_data:
                bar_count = len(kline_data["Close"][symbol])
                formatted = self._raw_formula_format_data(kline_data)
                stock_formatted = formatted.get(symbol, [])
                fmt_len = len(stock_formatted)

                if fmt_len != bar_count:
                    logger.warning(
                        "[TDX] %s: K线 bar_count=%d, formula_format_data=%d, "
                        "差值=%d, 已导出到 %s",
                        symbol,
                        bar_count,
                        fmt_len,
                        bar_count - fmt_len,
                        _dump_stock_csv(symbol, stock_df, "fmt_mismatch"),
                    )

                if stock_formatted:
                    self._raw_formula_set_data(
                        stock_code=symbol,
                        stock_period=period,
                        stock_data=stock_formatted,
                        count=len(stock_formatted),
                        dividend_type=1,
                    )
                    for ind_def in indicators:
                        logger.info(
                            "[TDX] %s: 计算指标 %s(%s)",
                            symbol,
                            ind_def.name,
                            ind_def.formula_arg,
                        )
                        result = self._raw_formula_zb(
                            formula_name=ind_def.name,
                            formula_arg=ind_def.formula_arg,
                        )
                        if result and "Value" in result and result["Value"]:
                            for out_name, vals in result["Value"].items():
                                if vals is not None and len(vals) != bar_count:
                                    logger.warning(
                                        "[TDX] %s: formula_zb(%s) 输出 %s "
                                        "返回 %d 值, K线 bar_count=%d, "
                                        "差值=%d, 已导出到 %s",
                                        symbol,
                                        ind_def.name,
                                        out_name,
                                        len(vals),
                                        bar_count,
                                        len(vals) - bar_count,
                                        _dump_stock_csv(
                                            symbol,
                                            stock_df,
                                            f"zb_mismatch_{ind_def.name}",
                                        ),
                                    )
                        self._merge_indicator_result(
                            stock_df, result, ind_def, bar_count
                        )
                        logger.debug(
                            "[TDX] %s: 指标 %s 计算完成, 输出列=%s",
                            symbol,
                            ind_def.name,
                            ind_def.column_names,
                        )

            parts.append(stock_df)

        if not parts:
            return pd.DataFrame(columns=["symbol", "date"])

        df: pd.DataFrame = pd.concat(parts, ignore_index=True)
        df = df.sort_values(by=["date", "symbol"]).reset_index(drop=True)
        logger.info(
            "[TDX] 数据获取完成: %d 条记录, %d 只股票",
            len(df),
            len(symbols),
        )
        logger.debug("[TDX] 最终 DataFrame:\n%s", df.to_string())
        return df

    def resolve_sector(
        self,
        sector: MarketSector,
        sector_filter: SectorFilter | None = None,
    ) -> list[str]:
        """Resolve sector to stock codes with optional filtering."""
        codes: list[str] = self._raw_get_stock_list(market=sector.value)
        if not codes:
            return []

        logger.info("[sector] %s: 获取到 %d 只股票", sector.name, len(codes))
        logger.debug("[sector] %s: 全部股票代码: %s", sector.name, codes)

        if sector_filter is None:
            return codes

        if sector_filter.sort_by is not None:
            use_float = sector_filter.sort_by == "float_cap"
            stock_data = self._fetch_market_cap(codes, use_float=use_float)
            before = len(stock_data)
            stock_data = [(c, v) for c, v in stock_data if v == v]  # filter NaN
            if dropped := before - len(stock_data):
                logger.info("[sector] 过滤掉 %d 只市值为 NaN 的股票", dropped)
            stock_data.sort(
                key=lambda x: x[1], reverse=not sector_filter.sort_ascending
            )
        else:
            stock_data = [(code, 0.0) for code in codes]

        has_min = sector_filter.min_market_cap is not None
        has_max = sector_filter.max_market_cap is not None
        if has_min or has_max:
            filtered: list[tuple[str, float]] = []
            for code, val in stock_data:
                if has_min and val < sector_filter.min_market_cap:  # type: ignore[operator]
                    continue
                if has_max and val > sector_filter.max_market_cap:  # type: ignore[operator]
                    continue
                filtered.append((code, val))
            stock_data = filtered
            logger.info("[sector] 市值区间过滤后剩余 %d 只股票", len(stock_data))
            logger.debug("[sector] 过滤后股票: %s", stock_data)

        result = [code for code, _ in stock_data]

        if sector_filter.max_stocks:
            result = result[: sector_filter.max_stocks]

        logger.info("[sector] 筛选完成，选中 %d 只股票", len(result))
        logger.debug("[sector] 最终选中股票: %s", result)
        return result
