"""Fixtures for RSI algo tests."""

from __future__ import annotations

from unittest.mock import MagicMock

import numpy as np
import pytest

from stablemoney.algo_config import AlgoConfig
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


@pytest.fixture
def default_algo() -> RSIAlgo:
    """RSIAlgo with default config (no stop loss)."""
    return RSIAlgo()


@pytest.fixture
def stop_loss_algo() -> RSIAlgo:
    """RSIAlgo with 5% stop loss."""
    return RSIAlgo(config=AlgoConfig(stop_loss_pct=5.0))
