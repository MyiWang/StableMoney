"""Tests for AlgoConfig frozen dataclass."""

from __future__ import annotations

from dataclasses import FrozenInstanceError

import pytest

from stablemoney.algo_config import AlgoConfig


def test_default_values() -> None:
    cfg = AlgoConfig()
    assert cfg.stop_loss_pct == 0.0
    assert cfg.take_profit_pct == 0.0


def test_custom_values() -> None:
    cfg = AlgoConfig(stop_loss_pct=5.0, take_profit_pct=10.0)
    assert cfg.stop_loss_pct == 5.0
    assert cfg.take_profit_pct == 10.0


def test_frozen() -> None:
    cfg = AlgoConfig(stop_loss_pct=5.0)
    with pytest.raises(FrozenInstanceError):
        cfg.stop_loss_pct = 10.0  # type: ignore[misc]


def test_equality() -> None:
    assert AlgoConfig(5.0, 10.0) == AlgoConfig(5.0, 10.0)


def test_inequality() -> None:
    assert AlgoConfig(5.0) != AlgoConfig(10.0)
