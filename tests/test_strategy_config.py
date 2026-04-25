"""Tests for BacktestConfig serialization."""

from __future__ import annotations

from dataclasses import FrozenInstanceError
from typing import TYPE_CHECKING

import pytest

from stablemoney.strategy_config import BacktestConfig
from stablemoney.market_sector import MarketSector, SectorFilter

if TYPE_CHECKING:
    from stablemoney.indicator_def import IndicatorDef


class TestToDict:
    def test_minimal(self) -> None:
        cfg = BacktestConfig(
            symbols=["600519.SH"],
            start_date="2024-01-01",
            end_date="2024-12-31",
        )
        d = cfg.to_dict()
        assert d["symbols"] == ["600519.SH"]
        assert d["start_date"] == "2024-01-01"
        assert d["end_date"] == "2024-12-31"
        assert d["initial_cash"] == 100_000
        assert "warmup" not in d
        assert d["indicators"] == []

    def test_with_indicators(
        self,
        simple_indicator: IndicatorDef,
        multi_indicator: IndicatorDef,
    ) -> None:
        cfg = BacktestConfig(
            symbols=["600519.SH"],
            start_date="2024-01-01",
            end_date="2024-12-31",
            indicators=[simple_indicator, multi_indicator],
        )
        d = cfg.to_dict()
        assert len(d["indicators"]) == 2
        assert d["indicators"][0] == {
            "name": "RSI",
            "params": {"period": 14},
            "outputs": ["value"],
        }

    def test_with_warmup(self) -> None:
        cfg = BacktestConfig(
            symbols=["600519.SH"],
            start_date="2024-01-01",
            end_date="2024-12-31",
            warmup=50,
        )
        assert cfg.to_dict()["warmup"] == 50

    def test_without_warmup(self) -> None:
        cfg = BacktestConfig(
            symbols=["600519.SH"],
            start_date="2024-01-01",
            end_date="2024-12-31",
            warmup=None,
        )
        assert "warmup" not in cfg.to_dict()

    def test_with_sector(self) -> None:
        cfg = BacktestConfig(
            start_date="2024-01-01",
            end_date="2024-12-31",
            sector=MarketSector.CHINEXT,
        )
        d = cfg.to_dict()
        assert d["sector"] == "51"

    def test_without_sector(self) -> None:
        cfg = BacktestConfig(
            symbols=["600519.SH"],
            start_date="2024-01-01",
            end_date="2024-12-31",
        )
        assert "sector" not in cfg.to_dict()

    def test_with_sector_filter(self) -> None:
        cfg = BacktestConfig(
            start_date="2024-01-01",
            end_date="2024-12-31",
            sector=MarketSector.STAR,
            sector_filter=SectorFilter(
                max_stocks=50, sort_by="market_cap",
                min_market_cap=10.0, max_market_cap=100.0,
            ),
        )
        d = cfg.to_dict()
        assert d["sector_filter"] == {
            "max_stocks": 50,
            "sort_by": "market_cap",
            "sort_ascending": True,
            "min_market_cap": 10.0,
            "max_market_cap": 100.0,
        }

    def test_without_sector_filter(self) -> None:
        cfg = BacktestConfig(
            symbols=["600519.SH"],
            start_date="2024-01-01",
            end_date="2024-12-31",
        )
        assert "sector_filter" not in cfg.to_dict()


