"""
Create or retrieve an Entra ID (Azure AD) service principal for ArcGIS Server
access to MPC Pro GeoCatalog-managed data.

This module can either:
  - Create a new app registration + service principal and assign it the
    GeoCatalog Reader role on the MPC Pro GeoCatalog resource, **or**
  - Accept an existing service principal's client_id / client_secret.

Uses the Azure CLI (``az``) under the hood — the user must be logged in
with ``az login`` with permissions to create app registrations and
role assignments in their tenant.
"""

from __future__ import annotations

import json
import logging
import subprocess
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger(__name__)

# Azure built-in role: GeoCatalog Reader
GEOCATALOG_READER_ROLE = "b7b8f583-43d0-40ae-b147-6b46f53661c1"


@dataclass
class ServicePrincipalInfo:
    """Credentials for a service principal."""
    tenant_id: str
    client_id: str
    client_secret: str
    display_name: str
    object_id: str = ""
    created_new: bool = False


class ServicePrincipalManager:
    """Create / manage Entra ID service principals via the Azure CLI."""

    def __init__(self, subscription_id: Optional[str] = None):
        self._subscription_id = subscription_id
        self._verify_az_cli()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def create_service_principal(
        self,
        display_name: str = "ArcGIS-Server-GeocatalogReader",
        secret_years: int = 2,
    ) -> ServicePrincipalInfo:
        """Create a new Entra ID app registration with a client secret.

        Parameters
        ----------
        display_name:
            Display name for the app registration.
        secret_years:
            Validity period for the generated client secret.

        Returns
        -------
        ServicePrincipalInfo with the new credentials.
        """
        logger.info(
            "Creating Entra ID app registration '%s' …", display_name
        )

        result = self._az(
            "ad", "app", "create",
            "--display-name", display_name,
            "--sign-in-audience", "AzureADMyOrg",
        )
        app_id = result["appId"]
        logger.info("App registration created: appId=%s", app_id)

        # Create the service principal for the app
        logger.info("Creating service principal …")
        sp_result = self._az(
            "ad", "sp", "create",
            "--id", app_id,
        )
        object_id = sp_result.get("id", sp_result.get("objectId", ""))
        logger.info("Service principal created: objectId=%s", object_id)

        # Create a client secret
        logger.info("Generating client secret (valid %d years) …", secret_years)
        cred_result = self._az(
            "ad", "app", "credential", "reset",
            "--id", app_id,
            "--append",
            "--years", str(secret_years),
            "--query", "{password: password}",
        )
        client_secret = cred_result.get("password", "")

        # Get tenant ID
        tenant_id = self._get_tenant_id()

        return ServicePrincipalInfo(
            tenant_id=tenant_id,
            client_id=app_id,
            client_secret=client_secret,
            display_name=display_name,
            object_id=object_id,
            created_new=True,
        )

    def assign_geocatalog_reader_role(
        self,
        principal_id: str,
        geocatalog_name: str,
        role_id: str = GEOCATALOG_READER_ROLE,
    ) -> bool:
        """Assign GeoCatalog Reader on a GeoCatalog resource.

        Searches across all accessible subscriptions for the
        ``Microsoft.Orbital/geoCatalogs`` resource with the given name
        and assigns the role.

        Parameters
        ----------
        principal_id:
            The service principal's appId (used as --assignee).
        geocatalog_name:
            The name of the GeoCatalog resource (e.g. ``skywatch-geocatalog``).
        role_id:
            The role definition GUID. Defaults to GeoCatalog Reader.

        Returns True if the assignment succeeded or already exists.
        """
        scope = self._get_geocatalog_scope(geocatalog_name)
        if not scope:
            logger.error(
                "Could not find GeoCatalog resource '%s' in any accessible subscription.",
                geocatalog_name,
            )
            return False

        logger.info(
            "Assigning GeoCatalog Reader on '%s' …", geocatalog_name
        )

        try:
            self._az(
                "role", "assignment", "create",
                "--assignee", principal_id,
                "--role", role_id,
                "--scope", scope,
            )
            logger.info(
                "Role assigned: GeoCatalog Reader → %s", geocatalog_name
            )
            return True
        except RuntimeError as exc:
            msg = str(exc)
            if "already exists" in msg.lower() or "conflict" in msg.lower():
                logger.info(
                    "GeoCatalog Reader role already assigned for '%s'.",
                    geocatalog_name,
                )
                return True
            logger.error("Role assignment failed: %s", exc)
            return False

    def get_existing_principal(
        self, client_id: str
    ) -> Optional[ServicePrincipalInfo]:
        """Look up an existing service principal by its appId/clientId.

        Returns ServicePrincipalInfo if found, None otherwise.
        """
        try:
            result = self._az(
                "ad", "sp", "show",
                "--id", client_id,
            )
            tenant_id = self._get_tenant_id()
            return ServicePrincipalInfo(
                tenant_id=tenant_id,
                client_id=client_id,
                client_secret="",  # Cannot retrieve existing secrets
                display_name=result.get("displayName", ""),
                object_id=result.get("id", result.get("objectId", "")),
                created_new=False,
            )
        except RuntimeError:
            return None

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _verify_az_cli(self) -> None:
        """Ensure the Azure CLI is installed and the user is logged in."""
        try:
            result = subprocess.run(
                ["az", "account", "show"],
                capture_output=True, text=True, timeout=30,
            )
            if result.returncode != 0:
                raise RuntimeError(
                    "Azure CLI is not logged in. Run 'az login' first."
                )
        except FileNotFoundError:
            raise RuntimeError(
                "Azure CLI ('az') not found. Install from "
                "https://learn.microsoft.com/cli/azure/install-azure-cli"
            )

    def _az(self, *args: str) -> dict:
        """Run an ``az`` command and return the parsed JSON output."""
        cmd = ["az", *args, "--output", "json"]
        logger.debug("Running: %s", " ".join(cmd))

        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=120,
        )

        if result.returncode != 0:
            stderr = result.stderr.strip()
            raise RuntimeError(
                f"az command failed (exit {result.returncode}): {stderr}"
            )

        stdout = result.stdout.strip()
        if not stdout:
            return {}
        return json.loads(stdout)

    def _get_tenant_id(self) -> str:
        """Get the current tenant ID from the Azure CLI."""
        result = self._az("account", "show", "--query", "tenantId")
        if isinstance(result, str):
            return result.strip('"')
        return result.get("tenantId", str(result))

    def _get_subscription_id(self) -> str:
        """Get the current subscription ID from the Azure CLI."""
        result = self._az("account", "show", "--query", "id")
        if isinstance(result, str):
            return result.strip('"')
        return result.get("id", str(result))

    def _get_geocatalog_scope(self, geocatalog_name: str) -> str:
        """Look up the full ARM resource ID for a GeoCatalog.

        Searches across all accessible subscriptions for a
        ``Microsoft.Orbital/geoCatalogs`` resource matching *geocatalog_name*.

        Returns the resource ID (suitable as a ``--scope`` value) or empty
        string if not found.
        """
        try:
            results = self._az(
                "resource", "list",
                "--resource-type", "Microsoft.Orbital/geoCatalogs",
                "--query", f"[?name=='{geocatalog_name}'].id",
            )
            if isinstance(results, list) and results:
                return str(results[0]).strip('"')

            # Not in default subscription — search all accessible ones
            subs = self._az("account", "list", "--query", "[].id")
            if not isinstance(subs, list):
                return ""
            for sub_id in subs:
                sub_id = str(sub_id).strip('"')
                try:
                    hits = self._az(
                        "resource", "list",
                        "--resource-type", "Microsoft.Orbital/geoCatalogs",
                        "--subscription", sub_id,
                        "--query", f"[?name=='{geocatalog_name}'].id",
                    )
                    if isinstance(hits, list) and hits:
                        return str(hits[0]).strip('"')
                except RuntimeError:
                    continue
            return ""
        except RuntimeError as exc:
            logger.debug(
                "Failed to look up GeoCatalog '%s': %s",
                geocatalog_name, exc,
            )
            return ""
