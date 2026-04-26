"""Logging configuration for StableMoney backtests.

Usage in example scripts::

    import argparse
    from stablemoney.log import setup_logging

    parser = argparse.ArgumentParser()
    parser.add_argument("--log-level", default="ERROR",
                        choices=["DEBUG", "INFO", "WARNING", "ERROR"])
    args = parser.parse_args()
    setup_logging(args.log_level)
"""

from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path

_LOG_FORMAT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"
_LOG_DIR = Path("logs")


def setup_logging(
    level: str = "INFO",
    log_dir: str | Path = _LOG_DIR,
) -> None:
    """Configure logging with console (ERROR only) and file (all levels) output.

    Args:
        level: Minimum log level for file output. One of DEBUG, INFO, WARNING, ERROR.
        log_dir: Directory for log files. Created automatically if it doesn't exist.
    """
    log_path = Path(log_dir)
    log_path.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = log_path / f"backtest_{timestamp}.log"

    root_logger = logging.getLogger("stablemoney")
    root_logger.setLevel(getattr(logging, level.upper(), logging.INFO))
    root_logger.propagate = False

    # Avoid duplicate handlers on repeated calls
    if root_logger.handlers:
        return

    # Console handler: ERROR only
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.ERROR)
    console_handler.setFormatter(logging.Formatter(_LOG_FORMAT, _DATE_FORMAT))
    root_logger.addHandler(console_handler)

    # File handler: all levels >= specified level
    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setLevel(getattr(logging, level.upper(), logging.INFO))
    file_handler.setFormatter(logging.Formatter(_LOG_FORMAT, _DATE_FORMAT))
    root_logger.addHandler(file_handler)

    root_logger.info("日志系统已初始化, 级别=%s, 文件=%s", level.upper(), log_file)


def log_dataframe(
    logger: logging.Logger,
    title: str,
    df: object,
    level: int = logging.INFO,
) -> None:
    """Log a DataFrame summary or full content based on effective log level.

    DEBUG: full DataFrame via ``to_string()``.
    INFO: shape + ``head()`` (first 5 rows).
    """
    if not logger.isEnabledFor(level):
        return

    import pandas as pd

    if not isinstance(df, pd.DataFrame):
        logger.log(level, "%s: %s", title, df)
        return

    if logger.isEnabledFor(logging.DEBUG):
        logger.debug("%s (shape=%s):\n%s", title, df.shape, df.to_string())
    else:
        logger.log(
            level,
            "%s (shape=%s):\n%s",
            title,
            df.shape,
            df.head().to_string(),
        )
