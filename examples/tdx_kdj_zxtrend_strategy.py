"""KDJ + ZXTREND golden cross strategy example with real TDX data source.

Buy signal: KDJ.J < 0 within 30 bars after ZXTREND SHORT_T crosses above LONG_T
Exit: stop loss 5%, take profit 15%, max hold 40 bars

Requires a running TDX environment with tqcenter installed.
See CLAUDE.md for TDX setup details.

Run::

    python examples/tdx_kdj_zxtrend_strategy.py
    python examples/tdx_kdj_zxtrend_strategy.py --log-level DEBUG
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
from stablemoney.algos import KdjZxtrendAlgo
from stablemoney.data_sources import TdxDataSource
from stablemoney.indicators import KDJ, ZXTREND
from stablemoney.log import setup_logging
from stablemoney.data_providers.tdx_data_provider import TdxDataProvider

# ---------------------------------------------------------------------------
# Run
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="KDJ + ZXTREND golden cross strategy backtest")
    parser.add_argument(
        "--log-level",
        default="ERROR",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="日志级别 (默认: ERROR)",
    )
    args = parser.parse_args()
    setup_logging(args.log_level)

    # Backtest configuration: 上证主板市值前100
    backtest_config = BacktestConfig(
        sector=MarketSector.MAIN_SH,
        sector_filter=SectorFilter(
            max_stocks=100,
            sort_by="market_cap",
            sort_ascending=False,
        ),
        start_date="2019-01-01",
        end_date="2023-12-31",
        initial_cash=100_000,
        indicators=[KDJ(9, 3, 3), ZXTREND(14, 28, 57, 114)],
        warmup=114,
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
        .set_algo(
            KdjZxtrendAlgo(
                config=AlgoConfig(
                    stop_loss_pct=5,
                    take_profit_pct=15,
                    hold_bars=40,
                ),
                lookback=30,
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
    print(result.metrics_df)
