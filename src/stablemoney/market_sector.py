"""Market sector enum and sector filter for stock list resolution."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class MarketSector(str, Enum):
    """A-share market sectors mapped to TDX ``get_stock_list`` market codes.

    Usage::

        sector = MarketSector.CHINEXT
        codes = tq.get_stock_list(market=sector.value)
    """

    ALL = "5"
    MAIN_SH = "7"
    MAIN_SZ = "8"
    CHINEXT = "51"
    STAR = "52"
    BSE = "53"


@dataclass(frozen=True)
class SectorFilter:
    """Filter and limit stocks resolved from a market sector.

    Supported ``sort_by`` values:

    - ``"market_cap"`` → sorted by total market cap (总市值, 亿元)
    - ``"float_cap"``  → sorted by float market cap (流通市值, 亿元)

    Market cap is calculated from close price × shares outstanding.

    Execution order: sort → filter by ``min_market_cap``/``max_market_cap``
    → limit to ``max_stocks``.
    """

    max_stocks: int | None = None
    sort_by: str | None = None
    sort_ascending: bool = True
    min_market_cap: float | None = None
    max_market_cap: float | None = None
