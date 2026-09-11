"""
geoai.shared.logging

Logging configuration for GeoAI SDK.
"""

import logging
import os


def setup_logging(level=None):
    """
    Setup logging for GeoAI SDK.

    Reads GEOAI_LOG_LEVEL environment variable (default: INFO).
    Valid values: DEBUG, INFO, WARNING, ERROR, CRITICAL

    :param level: Logging level (overrides environment variable if provided)
    """
    if level is None:
        # Read from environment variable, default to INFO
        level_str = os.getenv("GEOAI_LOG_LEVEL", "INFO").upper()
        level = getattr(logging, level_str, logging.INFO)

    # Configure root geoai logger
    geoai_logger = logging.getLogger("geoai")
    geoai_logger.setLevel(level)

    # Add console handler if not already present
    if not geoai_logger.handlers:
        handler = logging.StreamHandler()
        handler.setLevel(level)
        formatter = logging.Formatter("%(levelname)s: %(message)s")
        handler.setFormatter(formatter)
        geoai_logger.addHandler(handler)

    # Suppress noisy third-party loggers
    logging.getLogger("azure").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)


def get_logger(name: str):
    """
    Get logger for a module.

    :param name: Module name
    :return: Logger instance
    """
    return logging.getLogger(f"geoai.{name}")
