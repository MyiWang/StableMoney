"""Tests for the logging configuration module."""

from __future__ import annotations

import logging
from pathlib import Path

import pandas as pd
import pytest

from stablemoney.log import log_dataframe, setup_logging


@pytest.fixture(autouse=True)
def _reset_logging() -> None:
    """Remove stablemoney handlers between tests."""
    root = logging.getLogger("stablemoney")
    root.handlers.clear()
    root.setLevel(logging.WARNING)


class TestSetupLogging:
    def test_creates_log_dir(self, tmp_path: Path) -> None:
        log_dir = tmp_path / "logs"
        setup_logging(log_dir=log_dir)
        assert log_dir.exists()

    def test_creates_file_handler(self, tmp_path: Path) -> None:
        setup_logging(level="DEBUG", log_dir=tmp_path)
        root = logging.getLogger("stablemoney")
        file_handlers = [h for h in root.handlers if isinstance(h, logging.FileHandler)]
        assert len(file_handlers) == 1

    def test_creates_console_handler(self, tmp_path: Path) -> None:
        setup_logging(log_dir=tmp_path)
        root = logging.getLogger("stablemoney")
        console_handlers = [
            h for h in root.handlers
            if isinstance(h, logging.StreamHandler) and not isinstance(h, logging.FileHandler)
        ]
        assert len(console_handlers) == 1

    def test_console_handler_error_only(self, tmp_path: Path) -> None:
        setup_logging(log_dir=tmp_path)
        root = logging.getLogger("stablemoney")
        console_handlers = [
            h for h in root.handlers
            if isinstance(h, logging.StreamHandler) and not isinstance(h, logging.FileHandler)
        ]
        assert console_handlers[0].level == logging.ERROR

    def test_file_handler_level_info(self, tmp_path: Path) -> None:
        setup_logging(level="INFO", log_dir=tmp_path)
        root = logging.getLogger("stablemoney")
        file_handlers = [h for h in root.handlers if isinstance(h, logging.FileHandler)]
        assert file_handlers[0].level == logging.INFO

    def test_file_handler_level_debug(self, tmp_path: Path) -> None:
        setup_logging(level="DEBUG", log_dir=tmp_path)
        root = logging.getLogger("stablemoney")
        file_handlers = [h for h in root.handlers if isinstance(h, logging.FileHandler)]
        assert file_handlers[0].level == logging.DEBUG

    def test_no_duplicate_handlers(self, tmp_path: Path) -> None:
        setup_logging(log_dir=tmp_path)
        setup_logging(log_dir=tmp_path)
        root = logging.getLogger("stablemoney")
        assert len(root.handlers) == 2  # one console + one file

    def test_case_insensitive_level(self, tmp_path: Path) -> None:
        setup_logging(level="warning", log_dir=tmp_path)
        root = logging.getLogger("stablemoney")
        assert root.level == logging.WARNING

    def test_log_file_written(self, tmp_path: Path) -> None:
        setup_logging(level="INFO", log_dir=tmp_path)
        root = logging.getLogger("stablemoney")
        root.info("test message")
        file_handlers = [h for h in root.handlers if isinstance(h, logging.FileHandler)]
        file_handlers[0].flush()
        log_files = list(tmp_path.glob("backtest_*.log"))
        assert len(log_files) == 1
        content = log_files[0].read_text(encoding="utf-8")
        assert "test message" in content


class TestLogDataframe:
    def test_debug_level_full_output(self) -> None:
        test_logger = logging.getLogger("test.debug.df")
        test_logger.setLevel(logging.DEBUG)

        records: list[str] = []
        handler = logging.Handler()
        handler.emit = lambda record: records.append(record.getMessage())  # type: ignore[assignment]
        handler.setLevel(logging.DEBUG)
        test_logger.addHandler(handler)

        df = pd.DataFrame({"a": range(10), "b": range(10, 20)})
        log_dataframe(test_logger, "test df", df, level=logging.DEBUG)
        assert len(records) == 1
        assert "shape=(10, 2)" in records[0]
        # Full output should include last row
        assert "19" in records[0]

    def test_info_level_summary_output(self) -> None:
        test_logger = logging.getLogger("test.info.df")
        test_logger.setLevel(logging.INFO)

        records: list[str] = []
        handler = logging.Handler()
        handler.emit = lambda record: records.append(record.getMessage())  # type: ignore[assignment]
        handler.setLevel(logging.INFO)
        test_logger.addHandler(handler)

        df = pd.DataFrame({"a": range(100), "b": range(100, 200)})
        log_dataframe(test_logger, "test df", df, level=logging.INFO)
        assert len(records) == 1
        assert "shape=(100, 2)" in records[0]
        # Summary should only include head (first 5 rows), not row 99
        assert "199" not in records[0]

    def test_non_dataframe_passthrough(self) -> None:
        test_logger = logging.getLogger("test.passthrough")
        test_logger.setLevel(logging.INFO)

        records: list[str] = []
        handler = logging.Handler()
        handler.emit = lambda record: records.append(record.getMessage())  # type: ignore[assignment]
        handler.setLevel(logging.INFO)
        test_logger.addHandler(handler)

        log_dataframe(test_logger, "value", "some string", level=logging.INFO)
        assert len(records) == 1
        assert "some string" in records[0]

    def test_skips_when_disabled(self) -> None:
        test_logger = logging.getLogger("test.disabled")
        test_logger.setLevel(logging.WARNING)

        records: list[str] = []
        handler = logging.Handler()
        handler.emit = lambda record: records.append(record.getMessage())  # type: ignore[assignment]
        handler.setLevel(logging.DEBUG)
        test_logger.addHandler(handler)

        df = pd.DataFrame({"a": [1]})
        log_dataframe(test_logger, "test", df, level=logging.DEBUG)
        assert len(records) == 0
