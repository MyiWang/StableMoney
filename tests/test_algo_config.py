"""Tests for AlgoConfig dataclass."""

from __future__ import annotations

from dataclasses import FrozenInstanceError

import pytest
from stablemoney.algos.algo_config import AlgoConfig


class TestDefaults:
    def test_stop_loss(self) -> None:
        config = AlgoConfig()
        assert config.stop_loss_pct == 0.0

    def test_take_profit(self) -> None:
        config = AlgoConfig()
        assert config.take_profit_pct == 0.0

    def test_hold_bars(self) -> None:
        config = AlgoConfig()
        assert config.hold_bars == 0


class TestCustomValues:
    def test_stop_loss(self) -> None:
        config = AlgoConfig(stop_loss_pct=5.0)
        assert config.stop_loss_pct == 5.0

    def test_take_profit(self) -> None:
        config = AlgoConfig(take_profit_pct=10.0)
        assert config.take_profit_pct == 10.0

    def test_hold_bars(self) -> None:
        config = AlgoConfig(hold_bars=30)
        assert config.hold_bars == 30

    def test_all_params(self) -> None:
        config = AlgoConfig(stop_loss_pct=3.0, take_profit_pct=8.0, hold_bars=15)
        assert config.stop_loss_pct == 3.0
        assert config.take_profit_pct == 8.0
        assert config.hold_bars == 15


class TestFrozen:
    def test_frozen(self) -> None:
        config = AlgoConfig(stop_loss_pct=5.0)
        with pytest.raises(FrozenInstanceError):
            config.stop_loss_pct = 10.0  # type: ignore[misc]


class TestEquality:
    def test_equal(self) -> None:
        assert AlgoConfig(5.0, 10.0, 15) == AlgoConfig(5.0, 10.0, 15)

    def test_not_equal(self) -> None:
        assert AlgoConfig(5.0) != AlgoConfig(10.0)
