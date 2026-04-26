"""MA crossover strategy example with real TDX data source.

Buy when MA(10) crosses above MA(20) (golden cross).
Sell when MA(10) crosses below MA(20) (death cross).

Requires a running TDX environment with tqcenter installed.
See CLAUDE.md for TDX setup details.

Run::

    python examples/tdx_ma_cross_strategy.py
    python examples/tdx_ma_cross_strategy.py --log-level DEBUG
"""

from __future__ import annotations

import argparse
import io
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

import pybroker

pybroker.disable_data_source_cache()
pybroker.disable_indicator_cache()

from stablemoney import BacktestConfig, StrategyBuilder
from stablemoney.algos import MACrossAlgo
from stablemoney.data_sources import TdxDataSource
from stablemoney.indicators import MA
from stablemoney.log import setup_logging

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="MA crossover strategy backtest")
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="日志级别 (默认: INFO)",
    )
    args = parser.parse_args()
    setup_logging(args.log_level)

    backtest_config = BacktestConfig(
        symbols=["600519.SH", "000858.SZ", "000333.SZ"],
        start_date="2024-01-01",
        end_date="2024-12-31",
        initial_cash=100_000,
        indicators=[MA(10), MA(20)],
        warmup=20,
    )

    result = (
        StrategyBuilder()
        .set_data_source(
            TdxDataSource(
                indicators=backtest_config.indicators,
                tdx_dir=r"D:\Applications\tdx_test\PYPlugins\user",
            )
        )
        .set_backtest(backtest_config)
        .set_algo(MACrossAlgo())
        .run()
    )

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
