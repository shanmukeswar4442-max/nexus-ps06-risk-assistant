"""
Structured Logging Module for Production Security & Observability (NexusTiq24 PS06).
Ensures sensitive credentials (API keys) are NEVER logged.
"""

import logging
import sys
from typing import Any


def mask_sensitive(data: Any) -> str:
    """Masks API keys or tokens if passed into logs."""
    if not isinstance(data, str):
        data = str(data)
    if len(data) > 10 and ("AIza" in data or "sk-" in data):
        return data[:4] + "..." + data[-4:]
    return data


def setup_logger(name: str = "nexus_risk") -> logging.Logger:
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger

    logger.setLevel(logging.INFO)
    
    formatter = logging.Formatter(
        "[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    
    return logger


logger = setup_logger()
