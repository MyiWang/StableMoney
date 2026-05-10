"""Tests for MarketSector enum and SectorFilter dataclass."""

from __future__ import annotations

from dataclasses import FrozenInstanceError

import pytest
from stablemoney.market_sector import MarketSector, SectorFilter


class TestMarketSector:
    def test_all(self) -> None:
        assert MarketSector.ALL.value == "5"

    def test_main_sh(self) -> None:
        assert MarketSector.MAIN_SH.value == "7"

    def test_main_sz(self) -> None:
        assert MarketSector.MAIN_SZ.value == "8"

    def test_chinext(self) -> None:
        assert MarketSector.CHINEXT.value == "51"

    def test_star(self) -> None:
        assert MarketSector.STAR.value == "52"

    def test_bse(self) -> None:
        assert MarketSector.BSE.value == "53"

    def test_member_count(self) -> None:
        assert len(MarketSector) == 6

    def test_is_str_enum(self) -> None:
        assert isinstance(MarketSector.ALL, str)


class TestSectorFilterDefaults:
    def test_max_stocks(self) -> None:
        f = SectorFilter()
        assert f.max_stocks is None

    def test_sort_by(self) -> None:
        f = SectorFilter()
        assert f.sort_by is None

    def test_sort_ascending(self) -> None:
        f = SectorFilter()
        assert f.sort_ascending is True

    def test_min_market_cap(self) -> None:
        f = SectorFilter()
        assert f.min_market_cap is None

    def test_max_market_cap(self) -> None:
        f = SectorFilter()
        assert f.max_market_cap is None


class TestSectorFilterCustom:
    def test_max_stocks(self) -> None:
        f = SectorFilter(max_stocks=50)
        assert f.max_stocks == 50

    def test_sort_by_market_cap(self) -> None:
        f = SectorFilter(sort_by="market_cap")
        assert f.sort_by == "market_cap"

    def test_cap_range(self) -> None:
        f = SectorFilter(min_market_cap=100.0, max_market_cap=500.0)
        assert f.min_market_cap == 100.0
        assert f.max_market_cap == 500.0


class TestSectorFilterFrozen:
    def test_frozen(self) -> None:
        f = SectorFilter(max_stocks=10)
        with pytest.raises(FrozenInstanceError):
            f.max_stocks = 20  # type: ignore[misc]
