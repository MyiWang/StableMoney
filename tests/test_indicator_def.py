"""Tests for IndicatorDef dataclass."""

from __future__ import annotations

from dataclasses import FrozenInstanceError

import pytest
from stablemoney.indicator_def import IndicatorDef


class TestFullName:
    def test_single_param(self, simple_indicator: IndicatorDef) -> None:
        assert simple_indicator.full_name == "RSI_14"

    def test_multi_param(self, multi_indicator: IndicatorDef) -> None:
        assert multi_indicator.full_name == "KDJ_9_3_3"

    def test_no_param(self, no_param_indicator: IndicatorDef) -> None:
        assert no_param_indicator.full_name == "OBV"


class TestColumnNames:
    def test_single_output(self, simple_indicator: IndicatorDef) -> None:
        assert simple_indicator.column_names == ["RSI_14"]

    def test_multi_output(self, multi_indicator: IndicatorDef) -> None:
        assert multi_indicator.column_names == ["KDJ_K", "KDJ_D", "KDJ_J"]

    def test_no_param(self, no_param_indicator: IndicatorDef) -> None:
        assert no_param_indicator.column_names == ["OBV"]


class TestFormulaArg:
    def test_single_param(self, simple_indicator: IndicatorDef) -> None:
        assert simple_indicator.formula_arg == "14"

    def test_multi_param(self, multi_indicator: IndicatorDef) -> None:
        assert multi_indicator.formula_arg == "9,3,3"

    def test_no_param(self, no_param_indicator: IndicatorDef) -> None:
        assert no_param_indicator.formula_arg == ""


class TestFrozen:
    def test_frozen_name(self, simple_indicator: IndicatorDef) -> None:
        with pytest.raises(FrozenInstanceError):
            simple_indicator.name = "X"  # type: ignore[misc]

    def test_frozen_params(self, simple_indicator: IndicatorDef) -> None:
        with pytest.raises(FrozenInstanceError):
            simple_indicator.params = {}  # type: ignore[misc]


class TestDefaults:
    def test_default_outputs(self) -> None:
        ind = IndicatorDef("TEST")
        assert ind.outputs == ("value",)

    def test_default_params(self) -> None:
        ind = IndicatorDef("TEST")
        assert ind.params == {}
