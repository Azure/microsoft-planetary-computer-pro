"""
Discover STAC collections from a MPC Pro GeoCatalog instance and resolve
the underlying Azure Blob Storage account + container for each collection.

Each GeoCatalog collection maps to a single managed blob storage container.
The storage info is extracted by inspecting collection-level ``msft:storage_account``
and ``msft:container`` extension properties, or by falling back to parsing
item asset href URLs.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional
from urllib.parse import urlparse

from azure.identity import DefaultAzureCredential
from azure.planetarycomputer import PlanetaryComputerProClient

logger = logging.getLogger(__name__)


@dataclass
class CollectionInfo:
    """Metadata about a discovered STAC collection and its backing storage."""
    collection_id: str
    title: str
    description: str
    storage_account: str
    container: str
    item_count: Optional[int] = None

    @property
    def blob_endpoint(self) -> str:
        return f"https://{self.storage_account}.blob.core.windows.net"

    @property
    def display_name(self) -> str:
        return self.title or self.collection_id


class CollectionDiscovery:
    """Discover collections and their storage containers from MPC Pro."""

    def __init__(self, endpoint: str):
        self._endpoint = endpoint.rstrip("/")
        self._credential = DefaultAzureCredential()
        self._client = PlanetaryComputerProClient(
            endpoint=self._endpoint,
            credential=self._credential,
        )

    def list_collections(self) -> list[CollectionInfo]:
        """Retrieve all collections and resolve their storage info.

        Returns a list of ``CollectionInfo`` with storage account and
        container populated for every collection where we can discover
        the backing storage.
        """
        logger.info("Listing collections from %s …", self._endpoint)
        result = self._client.stac.list_collections()
        collections = result.collections

        logger.info("Found %d collection(s).", len(collections))

        infos: list[CollectionInfo] = []
        for coll in collections:
            coll_id = coll.id
            title = getattr(coll, "title", None) or coll.get("title", "") or ""
            description = (
                getattr(coll, "short_description", None)
                or coll.get("msft:short_description", "")
                or getattr(coll, "description", None)
                or coll.get("description", "")
                or ""
            )

            # ------------------------------------------------------------------
            # Strategy 1: Check extension properties on the collection itself
            # ------------------------------------------------------------------
            storage_account = coll.get("msft:storage_account", "")
            container = coll.get("msft:container", "")

            # ------------------------------------------------------------------
            # Strategy 2: Fetch one item and parse asset href
            # ------------------------------------------------------------------
            if not storage_account or not container:
                storage_account, container = self._discover_storage_from_items(coll_id)

            if not storage_account or not container:
                logger.warning(
                    "Could not determine storage for collection '%s'. "
                    "It will still be listed but may require manual storage info.",
                    coll_id,
                )

            infos.append(
                CollectionInfo(
                    collection_id=coll_id,
                    title=title,
                    description=description[:120] if description else "",
                    storage_account=storage_account,
                    container=container,
                )
            )

        return infos

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _discover_storage_from_items(
        self, collection_id: str
    ) -> tuple[str, str]:
        """Search for one item and parse blob URL from its asset href."""
        try:
            from azure.planetarycomputer.models import StacSearchParameters

            params = StacSearchParameters(
                collections=[collection_id],
                limit=1,
            )
            response = self._client.stac.search(body=params)
            features = response.get("features", [])
            if not features:
                logger.debug(
                    "No items in collection '%s'; cannot auto-detect storage.",
                    collection_id,
                )
                return ("", "")

            item = features[0]
            assets = item.get("assets", {})
            # Try common asset keys
            for key in ("data", "visual", "image", "B04"):
                if key in assets:
                    href = assets[key].get("href", "")
                    return self._parse_blob_url(href)

            # Fall back to first asset
            for asset in assets.values():
                href = asset.get("href", "")
                if href:
                    return self._parse_blob_url(href)

        except Exception as exc:
            logger.debug(
                "Error probing items for collection '%s': %s",
                collection_id,
                exc,
            )

        return ("", "")

    @staticmethod
    def _parse_blob_url(href: str) -> tuple[str, str]:
        """Extract storage account and container from an Azure Blob URL.

        Expected format:
            https://<account>.blob.core.windows.net/<container>/...
        """
        parsed = urlparse(href)
        host = parsed.hostname or ""

        if ".blob.core.windows.net" not in host:
            return ("", "")

        account = host.split(".")[0]
        path_parts = parsed.path.strip("/").split("/")
        container = path_parts[0] if path_parts else ""

        return (account, container)
