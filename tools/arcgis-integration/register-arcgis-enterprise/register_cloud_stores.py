#!/usr/bin/env python3
"""
Register MPC Pro GeoCatalog collections as cloud data stores on ArcGIS Enterprise.

This script discovers STAC collections from a Planetary Computer Pro GeoCatalog
instance, prompts you to select which ones to register, and then registers each
selected collection's backing Azure Blob Storage container as a cloud data store
on your ArcGIS Enterprise Image Server (or Hosting Server).

Usage:
    # Using a .env file (auto-detected if present in the same directory)
    python register_cloud_stores.py

    # Using a YAML config file
    python register_cloud_stores.py --config config.yaml

    # Using an explicit .env file
    python register_cloud_stores.py --env /path/to/.env

    # Non-interactive (register all collections)
    python register_cloud_stores.py --all

    # Dry run (show what would be registered without making changes)
    python register_cloud_stores.py --dry-run
"""

from __future__ import annotations

import argparse
import logging
import sys

from rich.console import Console

from src.config import load_config
from src.discovery import CollectionDiscovery
from src.registration import CloudStoreRegistrar
from src.cli import (
    run_interactive,
    run_service_principal_step,
    print_collections_table,
    print_results,
)

console = Console()


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Register MPC Pro collections as ArcGIS Enterprise cloud data stores.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--config", "-c",
        help="Path to YAML configuration file.",
    )
    parser.add_argument(
        "--env", "-e",
        help="Path to .env file (default: auto-detect .env in script directory).",
    )
    parser.add_argument(
        "--all", "-a",
        action="store_true",
        dest="register_all",
        help="Register all collections without prompting.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be registered without making changes.",
    )
    parser.add_argument(
        "--list-only",
        action="store_true",
        help="Only list collections — do not register anything.",
    )
    parser.add_argument(
        "--skip-service-principal",
        action="store_true",
        help="Skip automatic service principal creation (use existing creds from config).",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable debug logging.",
    )

    args = parser.parse_args()

    # Logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    )
    # Quiet noisy Azure SDK loggers unless --verbose
    if not args.verbose:
        for azure_logger in ("azure", "urllib3", "msal"):
            logging.getLogger(azure_logger).setLevel(logging.WARNING)

    try:
        # Load configuration
        cfg = load_config(config_path=args.config, env_path=args.env)

        if not cfg.geocatalog.endpoint:
            console.print(
                "[red]Error:[/red] GeoCatalog endpoint not configured. "
                "Set GEOCATALOG_ENDPOINT in your .env or config file."
            )
            return 1

        if not cfg.arcgis.portal_url:
            console.print(
                "[red]Error:[/red] ArcGIS portal URL not configured. "
                "Set ARCGIS_PORTAL_URL in your .env or config file."
            )
            return 1

        # Create components
        discovery = CollectionDiscovery(cfg.geocatalog.endpoint)
        storage_config = cfg.storage_credentials

        # Override SP creation if --skip-service-principal
        if args.skip_service_principal:
            from dataclasses import replace
            storage_config = replace(storage_config, create_service_principal=False)

        registrar = CloudStoreRegistrar(cfg.arcgis, storage_config, geocatalog_endpoint=cfg.geocatalog.endpoint)

        # List-only mode
        if args.list_only:
            with console.status("[bold]Discovering collections…[/bold]"):
                collections = discovery.list_collections()
            if not collections:
                console.print("[yellow]No collections found.[/yellow]")
                return 1
            print_collections_table(collections)
            return 0

        # Non-interactive: register all
        if args.register_all:
            with console.status("[bold]Discovering collections…[/bold]"):
                collections = discovery.list_collections()
            if not collections:
                console.print("[yellow]No collections found.[/yellow]")
                return 1

            print_collections_table(collections)
            console.print()

            # Service principal step (non-interactive: auto-create or use existing)
            from urllib.parse import urlparse
            hostname = urlparse(cfg.geocatalog.endpoint).hostname or ""
            geocatalog_name = hostname.split(".")[0] if hostname else ""
            updated_creds = run_service_principal_step(
                storage_config, geocatalog_name, dry_run=args.dry_run
            )
            registrar.update_storage_config(updated_creds)

            with console.status("[bold]Connecting to ArcGIS Enterprise…[/bold]"):
                registrar.connect()

            results = registrar.register_many(
                collections, dry_run=args.dry_run
            )
            print_results(results)
            return 0 if all(r.success for r in results) else 1

        # Interactive mode (default)
        return run_interactive(
            discovery=discovery,
            registrar=registrar,
            storage_config=storage_config,
            dry_run=args.dry_run,
        )

    except KeyboardInterrupt:
        console.print("\n[yellow]Interrupted.[/yellow]")
        return 130
    except Exception as exc:
        console.print(f"[red]Error:[/red] {exc}")
        if args.verbose:
            console.print_exception()
        return 1


if __name__ == "__main__":
    sys.exit(main())
