"""Shared test fixtures for StableMoney test suite."""

from __future__ import annotations

import pytest

from stablemoney.indicator_def import IndicatorDef


@pytest.fixture
def simple_indicator() -> IndicatorDef:
    """Single-output indicator: RSI(14) -> 'RSI_14'."""
    return IndicatorDef("RSI", {"period": 14})


@pytest.fixture
def multi_indicator() -> IndicatorDef:
    """Multi-output indicator: KDJ(9,3,3) -> KDJ_9_3_3_K, KDJ_9_3_3_D, KDJ_9_3_3_J."""
    return IndicatorDef(
        "KDJ",
        {"k_period": 9, "k_smooth": 3, "d_smooth": 3},
        outputs=("K", "D", "J"),
    )


@pytest.fixture
def no_param_indicator() -> IndicatorDef:
    """Indicator with no parameters: OBV -> 'OBV'."""
    return IndicatorDef("OBV")
