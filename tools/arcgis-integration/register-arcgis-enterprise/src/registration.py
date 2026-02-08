"""
Register Azure Blob Storage containers as cloud data stores on ArcGIS Server.

Uses the ``arcgis`` Python API to connect to an ArcGIS Enterprise portal,
locate the target server (Image Server or Hosting Server), and register
each selected MPC Pro collection's blob container as a cloud data store.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from typing import Optional

from arcgis.gis import GIS

from .config import ArcGISConfig, StorageCredentialConfig
from .discovery import CollectionInfo

logger = logging.getLogger(__name__)


@dataclass
class RegistrationResult:
    """Outcome of a single cloud store registration attempt."""
    collection_id: str
    store_name: str
    success: bool
    message: str
    already_existed: bool = False
    validated: Optional[bool] = None
    validation_message: str = ""


class CloudStoreRegistrar:
    """Registers blob containers as cloud data stores on ArcGIS Server."""

    def __init__(
        self,
        arcgis_config: ArcGISConfig,
        storage_config: StorageCredentialConfig,
        geocatalog_endpoint: str = "",
    ):
        self._arcgis_config = arcgis_config
        self._storage_config = storage_config
        self._geocatalog_endpoint = geocatalog_endpoint.rstrip("/")
        self._gis: Optional[GIS] = None
        self._server = None
        self._datastores = None

    # ------------------------------------------------------------------
    # Connection
    # ------------------------------------------------------------------

    def update_storage_config(self, config: StorageCredentialConfig) -> None:
        """Replace the storage credential configuration (e.g. after SP creation)."""
        self._storage_config = config

    def connect(self) -> None:
        """Connect to ArcGIS Enterprise and locate the target server."""
        cfg = self._arcgis_config

        logger.info("Connecting to ArcGIS Enterprise at %s …", cfg.portal_url)
        self._gis = GIS(
            cfg.portal_url,
            cfg.username,
            cfg.password,
            verify_cert=cfg.verify_cert,
        )
        logger.info(
            "Connected as %s.",
            self._gis.properties.user.username,
        )

        # Locate the server by role, with fallback to first available server
        server = None
        try:
            servers_by_role = self._gis.admin.servers.get(role=cfg.server_role)
            if servers_by_role:
                server = servers_by_role[0]
                logger.info("Found server with role '%s': %s", cfg.server_role, server.url)
        except Exception as exc:
            logger.debug("servers.get(role='%s') failed: %s", cfg.server_role, exc)

        if server is None:
            # Fall back: pick the first server from the list
            all_servers = self._gis.admin.servers.list()
            if not all_servers:
                raise RuntimeError(
                    f"No servers found in the ArcGIS Enterprise deployment."
                )
            server = all_servers[0]
            logger.info(
                "No server with role '%s' found — using first available server: %s",
                cfg.server_role,
                server.url,
            )

        self._server = server
        self._datastores = self._server.datastores
        logger.info("DataStoreManager ready at %s", self._datastores._url)

    # ------------------------------------------------------------------
    # Existing store queries
    # ------------------------------------------------------------------

    def list_existing_cloud_stores(self) -> list[str]:
        """Return the names of already-registered cloud stores."""
        self._ensure_connected()
        try:
            items = self._datastores.search(
                parent_path="/cloudStores",
                types="cloudStore",
            )
            return [item.datapath.split("/")[-1] for item in items]
        except Exception:
            # Fallback: just list top-level items
            return []

    def store_exists(self, store_name: str) -> bool:
        """Check whether a cloud store with the given name is already registered."""
        self._ensure_connected()
        try:
            result = self._datastores.get(f"/cloudStores/{store_name}")
            if result is None:
                return False
            # ds.get() can return a dict with status=error for missing items
            if hasattr(result, "properties"):
                props = result.properties
                if isinstance(props, dict) and props.get("status") == "error":
                    return False
            return True
        except Exception:
            return False

    def delete_store(self, store_name: str) -> bool:
        """Delete a registered cloud store by name."""
        self._ensure_connected()
        try:
            con = self._server._con
            url = f"{self._datastores._url}/unregisterItem"
            result = con.post(url, {"itempath": f"/cloudStores/{store_name}", "force": True})
            success = result.get("success", False) if isinstance(result, dict) else bool(result)
            if success:
                logger.info("Deleted cloud store '%s'.", store_name)
            return success
        except Exception as exc:
            logger.error("Failed to delete cloud store '%s': %s", store_name, exc)
            return False

    # ------------------------------------------------------------------
    # Registration
    # ------------------------------------------------------------------

    def register(
        self,
        collection: CollectionInfo,
        store_name: Optional[str] = None,
        dry_run: bool = False,
    ) -> RegistrationResult:
        """Register a single collection as a cloud data store.

        Parameters
        ----------
        collection:
            Collection metadata including storage_account and container.
        store_name:
            Override for the data store name. Defaults to the collection id
            with hyphens replaced by underscores.
        dry_run:
            If True, validate the payload but do not actually register.
        """
        self._ensure_connected()

        if not collection.storage_account or not collection.container:
            return RegistrationResult(
                collection_id=collection.collection_id,
                store_name="",
                success=False,
                message="Missing storage account or container information.",
            )

        name = store_name or collection.collection_id.replace("-", "_")

        # Check if already registered
        if self.store_exists(name):
            logger.info(
                "Cloud store '%s' already exists — skipping.", name
            )
            return RegistrationResult(
                collection_id=collection.collection_id,
                store_name=name,
                success=True,
                message="Cloud store already registered.",
                already_existed=True,
            )

        # Build the data item dict (MPC Pro geoCatalog format)
        data_item = self._build_data_item(
            name=name,
            storage_account=collection.storage_account,
            container=collection.container,
            collection_id=collection.collection_id,
        )

        if dry_run:
            logger.info(
                "[DRY RUN] Would register cloud store '%s' → %s/%s",
                name,
                collection.storage_account,
                collection.container,
            )
            return RegistrationResult(
                collection_id=collection.collection_id,
                store_name=name,
                success=True,
                message="Dry run — not registered.",
            )

        # Register the cloud store via ds.add(item)
        logger.info(
            "Registering cloud store '%s' → %s/%s …",
            name,
            collection.storage_account,
            collection.container,
        )

        try:
            self._datastores.add(data_item)
            logger.info("Cloud store '%s' registered at server level.", name)

            # Validate the newly-registered store
            validated, val_msg = self._validate_store(name)

            # Federate the data store item so it appears in the portal
            federated = self._federate_store(name)

            status_parts = ["Registered"]
            if validated:
                status_parts.append("validated")
            else:
                status_parts.append(f"validation: {val_msg}")
            if federated:
                status_parts.append("federated to portal")
            else:
                status_parts.append("federation pending")

            return RegistrationResult(
                collection_id=collection.collection_id,
                store_name=name,
                success=True,
                message=", ".join(status_parts) + ".",
                validated=validated,
                validation_message=val_msg,
            )

        except Exception as exc:
            logger.error("Failed to register '%s': %s", name, exc)
            return RegistrationResult(
                collection_id=collection.collection_id,
                store_name=name,
                success=False,
                message=str(exc),
            )

    def register_many(
        self,
        collections: list[CollectionInfo],
        dry_run: bool = False,
    ) -> list[RegistrationResult]:
        """Register multiple collections as cloud data stores."""
        results: list[RegistrationResult] = []
        for coll in collections:
            result = self.register(coll, dry_run=dry_run)
            results.append(result)
        return results

    # ------------------------------------------------------------------
    # Data item and connection string builders
    # ------------------------------------------------------------------

    def _build_data_item(self, name: str, storage_account: str, container: str, collection_id: str = "") -> dict:
        """Build the MPC Pro geoCatalog data item dict for ``ds.add()``."""
        conn_str = self._build_connection_string(storage_account, container, collection_id)
        return {
            "path": f"/cloudStores/{name}",
            "type": "cloudStore",
            "provider": "azure",
            "info": {
                "serviceType": "geoCatalog",
                "objectStore": container,
                "connectionString": conn_str,
                "isManaged": False,
            },
        }

    def _build_connection_string(self, storage_account: str, container: str = "", collection_id: str = "") -> str:
        """Build the JSON connection string based on credential type.

        For ``service_principal`` credentials targeting MPC Pro, produces the
        ``servicePrincipal`` format with ``tokenGenerationUrl`` and
        ``scopes`` fields that ArcGIS Enterprise needs to access
        geoCatalog-managed blob storage.
        """
        cred = self._storage_config
        cred_type = cred.credential_type.lower().replace("-", "_")

        if cred_type == "service_principal":
            # MPC Pro geoCatalog connection format
            token_url = ""
            if self._geocatalog_endpoint and collection_id:
                token_url = (
                    f"{self._geocatalog_endpoint}/sas/token/{collection_id}"
                    f"?api-version=2025-04-30-preview"
                )
            conn = {
                "credentialType": "servicePrincipal",
                "tenantId": cred.tenant_id,
                "clientId": cred.client_id,
                "clientSecret": cred.client_secret,
                "scopes": ["https://geocatalog.spatio.azure.com/.default"],
                "accountName": storage_account,
                "accountEndpoint": "core.windows.net",
                "authorityHost": "login.microsoftonline.com",
                "tokenGenerationUrl": token_url,
                "defaultEndpointsProtocol": "https",
            }

        elif cred_type == "access_key":
            conn = {
                "credentialType": "accessKey",
                "accountName": storage_account,
                "accountKey": cred.account_key,
                "accountEndpoint": f"https://{storage_account}.blob.core.windows.net",
                "defaultEndpointsProtocol": "https",
            }

        elif cred_type == "managed_identity":
            conn = {
                "credentialType": "userAssignedIdentity",
                "managedIdentityClientId": cred.managed_identity_client_id,
                "accountName": storage_account,
                "accountEndpoint": f"https://{storage_account}.blob.core.windows.net",
                "defaultEndpointsProtocol": "https",
            }

        elif cred_type == "sas_token":
            conn = {
                "credentialType": "sasToken",
                "sasToken": cred.sas_token,
                "accountName": storage_account,
                "accountEndpoint": f"https://{storage_account}.blob.core.windows.net",
                "defaultEndpointsProtocol": "https",
            }

        else:
            raise ValueError(
                f"Unsupported credential_type: '{cred.credential_type}'. "
                f"Use one of: service_principal, access_key, managed_identity, sas_token"
            )

        return json.dumps(conn)

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    def validate_store(self, store_name: str) -> tuple[bool, str]:
        """Validate a registered cloud store by name (public API)."""
        self._ensure_connected()
        return self._validate_store(store_name)

    def validate_all(self, store_names: list[str]) -> dict[str, tuple[bool, str]]:
        """Validate multiple cloud stores. Returns {name: (ok, message)}."""
        self._ensure_connected()
        results: dict[str, tuple[bool, str]] = {}
        for name in store_names:
            results[name] = self._validate_store(name)
        return results

    def _validate_store(self, store_name: str) -> tuple[bool, str]:
        """Validate a single cloud store. Returns (success, message).

        Uses the REST ``validateDataItem`` endpoint directly because the
        Python API's ``Datastore.validate()`` incorrectly returns ``False``
        for cloud stores that actually validate successfully.
        """
        try:
            # Get the full item definition from findItems
            items_resp = self._server._con.post(
                f"{self._datastores._url}/findItems",
                {"parentPath": "/cloudStores", "types": "cloudStore"},
            )
            items = items_resp.get("items", []) if isinstance(items_resp, dict) else []
            item = next(
                (i for i in items if i.get("path") == f"/cloudStores/{store_name}"),
                None,
            )
            if item is None:
                return (False, f"Store '{store_name}' not found.")

            # Validate via REST
            result = self._server._con.post(
                f"{self._datastores._url}/validateDataItem",
                {"item": json.dumps(item)},
            )
            logger.info("Validation for '%s': %s", store_name, result)

            if isinstance(result, dict):
                status = result.get("status", "")
                if status == "success":
                    return (True, "OK")
                messages = result.get("messages", [])
                msg = "; ".join(str(m) for m in messages) if messages else status or "Unknown error"
                return (False, msg)

            return (bool(result), str(result))

        except Exception as exc:
            logger.warning("Validation check for '%s' returned: %s", store_name, exc)
            return (False, str(exc))

    def _federate_store(self, store_name: str) -> bool:
        """Federate the data store item so it appears in the portal."""
        try:
            path = f"/cloudStores/{store_name}"
            result = self._datastores.federate_data_item(path)
            if result:
                logger.info("Data store '%s' federated to portal.", store_name)
            else:
                logger.warning("Federation of '%s' returned False.", store_name)
            return bool(result)
        except Exception as exc:
            logger.warning("Failed to federate '%s': %s", store_name, exc)
            return False

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _ensure_connected(self) -> None:
        if self._datastores is None:
            raise RuntimeError(
                "Not connected. Call connect() before performing operations."
            )
