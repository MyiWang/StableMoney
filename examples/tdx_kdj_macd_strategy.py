"""KDJ + MACD combined strategy example with real TDX data source.

Requires a running TDX environment with tqcenter installed.
See CLAUDE.md for TDX setup details.

Run::

    python examples/tdx_kdj_macd_strategy.py
"""

from __future__ import annotations

import io
import sys

# Fix Windows console encoding for Chinese output
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

import pybroker

pybroker.disable_data_source_cache()
pybroker.disable_indicator_cache()

from stablemoney import AlgoConfig, BacktestConfig, StrategyBuilder
from stablemoney.algos import KDJMacdAlgo
from stablemoney.data_sources import TdxDataSource
from stablemoney.indicators import KDJ, MACD

# ---------------------------------------------------------------------------
# Run
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    # Backtest configuration (symbols, dates, capital, indicators)
    backtest_config = BacktestConfig(
        symbols=[
            "000001.SZ",
            "000858.SZ",
            "601615.SH",
        ],
        start_date="2025-04-24",
        end_date="2026-04-24",
        initial_cash=100_000,
        indicators=[KDJ(9, 3, 3), MACD(12, 26, 9)],
        warmup=50,
    )

    # Build and run with TDX data source
    result = (
        StrategyBuilder()
        .set_data_source(
            TdxDataSource(
                indicators=backtest_config.indicators,
                tdx_dir=r"D:\Applications\tdx_test\PYPlugins\user",
            )
        )
        .set_backtest(backtest_config)
        .set_algo(
            KDJMacdAlgo(
                config=AlgoConfig(
                    stop_loss_pct=5.0,
                    take_profit_pct=10.0,
                    hold_bars=20,
                ),
            )
        )
        .run()
    )

    # Print results
    print(f"回测区间: {result.start_date} ~ {result.end_date}")
    print(f"初始资金: {backtest_config.initial_cash:,.0f}")
    print(f"最终权益: {result.portfolio['equity'].iloc[-1]:,.2f}")
    print(f"总交易次数: {len(result.trades)}")
    print()
    print("=== 订单明细 ===")
    print(result.orders.to_string())
    print()
    print("=== 交易明细 ===")
    print(result.trades.to_string())
