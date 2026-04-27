"""RSI strategy example with real TDX data source.

Requires a running TDX environment with tqcenter installed.
See CLAUDE.md for TDX setup details.

Run::

    python examples/tdx_rsi_strategy.py
    python examples/tdx_rsi_strategy.py --log-level DEBUG
"""

from __future__ import annotations

import argparse
import io
import sys

# Fix Windows console encoding for Chinese output
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

import pybroker

pybroker.disable_data_source_cache()
pybroker.disable_indicator_cache()

from stablemoney import AlgoConfig, BacktestConfig, StrategyBuilder
from stablemoney.algos import RSIAlgo
from stablemoney.data_sources import TdxDataSource
from stablemoney.indicators import MA, RSI
from stablemoney.log import setup_logging
from stablemoney.data_providers.tdx_data_provider import TdxDataProvider

# ---------------------------------------------------------------------------
# Run
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="RSI strategy backtest")
    parser.add_argument(
        "--log-level",
        default="ERROR",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="日志级别 (默认: INFO)",
    )
    args = parser.parse_args()
    setup_logging(args.log_level)

    # Backtest configuration (symbols, dates, capital, indicators)
    backtest_config = BacktestConfig(
        symbols=[
            "000001.SZ",
            "000858.SZ",
            "000004.SZ",
            "000006.SZ",
            "000007.SZ",
            "000008.SZ",
            "000009.SZ",
            "601615.SH",
            "300001.SZ",
        ],
        start_date="2025-04-24",
        end_date="2026-04-24",
        initial_cash=100_000,
        indicators=[RSI(14), MA(20)],
        warmup=110
    )

    # Build and run with TDX data source
    provider = TdxDataProvider(tdx_dir=r"D:\Applications\tdx_test\PYPlugins\user")
    result = (
        StrategyBuilder()
        .set_data_source(
            TdxDataSource(
                indicators=backtest_config.indicators,
                data_provider=provider,
            )
        )
        .set_data_provider(provider)
        .set_backtest(backtest_config)
        .set_algo(RSIAlgo(config=AlgoConfig(stop_loss_pct=5.0)))
        .run()
    )

    # Print results
    print(f"回测区间: {result.start_date} ~ {result.end_date}")
    print("初始资金: 500,000")
    print(f"最终权益: {result.portfolio['equity'].iloc[-1]:,.2f}")
    print(f"总交易次数: {len(result.trades)}")
    print()
    print(result.metrics_df)
    # print("=== 订单明细 ===")
    # print(result.orders.to_string())
    # print()
    # print("=== 交易明细 ===")
    # print(result.trades.to_string())
