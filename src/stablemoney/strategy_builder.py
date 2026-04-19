"""Strategy builder for composing and running backtests."""
from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from pybroker.strategy import Strategy as PyBrokerStrategy
from pybroker.strategy import TestResult

from stablemoney.strategy_config import BacktestConfig, StrategyConfig

if TYPE_CHECKING:
    from collections.abc import Callable, Iterable

    from pybroker.context import ExecContext
    from pybroker.data import DataSource


class StrategyBuilder:
    """Builder for composing and running a backtest.

    Provides a fluent interface to assemble the core components:

    1. ``DataSource`` — market data source
    2. ``StrategyConfig`` — strategy configuration (with custom params)
    3. ``BacktestConfig`` — backtest run configuration (symbols, dates, indicators)
    4. ``algo`` — trading logic (callable class or function)

    Example::

        result = (
            StrategyBuilder()
            .set_data_source(TdxDataSource(indicators=[RSI(14), MA(20)]))
            .set_config(StrategyConfig(initial_cash=500_000))
            .set_algo(RSIAlgo(stop_loss_pct=5.0))
            .set_symbols(["600519.SH"])
            .set_date_range("2024-01-01", "2024-12-31")
            .run()
        )

    Or use ``BacktestConfig`` to set symbols, dates, and indicators together::

        backtest = BacktestConfig(
            symbols=["600519.SH"],
            start_date="2024-01-01",
            end_date="2024-12-31",
            indicators=[RSI(14), MA(20)],
        )
        result = (
            StrategyBuilder()
            .set_data_source(TdxDataSource(backtest))
            .set_config(StrategyConfig(initial_cash=500_000))
            .set_backtest(backtest)
            .set_algo(RSIAlgo())
            .run()
        )
    """

    def __init__(self) -> None:
        self._data_source: DataSource | None = None
        self._config: StrategyConfig = StrategyConfig()
        self._backtest: BacktestConfig | None = None
        self._exec_fn: Callable[[ExecContext], None] | None = None
        self._symbols: list[str] = []
        self._start_date: datetime | None = None
        self._end_date: datetime | None = None

    def set_data_source(self, data_source: DataSource) -> StrategyBuilder:
        """Set the data source."""
        self._data_source = data_source
        return self

    def set_config(self, config: StrategyConfig) -> StrategyBuilder:
        """Set the strategy configuration."""
        self._config = config
        return self

    def set_backtest(self, backtest: BacktestConfig) -> StrategyBuilder:
        """Set backtest configuration (symbols, dates, indicators)."""
        self._backtest = backtest
        self._symbols = list(backtest.symbols)
        self._start_date = self._parse_date(backtest.start_date)
        self._end_date = self._parse_date(backtest.end_date)
        return self

    def set_algo(self, algo: Callable[[ExecContext], None]) -> StrategyBuilder:
        """Set the trading logic (class instance or plain function)."""
        self._exec_fn = algo
        return self

    def set_symbols(
        self, symbols: str | Iterable[str]
    ) -> StrategyBuilder:
        """Set the ticker symbols to backtest."""
        self._symbols = (
            [symbols] if isinstance(symbols, str) else list(symbols)
        )
        return self

    def set_date_range(
        self,
        start_date: str | datetime,
        end_date: str | datetime,
    ) -> StrategyBuilder:
        """Set the backtest date range."""
        self._start_date = self._parse_date(start_date)
        self._end_date = self._parse_date(end_date)
        return self

    def run(self) -> TestResult:
        """Execute the backtest.

        Steps:
            1. Validate all required parameters.
            2. Create and run a PyBroker ``Strategy``.

        Returns:
            ``TestResult`` from PyBroker.
        """
        self._validate()

        assert self._data_source is not None
        assert self._exec_fn is not None
        assert self._start_date is not None
        assert self._end_date is not None

        strategy = PyBrokerStrategy(
            data_source=self._data_source,
            start_date=self._start_date,
            end_date=self._end_date,
            config=self._config,
        )
        strategy.add_execution(
            fn=self._exec_fn,
            symbols=self._symbols,
        )
        return strategy.backtest()

    def _validate(self) -> None:
        """Validate that all required parameters are set."""
        if self._data_source is None:
            raise ValueError("DataSource is required. Call set_data_source().")
        if self._exec_fn is None:
            raise ValueError(
                "ExecuteCallback is required. Call set_algo()."
            )
        if not self._symbols:
            raise ValueError("Symbols are required. Call set_symbols().")
        if self._start_date is None or self._end_date is None:
            raise ValueError(
                "Date range is required. Call set_date_range()."
            )

    @staticmethod
    def _parse_date(date: str | datetime) -> datetime:
        """Parse a date string or return the datetime object."""
        if isinstance(date, str):
            return datetime.fromisoformat(date)
        return date
