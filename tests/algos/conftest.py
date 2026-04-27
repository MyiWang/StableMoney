"""Fixtures for algo tests."""

from __future__ import annotations

from unittest.mock import MagicMock

import numpy as np
import pytest

from stablemoney.algos.algo_config import AlgoConfig
from stablemoney.algos.kdj_macd_algo import KDJMacdAlgo
from stablemoney.algos.kdj_macd_ma_algo import KdjMacdMaAlgo
from stablemoney.algos.ma_cross_algo import MACrossAlgo
from stablemoney.algos.macd_algo import MacdAlgo
from stablemoney.algos.rsi_algo import RSIAlgo


def make_exec_context(
    *,
    rsi_value: float,
    ma_value: float,
    close_price: float,
    has_position: bool = False,
    entry_price: float | None = None,
    initial_cash: float = 100_000,
) -> MagicMock:
    """Create a mock ExecContext for RSIAlgo tests."""
    ctx = MagicMock()
    ctx.RSI_14 = np.array([rsi_value])
    ctx.MA_20 = np.array([ma_value])
    ctx.close = np.array([close_price])
    ctx.date = np.array([np.datetime64("2024-06-01")])
    ctx.config = MagicMock()
    ctx.config.initial_cash = initial_cash
    ctx.buy_shares = 0

    if has_position:
        pos = MagicMock()
        entry_mock = MagicMock()
        entry_mock.price = entry_price if entry_price is not None else close_price
        pos.entries = [entry_mock]
        ctx.long_pos.return_value = pos
    else:
        ctx.long_pos.return_value = None

    return ctx


def make_kdj_macd_context(
    *,
    kdj_j: list[float],
    macd_dif: float,
    macd_dea: float,
    ma_20: float,
    ma_60: float,
    close_price: float = 10.0,
    has_position: bool = False,
    entry_price: float | None = None,
    initial_cash: float = 100_000,
) -> MagicMock:
    """Create a mock ExecContext for KDJMacdAlgo tests.

    kdj_j is a list of 2 values: [prev, current].
    """
    ctx = MagicMock()
    ctx.KDJ_J = np.array(kdj_j)
    ctx.MACD_DIF = np.array([macd_dif])
    ctx.MACD_DEA = np.array([macd_dea])
    ctx.MA_20 = np.array([ma_20])
    ctx.MA_60 = np.array([ma_60])
    ctx.close = np.array([close_price])
    ctx.date = np.array([np.datetime64("2024-06-01")])
    ctx.config = MagicMock()
    ctx.config.initial_cash = initial_cash
    ctx.buy_shares = 0

    if has_position:
        pos = MagicMock()
        entry_mock = MagicMock()
        entry_mock.price = entry_price if entry_price is not None else close_price
        pos.entries = [entry_mock]
        ctx.long_pos.return_value = pos
    else:
        ctx.long_pos.return_value = None

    return ctx


@pytest.fixture
def default_algo() -> RSIAlgo:
    """RSIAlgo with default config (no stop loss)."""
    return RSIAlgo()


@pytest.fixture
def stop_loss_algo() -> RSIAlgo:
    """RSIAlgo with 5% stop loss."""
    return RSIAlgo(config=AlgoConfig(stop_loss_pct=5.0))


@pytest.fixture
def kdj_macd_algo() -> KDJMacdAlgo:
    """KDJMacdAlgo with default config."""
    return KDJMacdAlgo()


