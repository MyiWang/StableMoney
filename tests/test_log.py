"""Tests for the logging configuration module."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import pandas as pd
import pytest

from stablemoney.log import dump_stock_csv, log_dataframe, setup_logging

if TYPE_CHECKING:
    from pathlib import Path


@pytest.fixture(autouse=True)
def _reset_logging() -> None:
    """Remove stablemoney handlers between tests."""
    root = logging.getLogger("stablemoney")
    root.handlers.clear()
    root.setLevel(logging.WARNING)
    root.propagate = True


class TestSetupLogging:
    def test_returns_session_dir(self, tmp_path: Path) -> None:
        session_dir = setup_logging(log_dir=tmp_path)
        assert session_dir.exists()
        assert session_dir.name.startswith("backtest_")

    def test_creates_log_file_in_session_dir(self, tmp_path: Path) -> None:
        session_dir = setup_logging(level="INFO", log_dir=tmp_path)
        log_files = list(session_dir.glob("backtest.log"))
        assert len(log_files) == 1

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
            if isinstance(h, logging.StreamHandler)
            and not isinstance(h, logging.FileHandler)
        ]
        assert len(console_handlers) == 1

    def test_console_handler_error_only(self, tmp_path: Path) -> None:
        setup_logging(log_dir=tmp_path)
        root = logging.getLogger("stablemoney")
        console_handlers = [
            h for h in root.handlers
            if isinstance(h, logging.StreamHandler)
            and not isinstance(h, logging.FileHandler)
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
        session_dir = setup_logging(level="INFO", log_dir=tmp_path)
        root = logging.getLogger("stablemoney")
        root.info("test message")
        file_handlers = [h for h in root.handlers if isinstance(h, logging.FileHandler)]
        file_handlers[0].flush()
        log_file = session_dir / "backtest.log"
        content = log_file.read_text(encoding="utf-8")
        assert "test message" in content

    def test_propagate_disabled(self, tmp_path: Path) -> None:
        setup_logging(log_dir=tmp_path)
        root = logging.getLogger("stablemoney")
        assert root.propagate is False

    def test_info_not_propagated_to_root(self, tmp_path: Path) -> None:
        setup_logging(level="INFO", log_dir=tmp_path)

        root_records: list[str] = []
        root_handler = logging.Handler()
        root_handler.emit = lambda record: root_records.append(record.getMessage())  # type: ignore[method-assign]
        root_handler.setLevel(logging.NOTSET)
        logging.root.addHandler(root_handler)

        child = logging.getLogger("stablemoney.strategy_builder")
        child.info("should not reach root")

        assert len(root_records) == 0

        logging.root.removeHandler(root_handler)


class TestDumpStockCsv:
    def test_creates_csv_in_session_dir(self, tmp_path: Path) -> None:
        session_dir = setup_logging(log_dir=tmp_path)
        df = pd.DataFrame({"close": [10.0, 11.0]})
        path = dump_stock_csv(df, "600519.SH", "test")
        assert path.parent == session_dir
        assert path.exists()
        assert "600519_SH_test" in path.name

    def test_sorts_by_symbol_and_date(self, tmp_path: Path) -> None:
        setup_logging(log_dir=tmp_path)
        df = pd.DataFrame(
            {
                "symbol": ["B.SZ", "A.SH", "B.SZ", "A.SH"],
                "date": ["2024-01-02", "2024-01-01", "2024-01-01", "2024-01-02"],
                "close": [11.0, 10.0, 12.0, 13.0],
            }
        )
        path = dump_stock_csv(df, "test", "sorted")
        loaded = pd.read_csv(path)
        assert loaded["symbol"].iloc[0] == "A.SH"
        assert loaded["date"].iloc[0] == "2024-01-01"

    def test_no_sort_columns(self, tmp_path: Path) -> None:
        setup_logging(log_dir=tmp_path)
        df = pd.DataFrame({"close": [10.0, 11.0]})
        path = dump_stock_csv(df, "test", "no_sort")
        assert path.exists()
        loaded = pd.read_csv(path)
        assert len(loaded) == 2

    def test_fallback_dir_without_setup(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        import stablemoney.log as log_mod

        monkeypatch.setattr(log_mod, "_session_dir", tmp_path / "fallback")
        df = pd.DataFrame({"close": [10.0]})
        path = dump_stock_csv(df, "test", "fallback")
        assert path.parent == tmp_path / "fallback"
        assert path.exists()


class TestLogDataframe:
    def test_debug_level_full_output(self) -> None:
        test_logger = logging.getLogger("test.debug.df")
        test_logger.setLevel(logging.DEBUG)

        records: list[str] = []
        handler = logging.Handler()
        handler.emit = lambda record: records.append(record.getMessage())  # type: ignore[method-assign]
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
        handler.emit = lambda record: records.append(record.getMessage())  # type: ignore[method-assign]
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
        handler.emit = lambda record: records.append(record.getMessage())  # type: ignore[method-assign]
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
        handler.emit = lambda record: records.append(record.getMessage())  # type: ignore[method-assign]
        handler.setLevel(logging.DEBUG)
        test_logger.addHandler(handler)

        df = pd.DataFrame({"a": [1]})
        log_dataframe(test_logger, "test", df, level=logging.DEBUG)
        assert len(records) == 0
