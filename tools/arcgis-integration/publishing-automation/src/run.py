#!/usr/bin/env python3
"""
CLI entry point for the ArcGIS Publishing Automation pipeline.

Usage:
    python run.py --config path/to/config.yaml [--dry-run] [--verbose]

Exit codes:
    0 - Success (items were added or collection is up to date)
    1 - Error occurred
    2 - No new items found (success, but nothing to do)
"""

import argparse
import logging
import sys

from .config import ConfigurationError, load_config
from .pipeline import run as run_pipeline


def setup_logging(level: str = "INFO") -> None:
    """Configure logging for the pipeline."""
    numeric_level = getattr(logging, level.upper(), logging.INFO)
    logging.basicConfig(
        level=numeric_level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def main(args: list[str] | None = None) -> int:
    """
    Main entry point for the CLI.

    Args:
        args: Command-line arguments. Defaults to sys.argv[1:].

    Returns:
        Exit code (0=success, 1=error, 2=no new items).
    """
    parser = argparse.ArgumentParser(
        description="ArcGIS Publishing Automation — Discover new imagery from "
        "MPC Pro GeoCatalog and publish to ArcGIS Enterprise Image Server.",
        prog="publishing-automation",
    )
    parser.add_argument(
        "--config", "-c",
        required=True,
        help="Path to the YAML configuration file.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Query STAC and report what would be added without modifying anything.",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose (DEBUG) logging.",
    )

    parsed = parser.parse_args(args)

    # Setup logging
    log_level = "DEBUG" if parsed.verbose else "INFO"

    try:
        config = load_config(parsed.config)
    except (ConfigurationError, FileNotFoundError) as e:
        # Set up minimal logging to report config errors
        setup_logging(log_level)
        logging.error("Configuration error: %s", e)
        return 1

    # Use the log level from config unless --verbose overrides it
    if not parsed.verbose:
        log_level = config.deployment.log_level
    setup_logging(log_level)

    logger = logging.getLogger(__name__)
    logger.info("Starting ArcGIS Publishing Automation pipeline")
    if parsed.dry_run:
        logger.info("DRY RUN mode enabled — no changes will be made")

    # Run the pipeline
    try:
        result = run_pipeline(config, dry_run=parsed.dry_run)
    except Exception as e:
        logger.exception("Unhandled error during pipeline execution: %s", e)
        return 1

    if not result.success:
        logger.error("Pipeline failed: %s", result.error)
        return 1

    if result.items_new == 0:
        logger.info("No new items to process. Collection is up to date.")
        return 2

    logger.info("Pipeline completed successfully. %d items added.", result.items_added)
    return 0


if __name__ == "__main__":
    sys.exit(main())
