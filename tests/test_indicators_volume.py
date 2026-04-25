"""Tests for volume indicator factory functions: OBV, VOL_MA."""

from __future__ import annotations

from stablemoney.indicators.volume import OBV, VOL_MA


class TestOBV:
    def test_no_params(self) -> None:
        ind = OBV()
        assert ind.name == "OBV"
        assert ind.params == {}
        assert ind.full_name == "OBV"
        assert ind.formula_arg == ""


class TestVolMA:
    def test_default(self) -> None:
        assert VOL_MA().full_name == "VOL_MA_20"

    def test_custom(self) -> None:
        assert VOL_MA(30).full_name == "VOL_MA_30"
