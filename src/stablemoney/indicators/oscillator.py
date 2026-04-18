"""Oscillator indicator definitions: RSI, KDJ, CCI, WR."""

from __future__ import annotations

from stablemoney.indicator_def import IndicatorDef


def RSI(period: int = 14) -> IndicatorDef:
    """Relative Strength Index."""
    return IndicatorDef("RSI", {"period": period})


def KDJ(
    k_period: int = 9,
    k_smooth: int = 3,
    d_smooth: int = 3,
) -> IndicatorDef:
    """KDJ stochastic indicator (K, D, J)."""
    return IndicatorDef(
        "KDJ",
        {"k_period": k_period, "k_smooth": k_smooth, "d_smooth": d_smooth},
        outputs=("K", "D", "J"),
    )


def CCI(period: int = 14) -> IndicatorDef:
    """Commodity Channel Index."""
    return IndicatorDef("CCI", {"period": period})


def WR(period: int = 14) -> IndicatorDef:
    """Williams %R."""
    return IndicatorDef("WR", {"period": period})
