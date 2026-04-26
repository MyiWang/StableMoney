"""KDJ + MACD + MA combined strategy example with real TDX data source.

Requires a running TDX environment with tqcenter installed.
See CLAUDE.md for TDX setup details.

Run::

    python examples/tdx_kdj_macd_ma_strategy.py
    python examples/tdx_kdj_macd_ma_strategy.py --log-level DEBUG
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

from stablemoney import AlgoConfig, BacktestConfig, MarketSector, SectorFilter, StrategyBuilder
from stablemoney.algos import KdjMacdMaAlgo
from stablemoney.data_sources import TdxDataSource
from stablemoney.indicators import KDJ, MA, MACD
from stablemoney.log import setup_logging

# ---------------------------------------------------------------------------
# Run
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="KDJ + MACD + MA triple signal strategy backtest",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="日志级别 (默认: INFO)",
    )
    args = parser.parse_args()
    setup_logging(args.log_level)

    # Backtest configuration: 创业板市值前 20 的股票
    backtest_config = BacktestConfig(
        sector=MarketSector.CHINEXT,
        sector_filter=SectorFilter(
            sort_by="market_cap",
            sort_ascending=False,
            max_stocks=20,
        ),
        start_date="2023-01-01",
        end_date="2025-12-31",
        initial_cash=100_000,
        indicators=[KDJ(9, 3, 3), MACD(12, 26, 9), MA(10), MA(20)],
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
            KdjMacdMaAlgo(
                config=AlgoConfig(
                    stop_loss_pct=5,
                    take_profit_pct=20,
                    hold_bars=40,
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
