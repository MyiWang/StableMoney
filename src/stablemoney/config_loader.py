"""YAML configuration file loader and saver."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from stablemoney.strategy_config import BacktestConfig


def load_config(path: str | Path) -> BacktestConfig:
    """Load BacktestConfig from a YAML file.

    Args:
        path: Path to the YAML configuration file.

    Returns:
        A ``BacktestConfig`` instance.
    """
    path = Path(path)
    with path.open(encoding="utf-8") as f:
        data: dict[str, Any] = yaml.safe_load(f)

    backtest_data = data.get("backtest", {})
    return BacktestConfig.from_dict(backtest_data)


def save_config(
    backtest_config: BacktestConfig,
    path: str | Path,
) -> None:
    """Save BacktestConfig to a YAML file.

    Args:
        backtest_config: Backtest configuration to save.
        path: Path to write the YAML file.
    """
    path = Path(path)
    data = {"backtest": backtest_config.to_dict()}
    with path.open("w", encoding="utf-8") as f:
        yaml.dump(
            data,
            f,
            default_flow_style=False,
            allow_unicode=True,
            sort_keys=False,
        )
