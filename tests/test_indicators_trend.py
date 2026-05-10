"""Tests for trend indicator factory functions."""

from __future__ import annotations

from stablemoney.indicator_def import IndicatorDef
from stablemoney.indicators.trend import EMA, MACD, MA, ZXTREND


class TestMA:
    def test_default(self) -> None:
        ind = MA()
        assert ind.name == "MA"
        assert ind.params == {"period": 20}
        assert ind.outputs == ("value",)
        assert ind.formula_arg == "20"
        assert ind.full_name == "MA_20"

    def test_custom_period(self) -> None:
        ind = MA(60)
        assert ind.params == {"period": 60}
        assert ind.full_name == "MA_60"


class TestEMA:
    def test_default(self) -> None:
        ind = EMA()
        assert ind.name == "EMA"
        assert ind.params == {"period": 20}
        assert ind.outputs == ("value",)

    def test_custom_period(self) -> None:
        ind = EMA(12)
        assert ind.formula_arg == "12"
        assert ind.full_name == "EMA_12"


class TestMACD:
    def test_default(self) -> None:
        ind = MACD()
        assert ind.name == "MACD"
        assert ind.params == {"short": 12, "long": 26, "signal": 9}
        assert ind.outputs == ("DIF", "DEA", "MACD")
        assert ind.formula_arg == "12,26,9"
        assert ind.column_names == ["MACD_DIF", "MACD_DEA", "MACD_MACD"]

    def test_custom_params(self) -> None:
        ind = MACD(short=6, long=13, signal=5)
        assert ind.formula_arg == "6,13,5"
        assert ind.full_name == "MACD_6_13_5"


class TestZXTREND:
    def test_default(self) -> None:
        ind = ZXTREND()
        assert ind.name == "ZXTREND"
        assert ind.params == {"M1": 14, "M2": 28, "M3": 57, "M4": 114}
        assert ind.outputs == ("SHORT_T", "LONG_T")
        assert ind.formula_arg == "14,28,57,114"
        assert ind.column_names == ["ZXTREND_SHORT_T", "ZXTREND_LONG_T"]

    def test_custom_params(self) -> None:
        ind = ZXTREND(m1=7, m2=14, m3=28, m4=56)
        assert ind.formula_arg == "7,14,28,56"
