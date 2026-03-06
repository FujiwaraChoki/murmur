"""Logging configuration for Murmur."""

from __future__ import annotations

import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

LOG_DIR = Path.home() / ".config" / "murmur"
LOG_FILE = LOG_DIR / "murmur.log"
MAX_LOG_SIZE = 5 * 1024 * 1024  # 5 MB
BACKUP_COUNT = 3


def setup_logging(level: int = logging.DEBUG) -> None:
    """Configure logging to write to both file and stderr.

    Log file is stored at ~/.config/murmur/murmur.log with rotation.

    Args:
        level: Logging level for the file handler. Console stays at INFO.
    """
    LOG_DIR.mkdir(parents=True, exist_ok=True)

    root = logging.getLogger("murmur")
    root.setLevel(logging.DEBUG)

    # Avoid adding duplicate handlers if called more than once
    if root.handlers:
        return

    formatter = logging.Formatter(
        "%(asctime)s [%(levelname)-8s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # File handler with rotation
    file_handler = RotatingFileHandler(
        LOG_FILE, maxBytes=MAX_LOG_SIZE, backupCount=BACKUP_COUNT
    )
    file_handler.setLevel(level)
    file_handler.setFormatter(formatter)
    root.addHandler(file_handler)

    # Console handler (less verbose)
    console_handler = logging.StreamHandler(sys.stderr)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(
        logging.Formatter("%(asctime)s %(levelname)s: %(message)s", datefmt="%H:%M:%S")
    )
    root.addHandler(console_handler)
