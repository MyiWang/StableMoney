"""Tests for volatility indicator factory functions: BOLL, ATR."""

from __future__ import annotations

from stablemoney.indicators.volatility import ATR, BOLL


class TestBOLL:
    def test_default(self) -> None:
        ind = BOLL()
        assert ind.name == "BOLL"
        assert ind.outputs == ("upper", "middle", "lower")
        assert ind.full_name == "BOLL_20_2"

    def test_column_names(self) -> None:
        assert BOLL().column_names == [
            "BOLL_upper",
            "BOLL_middle",
            "BOLL_lower",
        ]

    def test_custom(self) -> None:
        assert BOLL(10, 3).full_name == "BOLL_10_3"


class TestATR:
    def test_default(self) -> None:
        assert ATR().full_name == "ATR_14"

    def test_custom(self) -> None:
        assert ATR(20).full_name == "ATR_20"
