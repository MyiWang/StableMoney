"""Declarative indicator definition for TDX formula engine."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class IndicatorDef:
    """Declarative indicator definition.

    Contains name, parameters, and output descriptions.
    The TDX formula engine uses ``name`` and parameter values
    (comma-joined via :attr:`formula_arg`) to call the formula.

    Attributes:
        name: TDX formula name, e.g. ``"KDJ"``, ``"RSI"``, ``"MA"``.
        params: Formula parameters as an ordered dict. Values are
            joined with commas to produce :attr:`formula_arg`.
        outputs: Output names this indicator produces.  Single-value
            indicators use the default ``("value",)``.  Multi-value
            indicators like KDJ use ``("K", "D", "J")``.
    """

    name: str
    params: dict[str, Any] = field(default_factory=dict)
    outputs: tuple[str, ...] = ("value",)

    @property
    def full_name(self) -> str:
        """Unique identifier string, e.g. ``'KDJ_9_3_3'``."""
        if not self.params:
            return self.name
        return f"{self.name}_{'_'.join(str(v) for v in self.params.values())}"

    @property
    def column_names(self) -> list[str]:
        """Generate column names for all outputs.

        Single-value indicators return ``[full_name]``.
        Multi-value indicators return ``[full_name_K, full_name_D, ...]``.
        """
        if len(self.outputs) == 1 and self.outputs[0] == "value":
            return [self.full_name]
        return [f"{self.full_name}_{out}" for out in self.outputs]

    @property
    def formula_arg(self) -> str:
        """Convert params to TDX formula argument format, e.g. ``'9,3,3'``."""
        return ",".join(str(v) for v in self.params.values())
