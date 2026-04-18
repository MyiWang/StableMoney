"""Simple RSI strategy example with mock data.

Demonstrates the full StableMoney pipeline:
- StrategyBuilder for strategy composition
- IndicatorDef for declarative indicator definitions
- ExecuteCallback for trading logic
- StrategyConfig with custom params (stop loss, take profit)

Run::

    python examples/simple_rsi_strategy.py
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from datetime import datetime

import numpy as np
import pandas as pd
from pybroker.data import DataSource

from stablemoney import IndicatorDef, StrategyBuilder, StrategyConfig
from stablemoney.indicators import MA, RSI

# ---------------------------------------------------------------------------
# Mock DataSource — simulates what TdxDataSource does with real TDX data
# ---------------------------------------------------------------------------


class MockDataSource(DataSource):
    """Mock data source that generates random OHLCV + indicator data.

    Mimics the behaviour of :class:`TdxDataSource`:
    - ``set_indicators()`` registers custom columns
    - ``_fetch_data()`` returns a PyBroker-format DataFrame
    """

    def __init__(self) -> None:
        super().__init__()  # type: ignore[no-untyped-call]
        self._indicators: list[Any] = []

    def set_indicators(self, indicators: list[Any]) -> None:
        """Register indicator columns (same API as TdxDataSource)."""
        from pybroker.scope import StaticScope

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
        rng = np.random.default_rng(42)
        dates = pd.bdate_range(start_date, end_date)

        records: list[dict[str, Any]] = []
        for symbol in sorted(symbols):
            price = 100.0
            closes: list[float] = []
            for dt in dates:
                change = rng.normal(0, 1.5)
                open_ = price
                close = round(price + change, 2)
                high = round(max(open_, close) + abs(rng.normal(0, 0.8)), 2)
                low = round(min(open_, close) - abs(rng.normal(0, 0.8)), 2)
                volume = int(rng.integers(100_000, 500_000))
                price = close
                closes.append(close)
                records.append(
                    {
                        "symbol": symbol,
                        "date": dt,
                        "open": open_,
                        "high": high,
                        "low": low,
                        "close": close,
                        "volume": volume,
                    }
                )

        df = pd.DataFrame(records)
        df = df.sort_values(["date", "symbol"]).reset_index(drop=True)

        # Compute indicators and merge as columns
        for ind_def in self._indicators:
            self._add_indicator_column(df, ind_def, dates, sorted(symbols))

        return df

    @staticmethod
    def _add_indicator_column(
        df: pd.DataFrame,
        ind_def: IndicatorDef,
        dates: pd.DatetimeIndex,
        symbols: list[str],
    ) -> None:
        """Compute indicator values and add them as DataFrame columns."""
        for symbol in symbols:
            mask = df["symbol"] == symbol
            close_prices = df.loc[mask, "close"].values

            for col_name in ind_def.column_names:
                if ind_def.name == "RSI":
                    period = ind_def.params.get("period", 14)
                    values = _compute_rsi(close_prices, period)
                elif ind_def.name == "MA":
                    period = ind_def.params.get("period", 20)
                    values = _compute_ma(close_prices, period)
                else:
                    values = np.zeros(len(close_prices))

                df.loc[mask, col_name] = values


def _compute_rsi(closes: np.ndarray, period: int) -> np.ndarray:
    """Simple RSI computation."""
    deltas = np.diff(closes, prepend=closes[0])
    gains = np.where(deltas > 0, deltas, 0.0)
    losses = np.where(deltas < 0, -deltas, 0.0)

    avg_gain = np.zeros_like(closes)
    avg_loss = np.zeros_like(closes)

    avg_gain[period] = np.mean(gains[1 : period + 1])
    avg_loss[period] = np.mean(losses[1 : period + 1])

    for i in range(period + 1, len(closes)):
        avg_gain[i] = (avg_gain[i - 1] * (period - 1) + gains[i]) / period
        avg_loss[i] = (avg_loss[i - 1] * (period - 1) + losses[i]) / period

    with np.errstate(divide="ignore", invalid="ignore"):
        rs = np.where(avg_loss != 0, avg_gain / avg_loss, 100.0)
        rsi = 100.0 - 100.0 / (1.0 + rs)
    rsi[:period] = np.nan
    return rsi


def _compute_ma(closes: np.ndarray, period: int) -> np.ndarray:
    """Simple moving average."""
    ma = np.full_like(closes, np.nan)
    for i in range(period - 1, len(closes)):
        ma[i] = np.mean(closes[i - period + 1 : i + 1])
    return ma


# ---------------------------------------------------------------------------
# Trading logic
# ---------------------------------------------------------------------------


def rsi_strategy(ctx: Any) -> None:
    """RSI oversold/overbought strategy with stop loss.

    Entry:
        - RSI < 35 (oversold)

    Exit:
        - RSI > 65 (overbought)
        - Stop loss triggered (configurable via params)
    """
    rsi = ctx.indicator("RSI_14")
    ma = ctx.indicator("MA_20")
    stop_loss_pct = ctx.config.params["stop_loss_pct"]

    pos = ctx.long_pos()

    # Stop loss check
    if pos is not None and pos.entries:
        entry_price = float(pos.entries[0].price)
        pnl_pct = (
            (ctx.close[-1] - entry_price) / entry_price * 100
        )
        if pnl_pct <= -stop_loss_pct:
            ctx.sell_all_shares()
            return

    # Buy signal: RSI oversold
    if rsi[-1] < 35 and pos is None:
        # Use MA as a reference for position sizing
        shares = int(ctx.config.initial_cash / ma[-1] / 10)
        ctx.buy_shares = max(shares, 100)

    # Sell signal: RSI overbought
    if rsi[-1] > 65 and pos is not None:
        ctx.sell_all_shares()


# ---------------------------------------------------------------------------
# Run
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import io
    import sys

    # Fix Windows console encoding for Chinese output
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

    # Disable PyBroker disk cache to avoid stale data
    import pybroker

    pybroker.disable_data_source_cache()
    pybroker.disable_indicator_cache()

    # Configuration
    config = StrategyConfig(
        initial_cash=500_000,
        params={
            "stop_loss_pct": 5.0,
            "take_profit_pct": 10.0,
        },
    )

    # Build and run
    result = (
        StrategyBuilder()
        .set_data_source(MockDataSource())
        .set_config(config)
        .add_indicator(RSI(14))
        .add_indicator(MA(20))
        .set_exec_fn(rsi_strategy)
        .set_symbols(["600519.SH"])
        .set_date_range("2024-01-01", "2024-12-31")
        .run()
    )

    # Print results
    print(f"回测区间: {result.start_date} ~ {result.end_date}")
    print("初始资金: 500,000")
    print(f"最终权益: {result.portfolio['equity'].iloc[-1]:,.2f}")
    print(f"总交易次数: {len(result.trades)}")
    print()
    print("=== 订单明细 ===")
    print(result.orders.to_string())
    print()
    print("=== 交易明细 ===")
    print(result.trades.to_string())
