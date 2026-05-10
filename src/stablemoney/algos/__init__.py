"""Built-in trading algos."""
from stablemoney.algos.algo_config import AlgoConfig
from stablemoney.algos.base_algo import BaseAlgo
from stablemoney.algos.kdj_macd_algo import KDJMacdAlgo
from stablemoney.algos.kdj_macd_ma_algo import KdjMacdMaAlgo
from stablemoney.algos.kdj_zxtrend_algo import KdjZxtrendAlgo
from stablemoney.algos.ma_cross_algo import MACrossAlgo
from stablemoney.algos.macd_algo import MacdAlgo
from stablemoney.algos.rsi_algo import RSIAlgo

__all__ = [
    "AlgoConfig",
    "BaseAlgo",
    "KDJMacdAlgo",
    "KdjMacdMaAlgo",
    "KdjZxtrendAlgo",
    "MACrossAlgo",
    "MacdAlgo",
    "RSIAlgo",
]
