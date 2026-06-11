"""
geoai.core.stac.searcher

STACSearcher - Search and filter STAC items from GeoCatalog.
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional

import pystac_client
from shapely.geometry import mapping

logger = logging.getLogger(__name__)


class STACSearcher:
    """
    STACSearcher - Search STAC catalog for items matching constraints.

    Extracted from AI Workflow patch-sampler service.

    Handles:
    - Spatial search (geometry intersection)
    - Temporal search (datetime filtering)
    - CQL2 filtering (cloud cover, etc.)
    - Item selection based on sort criteria
    """

    def __init__(self, geocatalog_uri: str, collection: str, credential=None):
        """
        Initialize STACSearcher.

        :param geocatalog_uri: GeoCatalog/STAC API endpoint
        :param collection: Collection name
        :param credential: Azure credential (optional, for authenticated catalogs)
        """
        self.geocatalog_uri = geocatalog_uri
        self.collection = collection
        self.credential = credential
        self._client = None

    def _get_client(self):
        """Get or create STAC client (lazy initialization)"""
        if self._client is None:
            self._client = pystac_client.Client.open(self.geocatalog_uri)
            logger.info(f"Connected to STAC catalog: {self.geocatalog_uri}")
        return self._client

    async def search(
        self,
        geometry: Optional[Dict] = None,
        bbox: Optional[List[float]] = None,
        datetime: Optional[str] = None,
        filter: Optional[Dict] = None,
        limit: Optional[int] = None,
        sort_by: Optional[List[Dict]] = None,
        max_retries: int = 5,
    ) -> List:
        """
        Search STAC catalog for items with automatic retry on timeout.

        :param geometry: GeoJSON geometry for spatial search (fallback if bbox not provided)
        :param bbox: Bounding box [minx, miny, maxx, maxy] (preferred for performance)
        :param datetime: ISO 8601 datetime or range (e.g., "2024-01-01/2024-12-31")
        :param filter: CQL2 filter dict (e.g., {"eo:cloud_cover": {"lte": 20}})
        :param limit: Max number of items to return
        :param sort_by: Sort criteria [{"field": "...", "direction": "asc|desc"}]
        :param max_retries: Maximum retry attempts on timeout (default: 5)
        :return: List of STAC items
        """
        for attempt in range(max_retries):
            try:
                client = self._get_client()

                # Build search parameters
                search_params = {
                    "collections": [self.collection],
                }

                # Prefer bbox over geometry (bbox is faster and uses spatial index)
                if bbox is not None:
                    search_params["bbox"] = bbox
                    spatial_type = "bbox"
                    spatial_desc = f"[{bbox[0]:.4f}, {bbox[1]:.4f}, {bbox[2]:.4f}, {bbox[3]:.4f}]"
                elif geometry is not None:
                    # Round coordinates to reduce URL length (prevent 413 errors)
                    rounded_geometry = self._round_geometry_coordinates(geometry, decimals=6)
                    search_params["intersects"] = rounded_geometry
                    spatial_type = "intersects"
                    spatial_desc = rounded_geometry.get("type", "unknown")
                else:
                    raise ValueError("Either geometry or bbox must be provided for STAC search")

                if datetime:
                    search_params["datetime"] = datetime

                if limit:
                    search_params["limit"] = limit

                # Add CQL2 filter if provided
                if filter:
                    search_params["filter"] = filter
                    search_params["filter_lang"] = "cql2-json"
                    logger.debug(f"Applying CQL filter: {filter}")

                # Add sort criteria if provided
                if sort_by:
                    # Convert sort_by to STAC API format
                    sort_str = ",".join([f"{s['direction'][0]}{s['field']}" for s in sort_by])
                    search_params["sortby"] = sort_str

                logger.info(
                    f"Searching STAC for collection: {self.collection}, "
                    f"spatial={spatial_type} ({spatial_desc}), "
                    f"datetime={datetime}, filter={filter is not None}, "
                    f"limit={limit}"
                )

                # Execute search
                search = client.search(**search_params)
                
                # Run the blocking list() operation in a thread pool for async compatibility
                loop = asyncio.get_event_loop()
                items = await loop.run_in_executor(None, lambda: list(search.items()))

                logger.info(f"Found {len(items)} STAC items for collection: {self.collection}")

                return items

            except Exception as e:
                error_msg = str(e).lower()
                is_timeout = "timeout" in error_msg or "timed out" in error_msg or "exceeded the maximum allowed time" in error_msg

                if is_timeout and attempt < max_retries - 1:
                    # Exponential backoff: 2s, 4s, 8s, 16s...
                    wait_time = 2 ** attempt
                    logger.warning(
                        f"STAC search timeout (attempt {attempt + 1}/{max_retries}), "
                        f"retrying in {wait_time}s... Error: {e}"
                    )
                    await asyncio.sleep(wait_time)
                else:
                    # Final failure or non-timeout error
                    if is_timeout:
                        logger.error(
                            f"STAC search failed after {max_retries} attempts. "
                            f"Planetary Computer API may be experiencing high load."
                        )
                    else:
                        logger.error(f"STAC search failed for collection {self.collection}: {e}")
                    raise

    async def search_from_external(self, stac_search: Any) -> List:
        """
        Execute a pre-built STAC search (pass-through mode).

        For advanced users who want full control over STAC queries.

        :param stac_search: Pre-built pystac_client.ItemSearch object
        :return: List of STAC items

        Example:
            >>> import pystac_client
            >>> search = pystac_client.Client.open("https://...").search(
            ...     collections=["naip"],
            ...     bbox=[-122.5, 37.5, -122.0, 38.0],
            ...     query={"eo:cloud_cover": {"lt": 20}}
            ... )
            >>> items = await searcher.search_from_external(search)
        """
        logger.info("Using pre-built STAC search (pass-through mode)")

        try:
            # Execute the external search
            items = list(stac_search.items())

            logger.info(f"Found {len(items)} STAC items from external search")

            return items

        except Exception as e:
            logger.error(f"External STAC search failed: {e}")
            raise

    def _round_geometry_coordinates(self, geometry: Dict, decimals: int = 6) -> Dict:
        """
        Round geometry coordinates to reduce URL length for STAC searches.

        :param geometry: GeoJSON geometry
        :param decimals: Number of decimal places to round to
        :return: Geometry with rounded coordinates
        """
        try:

            def round_coords(coords):
                if isinstance(coords[0], (list, tuple)):
                    return [round_coords(c) for c in coords]
                else:
                    return [round(c, decimals) for c in coords]

            rounded_dict = geometry.copy()
            rounded_dict["coordinates"] = round_coords(geometry["coordinates"])

            return rounded_dict

        except Exception as e:
            logger.warning(f"Failed to round geometry coordinates: {e}")
            return geometry
