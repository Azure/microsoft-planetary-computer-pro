"""
Interactive CLI for discovering MPC Pro collections and registering them
as cloud data stores on ArcGIS Enterprise.

Uses the ``rich`` library for formatted terminal output and prompts.
"""

from __future__ import annotations

import logging
import sys

from rich.console import Console
from rich.prompt import Confirm, Prompt
from rich.table import Table

from .config import StorageCredentialConfig
from .discovery import CollectionDiscovery, CollectionInfo
from .registration import CloudStoreRegistrar, RegistrationResult
from .service_principal import ServicePrincipalManager, ServicePrincipalInfo

logger = logging.getLogger(__name__)
console = Console()


def print_collections_table(collections: list[CollectionInfo]) -> None:
    """Render a numbered table of discovered collections."""
    table = Table(
        title="MPC Pro GeoCatalog Collections",
        show_lines=True,
    )
    table.add_column("#", style="bold cyan", width=4)
    table.add_column("Collection ID", style="bold")
    table.add_column("Title")
    table.add_column("Storage Account", style="dim")
    table.add_column("Container", style="dim")
    table.add_column("Description", max_width=50)

    for idx, coll in enumerate(collections, 1):
        storage = coll.storage_account or "[red]unknown[/red]"
        container = coll.container or "[red]unknown[/red]"
        table.add_row(
            str(idx),
            coll.collection_id,
            coll.display_name,
            storage,
            container,
            coll.description[:80] if coll.description else "",
        )

    console.print(table)


def prompt_collection_selection(
    collections: list[CollectionInfo],
) -> list[CollectionInfo]:
    """Ask the user which collections to register.

    Returns the selected subset (or all).
    """
    console.print()
    console.print("[bold]Which collections would you like to register as cloud data stores?[/bold]")
    console.print(
        "  Enter [cyan]all[/cyan] to register every collection,\n"
        "  a comma-separated list of numbers (e.g. [cyan]1,3,5[/cyan]),\n"
        "  a range (e.g. [cyan]1-4[/cyan]),\n"
        "  or [cyan]none[/cyan] to cancel."
    )

    choice = Prompt.ask("Selection", default="all")

    if choice.strip().lower() == "none":
        return []

    if choice.strip().lower() == "all":
        return list(collections)

    # Parse comma-separated numbers and ranges
    selected_indices: set[int] = set()
    for part in choice.split(","):
        part = part.strip()
        if "-" in part:
            try:
                start, end = part.split("-", 1)
                for i in range(int(start), int(end) + 1):
                    selected_indices.add(i)
            except ValueError:
                console.print(f"[red]Invalid range: '{part}'[/red]")
                continue
        else:
            try:
                selected_indices.add(int(part))
            except ValueError:
                console.print(f"[red]Invalid number: '{part}'[/red]")
                continue

    # Filter valid indices
    selected: list[CollectionInfo] = []
    for idx in sorted(selected_indices):
        if 1 <= idx <= len(collections):
            selected.append(collections[idx - 1])
        else:
            console.print(f"[yellow]Skipping #{idx} — out of range[/yellow]")

    return selected


def print_selection_summary(
    selected: list[CollectionInfo],
    existing_stores: list[str],
) -> None:
    """Show what will be registered and flag any that already exist."""
    console.print()
    console.print("[bold]Registration plan:[/bold]")

    table = Table(show_lines=False)
    table.add_column("Collection", style="bold")
    table.add_column("Store Name")
    table.add_column("Storage Account")
    table.add_column("Container")
    table.add_column("Status")

    for coll in selected:
        name = coll.collection_id.replace("-", "_")
        if name in existing_stores:
            status = "[yellow]already registered[/yellow]"
        elif not coll.storage_account:
            status = "[red]missing storage info[/red]"
        else:
            status = "[green]will register[/green]"

        table.add_row(
            coll.collection_id,
            name,
            coll.storage_account or "?",
            coll.container or "?",
            status,
        )

    console.print(table)


