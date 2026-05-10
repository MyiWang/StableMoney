"""Tests for oscillator indicator factory functions."""

from __future__ import annotations

from stablemoney.indicators.oscillator import CCI, KDJ, RSI, WR


class TestRSI:
    def test_default(self) -> None:
        ind = RSI()
        assert ind.name == "RSI"
        assert ind.params == {"period": 14}
        assert ind.outputs == ("value",)
        assert ind.full_name == "RSI_14"

    def test_custom_period(self) -> None:
        ind = RSI(6)
        assert ind.formula_arg == "6"


class TestKDJ:
    def test_default(self) -> None:
        ind = KDJ()
        assert ind.name == "KDJ"
        assert ind.params == {"k_period": 9, "k_smooth": 3, "d_smooth": 3}
        assert ind.outputs == ("K", "D", "J")
        assert ind.column_names == ["KDJ_K", "KDJ_D", "KDJ_J"]

    def test_custom_params(self) -> None:
        ind = KDJ(k_period=14, k_smooth=5, d_smooth=5)
        assert ind.formula_arg == "14,5,5"


class TestCCI:
    def test_default(self) -> None:
        ind = CCI()
        assert ind.name == "CCI"
        assert ind.params == {"period": 14}
        assert ind.outputs == ("value",)

    def test_custom_period(self) -> None:
        ind = CCI(28)
        assert ind.full_name == "CCI_28"


class TestWR:
    def test_default(self) -> None:
        ind = WR()
        assert ind.name == "WR"
        assert ind.params == {"period": 14}

    def test_custom_period(self) -> None:
        ind = WR(10)
        assert ind.formula_arg == "10"
