"""Extended StrategyConfig and BacktestConfig with serialization support."""

from __future__ import annotations

from dataclasses import dataclass, field, fields
from typing import Any

from pybroker.config import StrategyConfig as PyBrokerStrategyConfig

from stablemoney.indicator_def import IndicatorDef


@dataclass(frozen=True)
class StrategyConfig(PyBrokerStrategyConfig):
    """Extended PyBroker StrategyConfig with custom params.

    Custom parameters are accessible in the ExecuteCallback via
    ``ctx.config.params`` and can be used for risk control, position
    sizing, or any configurable logic.
    """

    params: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a plain dict."""
        result: dict[str, Any] = {}
        for f in fields(self):
            value = getattr(self, f.name)
            if f.name == "fee_mode" and value is not None:
                result[f.name] = str(value)
            else:
                result[f.name] = value
        return result

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> StrategyConfig:
        """Deserialize from a plain dict.

        Unknown keys are silently ignored so that JSON payloads from
        future frontends don't break deserialization.
        """
        valid_names = {f.name for f in fields(cls)}
        filtered = {k: v for k, v in data.items() if k in valid_names}
        return cls(**filtered)


@dataclass(frozen=True)
class BacktestConfig:
    """Backtest run configuration.

    Contains everything needed to start a backtest run: symbols,
    date range, period, dividend type, and indicator definitions.
    """

    symbols: list[str]
    start_date: str
    end_date: str
    period: str = "1d"
    dividend_type: str = "front"
    indicators: list[IndicatorDef] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a plain dict."""
        return {
            "symbols": list(self.symbols),
            "start_date": self.start_date,
            "end_date": self.end_date,
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
            period=data.get("period", "1d"),
            dividend_type=data.get("dividend_type", "front"),
            indicators=indicators,
        )