def print_results(results: list[RegistrationResult]) -> None:
    """Print the outcome of the registration batch."""
    console.print()
    console.print("[bold]Results:[/bold]")

    table = Table(show_lines=False)
    table.add_column("Store Name", style="bold")
    table.add_column("Collection")
    table.add_column("Outcome")
    table.add_column("Validated")
    table.add_column("Message")

    for r in results:
        if r.success and r.already_existed:
            outcome = "[yellow]skipped (exists)[/yellow]"
        elif r.success:
            outcome = "[green]registered[/green]"
        else:
            outcome = "[red]failed[/red]"

        if r.validated is None:
            val_col = "[dim]—[/dim]"
        elif r.validated:
            val_col = "[green]passed[/green]"
        else:
            val_col = f"[red]failed[/red]"

        msg = r.message
        if r.validation_message and not r.validated and r.validated is not None:
            msg += f" | validation: {r.validation_message}"

        table.add_row(
            r.store_name or "—",
            r.collection_id,
            outcome,
            val_col,
            msg,
        )

    console.print(table)

    succeeded = sum(1 for r in results if r.success and not r.already_existed)
    skipped = sum(1 for r in results if r.already_existed)
    failed = sum(1 for r in results if not r.success)
    validated = sum(1 for r in results if r.validated is True)
    val_failed = sum(1 for r in results if r.validated is False)
    console.print()
    console.print(
        f"[bold]Summary:[/bold] "
        f"[green]{succeeded} registered[/green], "
        f"[yellow]{skipped} skipped[/yellow], "
        f"[red]{failed} failed[/red]. "
        f"Validation: [green]{validated} passed[/green], "
        f"[red]{val_failed} failed[/red]."
    )


# ---------------------------------------------------------------------------
# Service Principal
# ---------------------------------------------------------------------------

def run_service_principal_step(
    storage_config: StorageCredentialConfig,
    geocatalog_name: str,
    dry_run: bool = False,
) -> StorageCredentialConfig:
    """Handle service principal creation or retrieval.

    If ``create_service_principal`` is True and no client_id is pre-configured,
    creates a new SP and assigns GeoCatalog Reader on the GeoCatalog resource.

    Returns an updated StorageCredentialConfig with the SP credentials populated.
    """
    cred_type = storage_config.credential_type.lower().replace("-", "_")
    if cred_type != "service_principal":
        # Nothing to do for non-SP credential types
        return storage_config

    # If an existing SP was provided, use it directly
    if storage_config.client_id and storage_config.client_secret:
        console.print()
        console.print(
            f"[bold]Using existing service principal:[/bold] "
            f"client_id={storage_config.client_id[:8]}…"
        )
        # Still offer to assign roles
        if geocatalog_name and Confirm.ask(
            "Assign GeoCatalog Reader to this SP on the GeoCatalog?",
            default=True,
        ):
            if not dry_run:
                _assign_geocatalog_role(
                    storage_config.client_id,
                    geocatalog_name,
                    storage_config.subscription_id,
                )
            else:
                console.print(
                    f"[yellow]  [DRY RUN] Would assign GeoCatalog Reader on: {geocatalog_name}[/yellow]"
                )
        return storage_config

    if not storage_config.create_service_principal:
        console.print()
        console.print(
            "[yellow]Warning:[/yellow] credential_type is 'service_principal' "
            "but no client_id/client_secret provided and create_service_principal=false. "
            "Cloud store registration may fail."
        )
        return storage_config

    # --- Create a new service principal ---
    console.print()
    console.print("[bold]Service Principal Setup[/bold]")
    console.print(
        "A new Entra ID app registration will be created and granted "
        "GeoCatalog Reader on the GeoCatalog resource."
    )

    sp_name = storage_config.sp_display_name
    console.print(f"  Display name: [cyan]{sp_name}[/cyan]")
    console.print(
        f"  GeoCatalog: [cyan]{geocatalog_name}[/cyan]"
    )

    if dry_run:
        console.print("[yellow]  [DRY RUN] Would create service principal and assign roles.[/yellow]")
        return storage_config

    if not Confirm.ask("Create a new service principal?", default=True):
        console.print("[yellow]Skipping service principal creation.[/yellow]")
        return storage_config

    with console.status("[bold]Creating service principal…[/bold]"):
        sp_mgr = ServicePrincipalManager(
            subscription_id=storage_config.subscription_id or None
        )
        sp_info = sp_mgr.create_service_principal(
            display_name=sp_name,
        )

    console.print()
    console.print("[green]Service principal created successfully.[/green]")
    console.print(f"  Tenant ID:     [cyan]{sp_info.tenant_id}[/cyan]")
    console.print(f"  Client ID:     [cyan]{sp_info.client_id}[/cyan]")
    console.print(f"  Client Secret: [cyan]{sp_info.client_secret[:4]}{'*' * 20}[/cyan]")
    console.print()
    console.print(
        "[bold yellow]Save these credentials — the client secret "
        "cannot be retrieved later.[/bold yellow]"
    )

    # Assign GeoCatalog Reader on the GeoCatalog resource
    _assign_geocatalog_role(
        sp_info.client_id,
        geocatalog_name,
        storage_config.subscription_id,
    )

    # Return an updated config with the new credentials
    from dataclasses import replace
    return replace(
        storage_config,
        tenant_id=sp_info.tenant_id,
        client_id=sp_info.client_id,
        client_secret=sp_info.client_secret,
    )


