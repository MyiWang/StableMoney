"""YAML configuration file loader and saver."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from stablemoney.strategy_config import BacktestConfig, StrategyConfig


def load_config(path: str | Path) -> tuple[StrategyConfig, BacktestConfig]:
    """Load StrategyConfig and BacktestConfig from a YAML file.

    Args:
        path: Path to the YAML configuration file.

    Returns:
        A tuple of ``(StrategyConfig, BacktestConfig)``.
    """
    path = Path(path)
    with path.open(encoding="utf-8") as f:
        data: dict[str, Any] = yaml.safe_load(f)

    strategy_data = data.get("strategy", {})
    backtest_data = data.get("backtest", {})

    strategy_config = StrategyConfig.from_dict(strategy_data)
    backtest_config = BacktestConfig.from_dict(backtest_data)
    return strategy_config, backtest_config


def save_config(
    strategy_config: StrategyConfig,
    backtest_config: BacktestConfig,
    path: str | Path,
) -> None:
    """Save StrategyConfig and BacktestConfig to a YAML file.

    Args:
        strategy_config: Strategy configuration to save.
        backtest_config: Backtest configuration to save.
        path: Path to write the YAML file.
    """
    path = Path(path)
    data = {
        "strategy": strategy_config.to_dict(),
        "backtest": backtest_config.to_dict(),
    }
    with path.open("w", encoding="utf-8") as f:
        yaml.dump(
            data, f, default_flow_style=False,
            allow_unicode=True, sort_keys=False,
        )
