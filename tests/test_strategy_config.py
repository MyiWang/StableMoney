"""Tests for BacktestConfig and YAML serialization."""

from __future__ import annotations

from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest
from stablemoney.indicator_def import IndicatorDef
from stablemoney.indicators import MACD, MA, RSI
from stablemoney.market_sector import MarketSector, SectorFilter
from stablemoney.strategy_config import BacktestConfig


def _make_symbols_config(**kwargs: object) -> BacktestConfig:
    """Create a config with symbols."""
    defaults = {
        "symbols": ["600519.SH"],
        "start_date": "2024-01-01",
        "end_date": "2024-12-31",
    }
    defaults.update(kwargs)
    return BacktestConfig(**defaults)  # type: ignore[arg-type]


class TestConstruction:
    def test_symbols_config(self) -> None:
        config = _make_symbols_config()
        assert config.symbols == ["600519.SH"]
        assert config.start_date == "2024-01-01"

    def test_sector_config(self) -> None:
        config = BacktestConfig(
            sector=MarketSector.CHINEXT,
            start_date="2024-01-01",
            end_date="2024-12-31",
        )
        assert config.sector == MarketSector.CHINEXT
        assert config.symbols == []

    def test_with_indicators(self) -> None:
        config = _make_symbols_config(indicators=[RSI(14), MA(20)])
        assert len(config.indicators) == 2
        assert config.indicators[0].name == "RSI"

    def test_with_sector_filter(self) -> None:
        sf = SectorFilter(max_stocks=50, sort_by="market_cap")
        config = BacktestConfig(
            sector=MarketSector.ALL,
            start_date="2024-01-01",
            end_date="2024-12-31",
            sector_filter=sf,
        )
        assert config.sector_filter is not None
        assert config.sector_filter.max_stocks == 50

    def test_defaults(self) -> None:
        config = BacktestConfig(symbols=["600519.SH"])
        assert config.initial_cash == 100_000
        assert config.period == "1d"
        assert config.dividend_type == "front"
        assert config.warmup is None
        assert config.sector is None
        assert config.sector_filter is None


class TestFrozen:
    def test_frozen(self) -> None:
        config = _make_symbols_config()
        with pytest.raises(FrozenInstanceError):
            config.start_date = "2025-01-01"  # type: ignore[misc]


class TestSerialize:
    def test_symbols_config(self) -> None:
        config = _make_symbols_config(indicators=[RSI(14)])
        data = config._serialize()
        assert data["symbols"] == ["600519.SH"]
        assert data["start_date"] == "2024-01-01"
        assert len(data["indicators"]) == 1
        assert data["indicators"][0]["name"] == "RSI"

    def test_sector_config(self) -> None:
        config = BacktestConfig(
            sector=MarketSector.CHINEXT,
            start_date="2024-01-01",
            end_date="2024-12-31",
        )
        data = config._serialize()
        assert data["sector"] == "51"
        assert "symbols" in data

    def test_sector_filter_serialized(self) -> None:
        sf = SectorFilter(max_stocks=10, sort_by="float_cap")
        config = BacktestConfig(
            sector=MarketSector.ALL,
            start_date="2024-01-01",
            end_date="2024-12-31",
            sector_filter=sf,
        )
        data = config._serialize()
        assert data["sector_filter"]["max_stocks"] == 10
        assert data["sector_filter"]["sort_by"] == "float_cap"

    def test_warmup_included_when_set(self) -> None:
        config = _make_symbols_config(warmup=100)
        data = config._serialize()
        assert data["warmup"] == 100

    def test_warmup_omitted_when_none(self) -> None:
        config = _make_symbols_config()
        data = config._serialize()
        assert "warmup" not in data

    def test_multi_output_indicator(self) -> None:
        config = _make_symbols_config(indicators=[MACD()])
        data = config._serialize()
        assert data["indicators"][0]["outputs"] == ["DIF", "DEA", "MACD"]


class TestDeserialize:
    def test_symbols_config(self) -> None:
        data = {
            "symbols": ["600519.SH"],
            "start_date": "2024-01-01",
            "end_date": "2024-12-31",
            "indicators": [{"name": "RSI", "params": {"period": 14}}],
        }
        config = BacktestConfig._deserialize(data)
        assert config.symbols == ["600519.SH"]
        assert len(config.indicators) == 1
        assert config.indicators[0].name == "RSI"

    def test_sector_config(self) -> None:
        data = {
            "symbols": [],
            "sector": "51",
            "start_date": "2024-01-01",
            "end_date": "2024-12-31",
        }
        config = BacktestConfig._deserialize(data)
        assert config.sector == MarketSector.CHINEXT

    def test_sector_filter_deserialized(self) -> None:
        data = {
            "symbols": [],
            "sector": "5",
            "start_date": "2024-01-01",
            "end_date": "2024-12-31",
            "sector_filter": {"max_stocks": 20, "sort_by": "market_cap"},
        }
        config = BacktestConfig._deserialize(data)
        assert config.sector_filter is not None
        assert config.sector_filter.max_stocks == 20

    def test_warmup(self) -> None:
        data = {
            "symbols": ["600519.SH"],
            "start_date": "2024-01-01",
            "end_date": "2024-12-31",
            "warmup": 100,
        }
        config = BacktestConfig._deserialize(data)
        assert config.warmup == 100


class TestYamlRoundTrip:
    def test_save_and_load(self, tmp_path: Path) -> None:
        config = _make_symbols_config(
            indicators=[RSI(14), MA(20)],
            warmup=100,
        )
        yaml_path = tmp_path / "config.yaml"
        config.save(yaml_path)
        loaded = BacktestConfig.from_yaml(yaml_path)
        assert loaded.symbols == config.symbols
        assert loaded.start_date == config.start_date
        assert loaded.warmup == config.warmup
        assert len(loaded.indicators) == 2

    def test_sector_round_trip(self, tmp_path: Path) -> None:
        sf = SectorFilter(max_stocks=50, sort_by="market_cap")
        config = BacktestConfig(
            sector=MarketSector.STAR,
            start_date="2024-01-01",
            end_date="2024-12-31",
            sector_filter=sf,
        )
        yaml_path = tmp_path / "config.yaml"
        config.save(yaml_path)
        loaded = BacktestConfig.from_yaml(yaml_path)
        assert loaded.sector == MarketSector.STAR
        assert loaded.sector_filter is not None
        assert loaded.sector_filter.max_stocks == 50

    def test_indicator_outputs_preserved(self, tmp_path: Path) -> None:
        config = _make_symbols_config(indicators=[MACD(6, 13, 5)])
        yaml_path = tmp_path / "config.yaml"
        config.save(yaml_path)
        loaded = BacktestConfig.from_yaml(yaml_path)
        assert loaded.indicators[0].outputs == ("DIF", "DEA", "MACD")
        assert loaded.indicators[0].params == {"short": 6, "long": 13, "signal": 5}