def _assign_geocatalog_role(
    client_id: str,
    geocatalog_name: str,
    subscription_id: str = "",
) -> None:
    """Assign GeoCatalog Reader on the GeoCatalog resource."""
    if not geocatalog_name:
        return

    console.print()
    with console.status("[bold]Assigning GeoCatalog Reader role…[/bold]"):
        sp_mgr = ServicePrincipalManager(
            subscription_id=subscription_id or None
        )
        ok = sp_mgr.assign_geocatalog_reader_role(
            principal_id=client_id,
            geocatalog_name=geocatalog_name,
        )

    if ok:
        console.print(f"  [green]✓[/green] GeoCatalog Reader → {geocatalog_name}")
    else:
        console.print(f"  [red]✗[/red] Failed to assign GeoCatalog Reader on {geocatalog_name}")


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------

def _extract_geocatalog_name(registrar: CloudStoreRegistrar) -> str:
    """Extract the GeoCatalog resource name from the registrar's endpoint.

    The endpoint URL is like
    ``https://skywatch-geocatalog.f5aza3htf5h8dnft.northcentralus.geocatalog.spatio.azure.com/``
    and the resource name is the first label (``skywatch-geocatalog``).
    """
    from urllib.parse import urlparse
    endpoint = registrar._geocatalog_endpoint
    if not endpoint:
        return ""
    hostname = urlparse(endpoint).hostname or ""
    return hostname.split(".")[0] if hostname else ""


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------

def run_interactive(
    discovery: CollectionDiscovery,
    registrar: CloudStoreRegistrar,
    storage_config: StorageCredentialConfig,
    dry_run: bool = False,
) -> int:
    """Run the full interactive workflow.

    Returns exit code: 0 = success, 1 = error, 2 = user cancelled.
    """
    # Step 1 — Discover collections
    console.print()
    with console.status("[bold]Discovering collections from MPC Pro…[/bold]"):
        collections = discovery.list_collections()

    if not collections:
        console.print("[yellow]No collections found in the GeoCatalog.[/yellow]")
        return 1

    print_collections_table(collections)

    # Step 2 — User selects which to register
    selected = prompt_collection_selection(collections)
    if not selected:
        console.print("[yellow]No collections selected. Exiting.[/yellow]")
        return 2

    # Step 3 — Service principal setup (create or validate existing)
    geocatalog_name = _extract_geocatalog_name(registrar)
    updated_creds = run_service_principal_step(
        storage_config, geocatalog_name, dry_run=dry_run
    )
    registrar.update_storage_config(updated_creds)

    # Step 4 — Connect to ArcGIS Enterprise
    console.print()
    with console.status("[bold]Connecting to ArcGIS Enterprise…[/bold]"):
        registrar.connect()

    # Step 5 — Show plan
    existing = registrar.list_existing_cloud_stores()
    print_selection_summary(selected, existing)

    if dry_run:
        console.print()
        console.print("[bold yellow]—— DRY RUN — no changes will be made ——[/bold yellow]")
        results = registrar.register_many(selected, dry_run=True)
        print_results(results)
        return 0

    # Step 6 — Confirm
    console.print()
    if not Confirm.ask("Proceed with registration?", default=True):
        console.print("[yellow]Cancelled.[/yellow]")
        return 2

    # Step 7 — Register and validate
    console.print()
    results = registrar.register_many(selected, dry_run=False)
    print_results(results)

    return 0 if all(r.success for r in results) else 1
