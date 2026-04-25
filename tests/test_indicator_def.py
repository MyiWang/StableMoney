"""Tests for IndicatorDef dataclass and properties."""

from __future__ import annotations

from dataclasses import FrozenInstanceError

import pytest

from stablemoney.indicator_def import IndicatorDef


class TestFullName:
    def test_with_params(self, simple_indicator: IndicatorDef) -> None:
        assert simple_indicator.full_name == "RSI_14"

    def test_multi_params(self, multi_indicator: IndicatorDef) -> None:
        assert multi_indicator.full_name == "KDJ_9_3_3"

    def test_no_params(self, no_param_indicator: IndicatorDef) -> None:
        assert no_param_indicator.full_name == "OBV"

    def test_mixed_param_types(self) -> None:
        ind = IndicatorDef("X", {"a": 2.5, "b": 10})
        assert ind.full_name == "X_2.5_10"


class TestColumnNames:
    def test_single_output(self, simple_indicator: IndicatorDef) -> None:
        assert simple_indicator.column_names == ["RSI_14"]

    def test_multi_output(self, multi_indicator: IndicatorDef) -> None:
        assert multi_indicator.column_names == [
            "KDJ_K",
            "KDJ_D",
            "KDJ_J",
        ]

    def test_no_params(self, no_param_indicator: IndicatorDef) -> None:
        assert no_param_indicator.column_names == ["OBV"]


class TestFormulaArg:
    def test_with_params(self, simple_indicator: IndicatorDef) -> None:
        assert simple_indicator.formula_arg == "14"

    def test_multi_params(self, multi_indicator: IndicatorDef) -> None:
        assert multi_indicator.formula_arg == "9,3,3"

    def test_no_params(self, no_param_indicator: IndicatorDef) -> None:
        assert no_param_indicator.formula_arg == ""


class TestFrozenAndDefaults:
    def test_frozen(self) -> None:
        ind = IndicatorDef("X")
        with pytest.raises(FrozenInstanceError):
            ind.name = "Y"  # type: ignore[misc]

    def test_default_outputs_is_value(self) -> None:
        ind = IndicatorDef("TEST", {"p": 1})
        assert ind.outputs == ("value",)
