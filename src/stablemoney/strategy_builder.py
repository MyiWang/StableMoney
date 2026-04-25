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
            2. Create and run a PyBroker ``Strategy``.

        Returns:
            ``TestResult`` from PyBroker.
        """
        self._validate()

        assert self._data_source is not None
        assert self._backtest is not None
        assert self._exec_fn is not None

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
            symbols=self._backtest.symbols,
        )

        warmup: int | None = None
        if self._backtest.warmup is not None:
            warmup = self._backtest.warmup

        return strategy.backtest(warmup=warmup)

    def _validate(self) -> None:
        """Validate that all required parameters are set."""
        if self._data_source is None:
            raise ValueError("DataSource is required. Call set_data_source().")
        if self._backtest is None:
            raise ValueError("BacktestConfig is required. Call set_backtest().")
        if self._exec_fn is None:
            raise ValueError("ExecuteCallback is required. Call set_algo().")
