"""
STAC client wrapper for MPC Pro GeoCatalog queries.

Uses the MPC Pro SDK (azure-planetarycomputer) with DefaultAzureCredential
to perform authenticated STAC searches. Returns raw (unsigned) asset hrefs
since ArcGIS Image Server accesses blob storage directly via its registered
cloud data store.
"""

import logging
from dataclasses import dataclass, field
from typing import Optional

from azure.identity import DefaultAzureCredential
from azure.planetarycomputer import PlanetaryComputerProClient
from azure.planetarycomputer.models import StacSearchParameters

from .config import GeoCatalogConfig, StacQueryConfig

logger = logging.getLogger(__name__)


@dataclass
class StacItemResult:
    """Represents a discovered STAC item with its asset URLs."""
    item_id: str
    collection: str
    datetime: Optional[str]
    bbox: Optional[list[float]]
    asset_href: str
    asset_key: str
    properties: dict = field(default_factory=dict)


class StacClient:
    """
    Client for querying STAC items from an MPC Pro GeoCatalog.

    Uses the MPC Pro SDK with Azure AD authentication. Returns raw blob
    URLs (not SAS-signed) since ArcGIS Image Server will access storage
    directly through its registered cloud data store.
    """

    def __init__(self, geocatalog_config: GeoCatalogConfig):
        """
        Initialize the STAC client.

        Args:
            geocatalog_config: GeoCatalog connection configuration.
        """
        self._endpoint = geocatalog_config.endpoint
        self._credential = DefaultAzureCredential()
        self._client = PlanetaryComputerProClient(
            endpoint=self._endpoint,
            credential=self._credential,
        )
        logger.info("STAC client initialized for %s", self._endpoint)

    def search(
        self, query_config: StacQueryConfig, source_asset_key: str = "visual"
    ) -> list[StacItemResult]:
        """
        Search the GeoCatalog for STAC items matching the query configuration.

        Automatically paginates through all result pages.

        Args:
            query_config: STAC query parameters (collections, bbox, datetime, filter).
            source_asset_key: The asset key to extract from each item (e.g., "visual",
                "B04", "data"). Defaults to "visual".

        Returns:
            List of StacItemResult objects with raw (unsigned) asset hrefs.
        """
        search_params = StacSearchParameters(
            collections=query_config.collections,
            limit=query_config.limit,
        )

        if query_config.bbox:
            search_params.bounding_box = query_config.bbox

        if query_config.datetime:
            search_params.date_time = query_config.datetime

        if query_config.filter:
            search_params.filter = query_config.filter
            if query_config.filter_lang:
                search_params.filter_lang = query_config.filter_lang

        logger.info(
            "Searching GeoCatalog: collections=%s, bbox=%s, datetime=%s",
            query_config.collections,
            query_config.bbox,
            query_config.datetime,
        )

        results: list[StacItemResult] = []
        items_searched = 0

        # Paginate through all results
        response = self._client.stac.search(body=search_params)
        while True:
            features = response.get("features", [])
            if not features:
                break

            for feature in features:
                item_id = feature.get("id", "")
                collection = feature.get("collection", "")
                properties = feature.get("properties", {})
                bbox = feature.get("bbox")
                dt = properties.get("datetime")

                assets = feature.get("assets", {})
                asset = assets.get(source_asset_key)
                if asset is None:
                    # Try fallback asset keys for common imagery types
                    for fallback_key in ["data", "B04", "image"]:
                        asset = assets.get(fallback_key)
                        if asset is not None:
                            logger.debug(
                                "Item %s: using fallback asset key '%s' (requested '%s')",
                                item_id, fallback_key, source_asset_key,
                            )
                            break

                if asset is None:
                    logger.warning(
                        "Item %s: no suitable asset found (available: %s)",
                        item_id, list(assets.keys()),
                    )
                    continue

                href = asset.get("href", "")
                actual_key = source_asset_key if source_asset_key in assets else "fallback"

                results.append(
                    StacItemResult(
                        item_id=item_id,
                        collection=collection,
                        datetime=dt,
                        bbox=bbox,
                        asset_href=href,
                        asset_key=actual_key,
                        properties=properties,
                    )
                )

            items_searched += len(features)

            # Check for next page
            links = response.get("links", [])
            next_link = next((l for l in links if l.get("rel") == "next"), None)
            if next_link is None:
                break

            # Follow the next page using the search endpoint with the token
            next_body = next_link.get("body")
            if next_body:
                response = self._client.stac.search(body=next_body)
            else:
                break

        logger.info(
            "STAC search complete: %d items found, %d with usable assets",
            items_searched, len(results),
        )
        return results

    def close(self):
        """Close the underlying client and credential."""
        self._client.close()
        self._credential.close()
