"""Tests for log module."""

from __future__ import annotations

import logging
from pathlib import Path

import pandas as pd
import pytest
from stablemoney.log import dump_stock_csv, log_dataframe, setup_logging


@pytest.fixture(autouse=True)
def _reset_logging() -> None:
    """Reset stablemoney logger between tests."""
    logger = logging.getLogger("stablemoney")
    yield
    logger.handlers.clear()
    logger.setLevel(logging.WARNING)
    logger.propagate = True


class TestSetupLogging:
    def test_returns_session_dir(self, tmp_path: Path) -> None:
        session = setup_logging(log_dir=tmp_path)
        assert session.exists()
        assert session.parent == tmp_path
        assert session.name.startswith("backtest_")

    def test_creates_log_file(self, tmp_path: Path) -> None:
        session = setup_logging(log_dir=tmp_path)
        log_file = session / "backtest.log"
        assert log_file.exists()

    def test_propagate_disabled(self, tmp_path: Path) -> None:
        setup_logging(log_dir=tmp_path)
        logger = logging.getLogger("stablemoney")
        assert logger.propagate is False

    def test_console_handler_error_only(self, tmp_path: Path) -> None:
        setup_logging(log_dir=tmp_path)
        logger = logging.getLogger("stablemoney")
        console_handlers = [
            h for h in logger.handlers if isinstance(h, logging.StreamHandler)
            and not isinstance(h, logging.FileHandler)
        ]
        assert len(console_handlers) == 1
        assert console_handlers[0].level == logging.ERROR

    def test_file_handler_level(self, tmp_path: Path) -> None:
        setup_logging(level="DEBUG", log_dir=tmp_path)
        logger = logging.getLogger("stablemoney")
        file_handlers = [
            h for h in logger.handlers if isinstance(h, logging.FileHandler)
        ]
        assert len(file_handlers) == 1
        assert file_handlers[0].level == logging.DEBUG

    def test_no_duplicate_handlers(self, tmp_path: Path) -> None:
        setup_logging(log_dir=tmp_path)
        setup_logging(log_dir=tmp_path)
        logger = logging.getLogger("stablemoney")
        assert len(logger.handlers) == 2  # one console + one file


class TestDumpStockCsv:
    def test_writes_csv(self, tmp_path: Path) -> None:
        setup_logging(log_dir=tmp_path)
        df = pd.DataFrame({"symbol": ["600519.SH"], "close": [1800.0]})
        path = dump_stock_csv(df, "600519.SH", "test")
        assert path.exists()
        assert path.suffix == ".csv"

    def test_sanitizes_filename(self, tmp_path: Path) -> None:
        setup_logging(log_dir=tmp_path)
        df = pd.DataFrame({"close": [10.0]})
        path = dump_stock_csv(df, "600519.SH", "tag")
        assert "600519_SH" in path.name

    def test_sorts_by_symbol_and_date(self, tmp_path: Path) -> None:
        setup_logging(log_dir=tmp_path)
        df = pd.DataFrame({
            "symbol": ["B", "A", "B"],
            "date": ["2024-03-01", "2024-01-01", "2024-02-01"],
            "close": [3.0, 1.0, 2.0],
        })
        path = dump_stock_csv(df, "TEST", "sort")
        result = pd.read_csv(path)
        assert result["symbol"].tolist() == ["A", "B", "B"]


class TestLogDataframe:
    def test_logs_shape_and_head(self, tmp_path: Path) -> None:
        setup_logging(level="DEBUG", log_dir=tmp_path)
        logger = logging.getLogger("stablemoney.test")
        logger.setLevel(logging.DEBUG)
        df = pd.DataFrame({"a": range(10)})
        # Should not raise
        log_dataframe(logger, "test_df", df)

    def test_logs_non_dataframe(self, tmp_path: Path) -> None:
        setup_logging(level="DEBUG", log_dir=tmp_path)
        logger = logging.getLogger("stablemoney.test")
        logger.setLevel(logging.DEBUG)
        # Should not raise with non-DataFrame
        log_dataframe(logger, "test_str", "not a df")

    def test_skips_when_disabled(self, tmp_path: Path) -> None:
        setup_logging(level="ERROR", log_dir=tmp_path)
        logger = logging.getLogger("stablemoney.test")
        logger.setLevel(logging.ERROR)
        df = pd.DataFrame({"a": [1]})
        # Should not raise and should skip
        log_dataframe(logger, "test", df, level=logging.DEBUG)
