"""Algo configuration for common risk control parameters."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class AlgoConfig:
    """Common risk control parameters for algos.

    Passed to algo constructors and accessible via ``algo.config``.
    """

    stop_loss_pct: float = 0.0
    take_profit_pct: float = 0.0
    hold_bars: int = 0
