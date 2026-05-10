"""Tests for volume indicator factory functions."""

from __future__ import annotations

from stablemoney.indicators.volume import OBV, VOL_MA


class TestOBV:
    def test_default(self) -> None:
        ind = OBV()
        assert ind.name == "OBV"
        assert ind.params == {}
        assert ind.outputs == ("value",)
        assert ind.formula_arg == ""
        assert ind.full_name == "OBV"


class TestVOLMA:
    def test_default(self) -> None:
        ind = VOL_MA()
        assert ind.name == "VOL_MA"
        assert ind.params == {"period": 20}
        assert ind.outputs == ("value",)

    def test_custom_period(self) -> None:
        ind = VOL_MA(30)
        assert ind.formula_arg == "30"
