"""Algo protocol for strategy execution logic."""
from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from pybroker.context import ExecContext


@runtime_checkable
class Algo(Protocol):
    """Protocol for callable trading algorithms.

    Any class that implements ``__call__(ctx) -> None`` satisfies this
    protocol. No inheritance required.
    """

    def __call__(self, ctx: ExecContext) -> None:
        """Execute trading logic for the current bar."""
        ...
