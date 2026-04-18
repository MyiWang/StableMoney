"""Volume indicator definitions: OBV, VOL_MA."""

from __future__ import annotations

from stablemoney.indicator_def import IndicatorDef


def OBV() -> IndicatorDef:
    """On Balance Volume."""
    return IndicatorDef("OBV")


def VOL_MA(period: int = 20) -> IndicatorDef:
    """Volume Moving Average."""
    return IndicatorDef("VOL_MA", {"period": period})
