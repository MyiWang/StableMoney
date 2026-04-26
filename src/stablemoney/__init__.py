"""StableMoney - A-share backtesting framework."""

from stablemoney.algos.algo_config import AlgoConfig
from stablemoney.data_providers.data_provider import DataProvider
from stablemoney.indicator_def import IndicatorDef
from stablemoney.market_sector import MarketSector, SectorFilter
from stablemoney.strategy_builder import StrategyBuilder
from stablemoney.strategy_config import BacktestConfig

__all__ = [
    "AlgoConfig",
    "BacktestConfig",
    "DataProvider",
    "IndicatorDef",
    "MarketSector",
    "SectorFilter",
    "StrategyBuilder",
]
