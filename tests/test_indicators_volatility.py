"""Tests for volatility indicator factory functions."""

from __future__ import annotations

from stablemoney.indicators.volatility import ATR, BOLL


class TestBOLL:
    def test_default(self) -> None:
        ind = BOLL()
        assert ind.name == "BOLL"
        assert ind.params == {"period": 20, "nbdev": 2}
        assert ind.outputs == ("upper", "middle", "lower")
        assert ind.column_names == ["BOLL_upper", "BOLL_middle", "BOLL_lower"]

    def test_custom_params(self) -> None:
        ind = BOLL(period=10, nbdev=3)
        assert ind.formula_arg == "10,3"


class TestATR:
    def test_default(self) -> None:
        ind = ATR()
        assert ind.name == "ATR"
        assert ind.params == {"period": 14}
        assert ind.outputs == ("value",)

    def test_custom_period(self) -> None:
        ind = ATR(20)
        assert ind.full_name == "ATR_20"
