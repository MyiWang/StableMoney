"""Tests for trend indicator factory functions: MA, EMA, MACD."""

from __future__ import annotations

from stablemoney.indicators.trend import EMA, MA, MACD


class TestMA:
    def test_default(self) -> None:
        ind = MA()
        assert ind.name == "MA"
        assert ind.params == {"period": 20}
        assert ind.outputs == ("value",)
        assert ind.full_name == "MA_20"

    def test_custom_period(self) -> None:
        assert MA(10).full_name == "MA_10"


class TestEMA:
    def test_default(self) -> None:
        ind = EMA()
        assert ind.name == "EMA"
        assert ind.full_name == "EMA_20"

    def test_custom_period(self) -> None:
        assert EMA(50).full_name == "EMA_50"


class TestMACD:
    def test_default(self) -> None:
        ind = MACD()
        assert ind.name == "MACD"
        assert ind.outputs == ("DIF", "DEA", "MACD")
        assert ind.full_name == "MACD_12_26_9"

    def test_custom_params(self) -> None:
        assert MACD(5, 35, 7).full_name == "MACD_5_35_7"

    def test_column_names(self) -> None:
        assert MACD().column_names == [
            "MACD_12_26_9_DIF",
            "MACD_12_26_9_DEA",
            "MACD_12_26_9_MACD",
        ]

    def test_formula_arg(self) -> None:
        assert MACD().formula_arg == "12,26,9"
