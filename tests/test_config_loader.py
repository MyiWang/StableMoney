"""Tests for YAML config loader and saver."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
import yaml

from stablemoney.config_loader import load_config, save_config
from stablemoney.strategy_config import BacktestConfig

if TYPE_CHECKING:
    from pathlib import Path

    from stablemoney.indicator_def import IndicatorDef


def _make_config(indicators: list[IndicatorDef] | None = None) -> BacktestConfig:
    return BacktestConfig(
        symbols=["600519.SH"],
        start_date="2024-01-01",
        end_date="2024-12-31",
        indicators=indicators or [],
    )


def test_save_and_load_roundtrip(
    tmp_path: Path,
    simple_indicator: IndicatorDef,
) -> None:
    original = BacktestConfig(
        symbols=["600519.SH", "000858.SZ"],
        start_date="2024-01-01",
        end_date="2024-12-31",
        initial_cash=500_000,
        indicators=[simple_indicator],
        warmup=100,
    )
    path = tmp_path / "config.yaml"
    save_config(original, path)
    loaded = load_config(path)
    assert loaded == original


def test_save_creates_file(tmp_path: Path) -> None:
    path = tmp_path / "config.yaml"
    save_config(_make_config(), path)
    assert path.exists()


def test_save_yaml_structure(
    tmp_path: Path,
    simple_indicator: IndicatorDef,
) -> None:
    path = tmp_path / "config.yaml"
    save_config(
        BacktestConfig(
            symbols=["600519.SH"],
            start_date="2024-01-01",
            end_date="2024-12-31",
            indicators=[simple_indicator],
        ),
        path,
    )
    with path.open(encoding="utf-8") as f:
        raw = yaml.safe_load(f)
    assert "backtest" in raw
    assert "indicators" in raw["backtest"]
    assert len(raw["backtest"]["indicators"]) == 1


def test_load_from_string_path(tmp_path: Path) -> None:
    path = tmp_path / "config.yaml"
    save_config(_make_config(), path)
    loaded = load_config(str(path))
    assert loaded.symbols == ["600519.SH"]


def test_load_missing_file_raises(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        load_config(tmp_path / "nonexistent.yaml")


def test_empty_indicators(tmp_path: Path) -> None:
    path = tmp_path / "config.yaml"
    save_config(_make_config(indicators=[]), path)
    loaded = load_config(path)
    assert loaded.indicators == []


def test_save_with_warmup(tmp_path: Path) -> None:
    cfg = BacktestConfig(
        symbols=["600519.SH"],
        start_date="2024-01-01",
        end_date="2024-12-31",
        warmup=50,
    )
    path = tmp_path / "config.yaml"
    save_config(cfg, path)
    loaded = load_config(path)
    assert loaded.warmup == 50
