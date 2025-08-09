import logging
import os
import sys
from enum import Enum
from typing import Any, Dict, Optional, Union

from loguru import logger


class LoggingFormat(str, Enum):
    CONSOLE = "CONSOLE"
    JSON = "JSON"


def json_format(record: Dict[str, Any]) -> str:
    return record["message"]


def analytics_filter(record: Dict[str, Any]) -> bool:
    return record.get("extra", {}).get("analytics", False)


def inv_analytics_filter(record: Dict[str, Any]) -> bool:
    return not record.get("extra", {}).get("analytics", False)


def setup_logger(level: str = "INFO", fmt: LoggingFormat = LoggingFormat.CONSOLE, log_folder: Optional[str] = None):
    log_level: Union[int, str] = logging.getLevelName(level.upper())
    if not isinstance(log_level, int):
        log_level = logging.INFO

    if fmt == LoggingFormat.JSON and os.getenv("LOG_SANE", "0").lower() == "0":  # better debugging github_app
        logger.remove(None)
        logger.add(
            sys.stdout,
            level=log_level,
            format="{message}",
            colorize=False,
            serialize=True,
            filter=lambda record: not record.get("extra", {}).get("analytics", False),
        )
    elif fmt == LoggingFormat.CONSOLE:  # does not print the 'extra' fields
        logger.remove(None)
        logger.add(sys.stdout, level=log_level, colorize=True, filter=lambda record: not record.get("extra", {}).get("analytics", False))

    if log_folder:
        pid = os.getpid()
        log_file = os.path.join(log_folder, f"app.{pid}.log")
        logger.add(
            log_file,
            level=log_level,
            format="{message}",
            colorize=False,
            serialize=True,
            filter=lambda record: record.get("extra", {}).get("analytics", False),
        )

    return logger


def get_logger(*_args: Any, **_kwargs: Any):
    """Get logger instance (compatibility function)"""
    return logger
