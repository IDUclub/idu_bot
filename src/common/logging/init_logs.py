import sys
from pathlib import Path
from typing import Any

from loguru import logger


def add_logger(target: Any):

    logger.add(
        target,
        level="INFO",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {name}:{function}:{line} | {message}",
    )


def init_logs(logs_path: Path):

    logger.remove()
    add_logger(sys.stdout)
    add_logger(logs_path)
    logger.info("Initialized logs")
