"""Abstract interface for market data providers."""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from datetime import datetime

    import pandas as pd

    from stablemoney.indicator_def import IndicatorDef
    from stablemoney.market_sector import MarketSector, SectorFilter


class DataProvider(ABC):
    """Abstract interface for market data providers.

    Decouples data fetching logic from PyBroker's DataSource and
    strategy assembly, enabling provider swaps and isolated testing.
    """

    @abstractmethod
    def fetch_stock_data(
        self,
        symbols: frozenset[str],
        start_date: datetime,
        end_date: datetime,
        timeframe: str | None,
        indicators: list[IndicatorDef],
    ) -> pd.DataFrame:
        """Fetch OHLCV data with computed indicator columns.

        Returns a DataFrame with columns: symbol, date, open, high, low,
        close, volume, plus one column per indicator output.
        Returns empty DataFrame (symbol, date columns only) if no data.
        """
        ...

    @abstractmethod
    def resolve_sector(
        self,
        sector: MarketSector,
        sector_filter: SectorFilter | None = None,
    ) -> list[str]:
        """Resolve a market sector to a filtered list of stock codes."""
        ...
