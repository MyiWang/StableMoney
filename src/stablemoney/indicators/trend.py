"""Trend indicator definitions: MA, EMA, MACD."""

from __future__ import annotations

from stablemoney.indicator_def import IndicatorDef


def MA(period: int = 20) -> IndicatorDef:
    """Simple Moving Average."""
    return IndicatorDef("MA", {"period": period})


def EMA(period: int = 20) -> IndicatorDef:
    """Exponential Moving Average."""
    return IndicatorDef("EMA", {"period": period})


def MACD(
    short: int = 12,
    long: int = 26,
    signal: int = 9,
) -> IndicatorDef:
    """MACD indicator (DIF, DEA, MACD)."""
    return IndicatorDef(
        "MACD",
        {"short": short, "long": long, "signal": signal},
        outputs=("DIF", "DEA", "MACD"),
    )
