"""StockInfo dataclass for market cap calculations."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class StockInfo:
    """Single stock's basic financial info.

    Holds price, shares, and computed market cap for sector filtering.
    """

    code: str
    close_price: float
    shares_wan: float
    market_cap_yi: float
