"""BacktestConfig with YAML serialization support."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from stablemoney.indicator_def import IndicatorDef
from stablemoney.market_sector import MarketSector, SectorFilter


@dataclass(frozen=True)
class BacktestConfig:
    """Backtest run configuration.

    Contains everything needed to start a backtest run: symbols or sector,
    date range, initial capital, indicators, and warmup period.

    Exactly one of ``symbols`` or ``sector`` must be provided.
    """

    symbols: list[str] = field(default_factory=list)
    start_date: str = ""
    end_date: str = ""
    initial_cash: float = 100_000
    period: str = "1d"
    dividend_type: str = "front"
    indicators: list[IndicatorDef] = field(default_factory=list)
    warmup: int | None = None
    sector: MarketSector | None = None
    sector_filter: SectorFilter | None = None

    def _serialize(self) -> dict[str, Any]:
        """Convert to a plain dict for YAML serialization."""
        result: dict[str, Any] = {
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
            **(
                {"warmup": self.warmup}
                if self.warmup is not None
                else {}
            ),
            **(
                {"sector": self.sector.value}
                if self.sector is not None
                else {}
            ),
            **(
                {
                    "sector_filter": {
                        "max_stocks": self.sector_filter.max_stocks,
                        "sort_by": self.sector_filter.sort_by,
                        "sort_ascending": self.sector_filter.sort_ascending,
                        "min_market_cap": self.sector_filter.min_market_cap,
                        "max_market_cap": self.sector_filter.max_market_cap,
                    }
                }
                if self.sector_filter is not None
                else {}
            ),
        }
        return result

    @classmethod
    def _deserialize(cls, data: dict[str, Any]) -> BacktestConfig:
        """Construct from a plain dict (YAML-loaded)."""
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

        sector: MarketSector | None = None
        if "sector" in data and data["sector"] is not None:
            sector = MarketSector(data["sector"])

        sector_filter: SectorFilter | None = None
        if "sector_filter" in data and data["sector_filter"] is not None:
            sf = data["sector_filter"]
            sector_filter = SectorFilter(
                max_stocks=sf.get("max_stocks"),
                sort_by=sf.get("sort_by"),
                sort_ascending=sf.get("sort_ascending", True),
                min_market_cap=sf.get("min_market_cap"),
                max_market_cap=sf.get("max_market_cap"),
            )

        return cls(
            symbols=data.get("symbols", []),
            start_date=data.get("start_date", ""),
            end_date=data.get("end_date", ""),
            initial_cash=data.get("initial_cash", 100_000),
            period=data.get("period", "1d"),
            dividend_type=data.get("dividend_type", "front"),
            indicators=indicators,
            warmup=data.get("warmup"),
            sector=sector,
            sector_filter=sector_filter,
        )

    @classmethod
    def from_yaml(cls, path: str | Path) -> BacktestConfig:
        """Load from a YAML file."""
        path = Path(path)
        with path.open(encoding="utf-8") as f:
            data: dict[str, Any] = yaml.safe_load(f)

        backtest_data = data.get("backtest", {})
        return cls._deserialize(backtest_data)

    def save(self, path: str | Path) -> None:
        """Save to a YAML file."""
        path = Path(path)
        data = {"backtest": self._serialize()}
        with path.open("w", encoding="utf-8") as f:
            yaml.dump(
                data,
                f,
                default_flow_style=False,
                allow_unicode=True,
                sort_keys=False,
            )
