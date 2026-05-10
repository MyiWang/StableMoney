"""Trend indicator definitions: MA, EMA, MACD, ZXTREND."""

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


def ZXTREND(
    m1: int = 14,
    m2: int = 28,
    m3: int = 57,
    m4: int = 114,
) -> IndicatorDef:
    """ZXTREND custom indicator (SHORT_T, LONG_T)."""
    return IndicatorDef(
        "ZXTREND",
        {"M1": m1, "M2": m2, "M3": m3, "M4": m4},
        outputs=("SHORT_T", "LONG_T"),
    )
