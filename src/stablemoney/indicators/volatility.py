"""Volatility indicator definitions: BOLL, ATR."""

from __future__ import annotations

from stablemoney.indicator_def import IndicatorDef


def BOLL(period: int = 20, nbdev: int = 2) -> IndicatorDef:
    """Bollinger Bands (upper, middle, lower)."""
    return IndicatorDef(
        "BOLL",
        {"period": period, "nbdev": nbdev},
        outputs=("upper", "middle", "lower"),
    )


def ATR(period: int = 14) -> IndicatorDef:
    """Average True Range."""
    return IndicatorDef("ATR", {"period": period})
