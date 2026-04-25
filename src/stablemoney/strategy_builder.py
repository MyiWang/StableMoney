"""Strategy builder for composing and running backtests."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from pybroker.config import StrategyConfig as PyBrokerStrategyConfig
from pybroker.strategy import Strategy as PyBrokerStrategy
from pybroker.strategy import TestResult

if TYPE_CHECKING:
    from collections.abc import Callable

    from pybroker.context import ExecContext
    from pybroker.data import DataSource

    from stablemoney.market_sector import MarketSector, SectorFilter
    from stablemoney.strategy_config import BacktestConfig


class StrategyBuilder:
    """Builder for composing and running a backtest.

    Provides a fluent interface to assemble the core components:

    1. ``DataSource`` — market data source
    2. ``BacktestConfig`` — backtest configuration (symbols, dates, capital, indicators)
    3. ``algo`` — trading logic (callable class or function)

    Example::

        backtest = BacktestConfig(
            symbols=["600519.SH"],
            start_date="2024-01-01",
            end_date="2024-12-31",
            initial_cash=500_000,
            indicators=[RSI(14), MA(20)],
        )
        result = (
            StrategyBuilder()
            .set_data_source(TdxDataSource(indicators=backtest.indicators))
            .set_backtest(backtest)
            .set_algo(RSIAlgo(config=AlgoConfig(stop_loss_pct=5.0)))
            .run()
        )
    """

    def __init__(self) -> None:
        self._data_source: DataSource | None = None
        self._backtest: BacktestConfig | None = None
        self._exec_fn: Callable[[ExecContext], None] | None = None

    def set_data_source(self, data_source: DataSource) -> StrategyBuilder:
        """Set the data source."""
        self._data_source = data_source
        return self

    def set_backtest(self, backtest: BacktestConfig) -> StrategyBuilder:
        """Set backtest configuration (symbols, dates, capital, indicators)."""
        self._backtest = backtest
        return self

    def set_algo(self, algo: Callable[[ExecContext], None]) -> StrategyBuilder:
        """Set the trading logic (class instance or plain function)."""
        self._exec_fn = algo
        return self

    def run(self) -> TestResult:
        """Execute the backtest.

        Steps:
            1. Validate all required parameters.
            2. Resolve sector to symbols if needed.
            3. Create and run a PyBroker ``Strategy``.

        Returns:
            ``TestResult`` from PyBroker.
        """
        self._validate()

        assert self._data_source is not None
        assert self._backtest is not None
        assert self._exec_fn is not None

        symbols = self._resolve_symbols()

        config = PyBrokerStrategyConfig(
            initial_cash=self._backtest.initial_cash,
        )
        strategy = PyBrokerStrategy(
            data_source=self._data_source,
            start_date=datetime.fromisoformat(self._backtest.start_date),
            end_date=datetime.fromisoformat(self._backtest.end_date),
            config=config,
        )
        strategy.add_execution(
            fn=self._exec_fn,
            symbols=symbols,
        )

        warmup: int | None = None
        if self._backtest.warmup is not None:
            warmup = self._backtest.warmup

        return strategy.backtest(warmup=warmup)

    def _resolve_symbols(self) -> list[str]:
        """Resolve symbols from sector or use explicit symbol list."""
        assert self._backtest is not None

        if self._backtest.symbols:
            return self._backtest.symbols

        if self._backtest.sector is None:
            raise ValueError(
                "Either 'symbols' or 'sector' must be provided in BacktestConfig."
            )

        return _resolve_sector(
            self._backtest.sector,
            self._backtest.sector_filter,
        )

    def _validate(self) -> None:
        """Validate that all required parameters are set."""
        if self._data_source is None:
            raise ValueError("DataSource is required. Call set_data_source().")
        if self._backtest is None:
            raise ValueError("BacktestConfig is required. Call set_backtest().")
        if self._exec_fn is None:
            raise ValueError("ExecuteCallback is required. Call set_algo().")

        has_symbols = bool(self._backtest.symbols)
        has_sector = self._backtest.sector is not None
        if has_symbols and has_sector:
            raise ValueError(
                "'symbols' and 'sector' are mutually exclusive. Provide only one."
            )
        if not has_symbols and not has_sector:
            raise ValueError(
                "Either 'symbols' or 'sector' must be provided in BacktestConfig."
            )


def _resolve_sector(
    sector: MarketSector,
    sector_filter: SectorFilter | None,
) -> list[str]:
    """Fetch stock codes from TDX for the given sector and apply filter.

    Requires TDX to be initialized (via ``TdxDataSource`` with ``tdx_dir``).

    Market cap is calculated as: close_price × total_shares(万股) / 10000 = 亿元.
    """
    try:
        from tqcenter import tq
    except ImportError as e:
        raise ImportError(
            "Sector resolution requires TDX. "
            "Initialize TdxDataSource with tdx_dir before using sector."
        ) from e

    codes: list[str] = tq.get_stock_list(market=sector.value)
    if not codes:
        return []

    print(f"[sector] {sector.name}: 获取到 {len(codes)} 只股票")

    if sector_filter is None:
        return codes

    # Sort by real market cap if sort_by is set
    if sector_filter.sort_by is not None:
        use_float = sector_filter.sort_by == "float_cap"
        stock_data = _fetch_market_cap(tq, codes, use_float=use_float)
        stock_data.sort(
            key=lambda x: x[1], reverse=not sector_filter.sort_ascending
        )
    else:
        stock_data = [(code, 0.0) for code in codes]

    # Filter by market cap range (亿元)
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
        print(f"[sector] 市值区间过滤后剩余 {len(stock_data)} 只股票")

    result = [code for code, _ in stock_data]

    if sector_filter.max_stocks:
        result = result[: sector_filter.max_stocks]

    print(f"[sector] 筛选完成，选中 {len(result)} 只股票")
    return result


def _fetch_market_cap(
    tq: object,
    codes: list[str],
    *,
    use_float: bool = False,
) -> list[tuple[str, float]]:
    """Calculate real market cap (亿元) for each stock.

    Uses ``get_market_data`` (batch) for close prices and ``get_stock_info``
    (per stock) for shares outstanding.
    """
    cap_type = "流通市值" if use_float else "总市值"
    share_field = "ActiveCapital" if use_float else "J_zgb"
    print(f"[sector] 正在计算 {len(codes)} 只股票的{cap_type}...")

    # Batch fetch close prices
    data = tq.get_market_data(  # type: ignore[attr-defined]
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
        print("[sector] 收盘价数据为空，无法计算市值")
        return [(code, 0.0) for code in codes]

    last_row = close_df.iloc[-1]

    # Per-stock fetch shares and calculate market cap
    result: list[tuple[str, float]] = []
    skipped = 0
    for code in codes:
        try:
            price = float(last_row[code])
        except (KeyError, ValueError, TypeError):
            skipped += 1
            continue

        if price <= 0:
            skipped += 1
            continue

        try:
            info = tq.get_stock_info(  # type: ignore[attr-defined]
                stock_code=code, field_list=[share_field]
            )
            shares_wan = float(info.get(share_field, 0))  # 万股
        except Exception:
            skipped += 1
            continue

        # 市值(亿) = 收盘价 × 总股本(万股) / 10000
        mcap = price * shares_wan / 10000
        result.append((code, mcap))

    valid = len(result)
    print(f"[sector] 成功计算 {valid}/{len(codes)} 只股票的{cap_type}")
    if skipped:
        print(f"[sector] 跳过 {skipped} 只（价格异常或缺数据）")
    return result
