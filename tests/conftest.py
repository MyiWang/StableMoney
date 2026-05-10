"""Shared fixtures for indicator tests."""

from __future__ import annotations

import pytest
from stablemoney.indicator_def import IndicatorDef


@pytest.fixture
def simple_indicator() -> IndicatorDef:
    """Single-output indicator: RSI(14)."""
    return IndicatorDef("RSI", {"period": 14})


@pytest.fixture
def multi_indicator() -> IndicatorDef:
    """Multi-output indicator: KDJ(9, 3, 3)."""
    return IndicatorDef(
        "KDJ",
        {"k_period": 9, "k_smooth": 3, "d_smooth": 3},
        outputs=("K", "D", "J"),
    )


@pytest.fixture
def no_param_indicator() -> IndicatorDef:
    """No-parameter indicator: OBV."""
    return IndicatorDef("OBV")
