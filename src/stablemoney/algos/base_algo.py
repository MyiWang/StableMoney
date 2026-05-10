"""Abstract base class for trading algos."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Mapping

    from pybroker.context import ExecContext


class BaseAlgo(ABC):
    """Abstract base class for trading algos.

    Subclasses must implement :meth:`trade` for per-symbol execution logic.
    Override :meth:`before_trade` and :meth:`after_trade` to add
    cross-symbol hooks that run before/after all symbols on each bar.
    """

    @abstractmethod
    def trade(self, ctx: ExecContext) -> None:
        """Per-symbol trading logic. Called once per symbol per bar."""

    def before_trade(self, ctxs: Mapping[str, ExecContext]) -> None:  # noqa: B027
        """Hook called before all symbol executions on each bar."""

    def after_trade(self, ctxs: Mapping[str, ExecContext]) -> None:  # noqa: B027
        """Hook called after all symbol executions on each bar."""
