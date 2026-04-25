"""BacktestConfig with serialization support."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from stablemoney.indicator_def import IndicatorDef


@dataclass(frozen=True)
class BacktestConfig:
    """Backtest run configuration.

    Contains everything needed to start a backtest run: symbols,
    date range, initial capital, indicators, and warmup period.
    """

    symbols: list[str]
    start_date: str
    end_date: str
    initial_cash: float = 100_000
    period: str = "1d"
    dividend_type: str = "front"
    indicators: list[IndicatorDef] = field(default_factory=list)
    warmup: int | None = None

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a plain dict."""
        return {
            "symbols": list(self.symbols),
            "start_date": self.start_date,
            "end_date": self.end_date,
            "initial_cash": self.initial_cash,
            "period": self.period,
            "dividend_type": self.dividend_type,
            "indicators": [
                {
                    "name": ind.name,
                    "params": dict(ind.params),
                    "outputs": list(ind.outputs),
                }
                for ind in self.indicators
            ],
            **({"warmup": self.warmup} if self.warmup is not None else {}),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> BacktestConfig:
        """Deserialize from a plain dict."""
        indicators: list[IndicatorDef] = []
        for ind_data in data.get("indicators", []):
            outputs = ind_data.get("outputs", ("value",))
            if isinstance(outputs, list):
                outputs = tuple(outputs)
            indicators.append(
                IndicatorDef(
                    name=ind_data["name"],
                    params=ind_data.get("params", {}),
                    outputs=outputs,
                )
            )
        return cls(
            symbols=data["symbols"],
            start_date=data["start_date"],
            end_date=data["end_date"],
            initial_cash=data.get("initial_cash", 100_000),
            period=data.get("period", "1d"),
            dividend_type=data.get("dividend_type", "front"),
            indicators=indicators,
            warmup=data.get("warmup"),
        )
