"""RSI strategy example with real TDX data source.

Requires a running TDX environment with tqcenter installed.
See CLAUDE.md for TDX setup details.

Run::

    python examples/tdx_rsi_strategy.py
"""

from __future__ import annotations

from typing import Any

import numpy as np

from stablemoney import BacktestConfig, StrategyBuilder, StrategyConfig
from stablemoney.indicators import MA, RSI
from stablemoney.tdx_data_source import TdxDataSource

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
    rsi = ctx.RSI_14
    ma = ctx.MA_20
    stop_loss_pct = ctx.config.params["stop_loss_pct"]

    # Skip bars where indicators haven't warmed up yet
    if np.isnan(rsi[-1]) or np.isnan(ma[-1]):
        return

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

    # Disable PyBroker disk cache
    import pybroker

    pybroker.disable_data_source_cache()
    pybroker.disable_indicator_cache()

    # Strategy configuration (capital, fees, custom params)
    strategy_config = StrategyConfig(
        initial_cash=500_000,
        params={
            "stop_loss_pct": 5.0,
            "take_profit_pct": 10.0,
        },
    )

    # Backtest configuration (symbols, dates, indicators)
    backtest_config = BacktestConfig(
        symbols=["600519.SH", "000858.SZ"],
        start_date="2024-01-01",
        end_date="2024-12-31",
        indicators=[RSI(14), MA(20)],
    )

    # Build and run with TDX data source
    result = (
        StrategyBuilder()
        .set_data_source(TdxDataSource(
            indicators=backtest_config.indicators,
            tdx_dir=r"D:\Applications\tdx_test\PYPlugins\user",
        ))
        .set_config(strategy_config)
        .set_backtest(backtest_config)
        .set_exec_fn(rsi_strategy)
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
