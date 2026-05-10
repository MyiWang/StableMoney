"""Tests for metrics_i18n module."""

from __future__ import annotations

import pandas as pd
import pytest

from stablemoney.metrics_i18n import METRIC_NAMES_CN, translate_metrics


@pytest.fixture
def sample_metrics_df() -> pd.DataFrame:
    """Build a small metrics DataFrame like PyBroker's TestResult.metrics_df."""
    return pd.DataFrame(
        {
            "name": ["trade_count", "win_rate", "sharpe", "unknown_metric"],
            "value": [272, 30.51, 0.02396, 42],
        }
    )


class TestMetricNamesCn:
    def test_all_keys_are_lowercase_snake(self) -> None:
        for key in METRIC_NAMES_CN:
            assert key == key.lower()
            assert " " not in key

    def test_all_values_are_chinese(self) -> None:
        for key, val in METRIC_NAMES_CN.items():
            assert val, f"Empty Chinese name for {key}"

    def test_covers_common_metrics(self) -> None:
        expected = [
            "trade_count",
            "total_return_pct",
            "win_rate",
            "max_drawdown",
            "sharpe",
            "profit_factor",
        ]
        for m in expected:
            assert m in METRIC_NAMES_CN


class TestTranslateMetrics:
    def test_translates_known_names(
        self, sample_metrics_df: pd.DataFrame
    ) -> None:
        result = translate_metrics(sample_metrics_df)
        assert result["name"].iloc[0] == "总交易次数"
        assert result["name"].iloc[1] == "胜率(%)"
        assert result["name"].iloc[2] == "夏普比率"

    def test_preserves_unknown_names(
        self, sample_metrics_df: pd.DataFrame
    ) -> None:
        result = translate_metrics(sample_metrics_df)
        assert result["name"].iloc[3] == "unknown_metric"

    def test_does_not_mutate_original(
        self, sample_metrics_df: pd.DataFrame
    ) -> None:
        original_name = sample_metrics_df["name"].iloc[0]
        translate_metrics(sample_metrics_df)
        assert sample_metrics_df["name"].iloc[0] == original_name

    def test_preserves_values(
        self, sample_metrics_df: pd.DataFrame
    ) -> None:
        result = translate_metrics(sample_metrics_df)
        pd.testing.assert_series_equal(result["value"], sample_metrics_df["value"])

    def test_empty_dataframe(self) -> None:
        df = pd.DataFrame(columns=["name", "value"])
        result = translate_metrics(df)
        assert len(result) == 0

    def test_no_name_column(self) -> None:
        df = pd.DataFrame({"value": [1, 2, 3]})
        result = translate_metrics(df)
        assert list(result.columns) == ["value"]