class TestFromDict:
    def test_minimal(self) -> None:
        cfg = BacktestConfig.from_dict(
            {
                "symbols": ["600519.SH"],
                "start_date": "2024-01-01",
                "end_date": "2024-12-31",
            }
        )
        assert cfg.symbols == ["600519.SH"]
        assert cfg.initial_cash == 100_000
        assert cfg.period == "1d"
        assert cfg.indicators == []
        assert cfg.warmup is None

    def test_all_fields(self, simple_indicator: IndicatorDef) -> None:
        cfg = BacktestConfig.from_dict(
            {
                "symbols": ["600519.SH"],
                "start_date": "2024-01-01",
                "end_date": "2024-12-31",
                "initial_cash": 500_000,
                "period": "1w",
                "dividend_type": "back",
                "indicators": [{"name": "RSI", "params": {"period": 14}}],
                "warmup": 100,
            }
        )
        assert cfg.initial_cash == 500_000
        assert cfg.period == "1w"
        assert cfg.dividend_type == "back"
        assert cfg.warmup == 100
        assert len(cfg.indicators) == 1
        assert cfg.indicators[0].name == "RSI"

    def test_outputs_as_list(self) -> None:
        cfg = BacktestConfig.from_dict(
            {
                "symbols": ["600519.SH"],
                "start_date": "2024-01-01",
                "end_date": "2024-12-31",
                "indicators": [
                    {"name": "KDJ", "params": {}, "outputs": ["K", "D", "J"]}
                ],
            }
        )
        assert cfg.indicators[0].outputs == ("K", "D", "J")

    def test_outputs_missing_defaults_to_value(self) -> None:
        cfg = BacktestConfig.from_dict(
            {
                "symbols": ["600519.SH"],
                "start_date": "2024-01-01",
                "end_date": "2024-12-31",
                "indicators": [{"name": "RSI", "params": {"period": 14}}],
            }
        )
        assert cfg.indicators[0].outputs == ("value",)

    def test_with_sector(self) -> None:
        cfg = BacktestConfig.from_dict(
            {
                "start_date": "2024-01-01",
                "end_date": "2024-12-31",
                "sector": "51",
            }
        )
        assert cfg.sector is MarketSector.CHINEXT
        assert cfg.symbols == []

    def test_with_sector_filter(self) -> None:
        cfg = BacktestConfig.from_dict(
            {
                "start_date": "2024-01-01",
                "end_date": "2024-12-31",
                "sector": "52",
                "sector_filter": {
                    "max_stocks": 30,
                    "sort_by": "pe",
                    "sort_ascending": False,
                },
            }
        )
        assert cfg.sector is MarketSector.STAR
        assert cfg.sector_filter is not None
        assert cfg.sector_filter.max_stocks == 30
        assert cfg.sector_filter.sort_by == "pe"
        assert cfg.sector_filter.sort_ascending is False

    def test_without_sector(self) -> None:
        cfg = BacktestConfig.from_dict(
            {
                "symbols": ["600519.SH"],
                "start_date": "2024-01-01",
                "end_date": "2024-12-31",
            }
        )
        assert cfg.sector is None
        assert cfg.sector_filter is None


class TestRoundtrip:
    def test_to_dict_from_dict(
        self,
        simple_indicator: IndicatorDef,
        multi_indicator: IndicatorDef,
    ) -> None:
        original = BacktestConfig(
            symbols=["600519.SH", "000858.SZ"],
            start_date="2024-01-01",
            end_date="2024-12-31",
            initial_cash=500_000,
            indicators=[simple_indicator, multi_indicator],
        )
        restored = BacktestConfig.from_dict(original.to_dict())
        assert restored == original

    def test_preserves_warmup(self) -> None:
        original = BacktestConfig(
            symbols=["600519.SH"],
            start_date="2024-01-01",
            end_date="2024-12-31",
            warmup=100,
        )
        restored = BacktestConfig.from_dict(original.to_dict())
        assert restored.warmup == 100

    def test_preserves_sector(self) -> None:
        original = BacktestConfig(
            start_date="2024-01-01",
            end_date="2024-12-31",
            sector=MarketSector.CHINEXT,
            sector_filter=SectorFilter(max_stocks=20, sort_by="float_cap"),
        )
        restored = BacktestConfig.from_dict(original.to_dict())
        assert restored.sector is MarketSector.CHINEXT
        assert restored.sector_filter is not None
        assert restored.sector_filter.max_stocks == 20
        assert restored.sector_filter.sort_by == "float_cap"


def test_frozen() -> None:
    cfg = BacktestConfig(
        symbols=["600519.SH"],
        start_date="2024-01-01",
        end_date="2024-12-31",
    )
    with pytest.raises(FrozenInstanceError):
        cfg.symbols = []  # type: ignore[misc]
