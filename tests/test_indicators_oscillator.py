"""Tests for oscillator indicator factory functions: RSI, KDJ, CCI, WR."""

from __future__ import annotations

from stablemoney.indicators.oscillator import CCI, KDJ, RSI, WR


class TestRSI:
    def test_default(self) -> None:
        ind = RSI()
        assert ind.name == "RSI"
        assert ind.params == {"period": 14}
        assert ind.full_name == "RSI_14"

    def test_custom_period(self) -> None:
        assert RSI(7).full_name == "RSI_7"


class TestKDJ:
    def test_default(self) -> None:
        ind = KDJ()
        assert ind.name == "KDJ"
        assert ind.outputs == ("K", "D", "J")
        assert ind.full_name == "KDJ_9_3_3"

    def test_column_names(self) -> None:
        assert KDJ().column_names == [
            "KDJ_K",
            "KDJ_D",
            "KDJ_J",
        ]

    def test_formula_arg(self) -> None:
        assert KDJ().formula_arg == "9,3,3"


class TestCCI:
    def test_default(self) -> None:
        assert CCI().full_name == "CCI_14"


class TestWR:
    def test_default(self) -> None:
        assert WR().full_name == "WR_14"
