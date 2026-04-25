"""Tests for MarketSector enum and SectorFilter."""

from __future__ import annotations

from dataclasses import FrozenInstanceError

import pytest

from stablemoney.market_sector import MarketSector, SectorFilter


class TestMarketSector:
    def test_all_a_shares(self) -> None:
        assert MarketSector.ALL == "5"

    def test_main_sh(self) -> None:
        assert MarketSector.MAIN_SH == "7"

    def test_main_sz(self) -> None:
        assert MarketSector.MAIN_SZ == "8"

    def test_chinext(self) -> None:
        assert MarketSector.CHINEXT == "51"

    def test_star(self) -> None:
        assert MarketSector.STAR == "52"

    def test_bse(self) -> None:
        assert MarketSector.BSE == "53"

    def test_is_string(self) -> None:
        assert isinstance(MarketSector.CHINEXT, str)

    def test_value_access(self) -> None:
        assert MarketSector.CHINEXT.value == "51"

    def test_from_value(self) -> None:
        assert MarketSector("51") is MarketSector.CHINEXT

    def test_invalid_value(self) -> None:
        with pytest.raises(ValueError):
            MarketSector("999")


class TestSectorFilterDefaults:
    def test_default_max_stocks(self) -> None:
        sf = SectorFilter()
        assert sf.max_stocks is None

    def test_default_sort_by(self) -> None:
        sf = SectorFilter()
        assert sf.sort_by is None

    def test_default_sort_ascending(self) -> None:
        sf = SectorFilter()
        assert sf.sort_ascending is True

    def test_default_min_market_cap(self) -> None:
        sf = SectorFilter()
        assert sf.min_market_cap is None

    def test_default_max_market_cap(self) -> None:
        sf = SectorFilter()
        assert sf.max_market_cap is None


class TestSectorFilterCustom:
    def test_custom_values(self) -> None:
        sf = SectorFilter(
            max_stocks=50,
            sort_by="market_cap",
            sort_ascending=False,
            min_market_cap=300.0,
            max_market_cap=500.0,
        )
        assert sf.max_stocks == 50
        assert sf.sort_by == "market_cap"
        assert sf.sort_ascending is False
        assert sf.min_market_cap == 300.0
        assert sf.max_market_cap == 500.0


class TestSectorFilterFrozen:
    def test_frozen(self) -> None:
        sf = SectorFilter()
        with pytest.raises(FrozenInstanceError):
            sf.max_stocks = 10  # type: ignore[misc]