def make_macd_context(
    *,
    macd_dif: list[float],
    macd_dea: list[float],
    close_price: float = 10.0,
    has_position: bool = False,
    entry_price: float | None = None,
    initial_cash: float = 100_000,
) -> MagicMock:
    """Create a mock ExecContext for MacdAlgo tests.

    macd_dif and macd_dea are lists of 2 values: [prev, current].
    """
    ctx = MagicMock()
    ctx.MACD_DIF = np.array(macd_dif)
    ctx.MACD_DEA = np.array(macd_dea)
    ctx.close = np.array([close_price])
    ctx.date = np.array([np.datetime64("2024-06-01")])
    ctx.config = MagicMock()
    ctx.config.initial_cash = initial_cash
    ctx.buy_shares = 0

    if has_position:
        pos = MagicMock()
        entry_mock = MagicMock()
        entry_mock.price = entry_price if entry_price is not None else close_price
        pos.entries = [entry_mock]
        ctx.long_pos.return_value = pos
    else:
        ctx.long_pos.return_value = None

    return ctx


@pytest.fixture
def macd_algo() -> MacdAlgo:
    """MacdAlgo with default config."""
    return MacdAlgo()


@pytest.fixture
def macd_algo_with_risk() -> MacdAlgo:
    """MacdAlgo with risk management config."""
    return MacdAlgo(
        config=AlgoConfig(stop_loss_pct=3, take_profit_pct=10, hold_bars=20),
    )


def make_ma_cross_context(
    *,
    ma_short: list[float],
    ma_long: list[float],
    close_price: float = 10.0,
    has_position: bool = False,
    entry_price: float | None = None,
    initial_cash: float = 100_000,
) -> MagicMock:
    """Create a mock ExecContext for MACrossAlgo tests.

    ma_short and ma_long are lists of 2 values: [prev, current].
    """
    ctx = MagicMock()
    ctx.MA_10 = np.array(ma_short)
    ctx.MA_20 = np.array(ma_long)
    ctx.close = np.array([close_price])
    ctx.date = np.array([np.datetime64("2024-06-01")])
    ctx.config = MagicMock()
    ctx.config.initial_cash = initial_cash
    ctx.buy_shares = 0

    if has_position:
        pos = MagicMock()
        entry_mock = MagicMock()
        entry_mock.price = entry_price if entry_price is not None else close_price
        pos.entries = [entry_mock]
        ctx.long_pos.return_value = pos
    else:
        ctx.long_pos.return_value = None

    return ctx


@pytest.fixture
def ma_cross_algo() -> MACrossAlgo:
    """MACrossAlgo with default config."""
    return MACrossAlgo()


@pytest.fixture
def ma_cross_algo_with_risk() -> MACrossAlgo:
    """MACrossAlgo with risk management config."""
    return MACrossAlgo(
        config=AlgoConfig(stop_loss_pct=3, take_profit_pct=10, hold_bars=20),
    )


def make_kdj_macd_ma_context(
    *,
    kdj_j: float,
    macd_dif: float,
    macd_dea: float,
    ma_short: float,
    ma_long: float,
    close_price: float = 10.0,
    has_position: bool = False,
    entry_price: float | None = None,
    initial_cash: float = 100_000,
) -> MagicMock:
    """Create a mock ExecContext for KdjMacdMaAlgo tests."""
    ctx = MagicMock()
    ctx.KDJ_J = np.array([kdj_j])
    ctx.MACD_DIF = np.array([macd_dif])
    ctx.MACD_DEA = np.array([macd_dea])
    ctx.MA_10 = np.array([ma_short])
    ctx.MA_20 = np.array([ma_long])
    ctx.close = np.array([close_price])
    ctx.date = np.array([np.datetime64("2024-06-01")])
    ctx.config = MagicMock()
    ctx.config.initial_cash = initial_cash
    ctx.buy_shares = 0

    if has_position:
        pos = MagicMock()
        entry_mock = MagicMock()
        entry_mock.price = entry_price if entry_price is not None else close_price
        pos.entries = [entry_mock]
        ctx.long_pos.return_value = pos
    else:
        ctx.long_pos.return_value = None

    return ctx


@pytest.fixture
def kdj_macd_ma_algo() -> KdjMacdMaAlgo:
    """KdjMacdMaAlgo with default config."""
    return KdjMacdMaAlgo()
