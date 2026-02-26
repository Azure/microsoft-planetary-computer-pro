"""
ArcGIS Image Collection manager.

Uses the ArcGIS API for Python (arcgis package) to create and manage image
collections on ArcGIS Enterprise with Image Server. Maps STAC item blob URLs
to registered cloud data store paths for direct Image Server access.
"""

import logging
from typing import Optional
from urllib.parse import urlparse

from arcgis.gis import GIS
from arcgis.raster import ImageryLayer
from arcgis.raster.analytics import create_image_collection

from .config import ArcGISEnterpriseConfig, CloudStoreConfig, ImageCollectionConfig
from .stac_client import StacItemResult

logger = logging.getLogger(__name__)


class ImageryManagerError(Exception):
    """Raised when image collection operations fail."""
    pass


class ImageryManager:
    """
    Manages ArcGIS Image Collections on ArcGIS Enterprise.

    Handles creating image collections, querying existing items for
    deduplication, and adding new rasters from cloud-stored COGs.
    """

    def __init__(
        self,
        enterprise_config: ArcGISEnterpriseConfig,
        cloud_store_config: CloudStoreConfig,
        image_collection_config: ImageCollectionConfig,
    ):
        """
        Initialize the imagery manager and connect to ArcGIS Enterprise.

        Args:
            enterprise_config: ArcGIS Enterprise portal connection settings.
            cloud_store_config: Cloud data store configuration for blob URL mapping.
            image_collection_config: Image collection settings.
        """
        self._cloud_config = cloud_store_config
        self._collection_config = image_collection_config
        self._gis = self._connect(enterprise_config)
        self._image_server_url = enterprise_config.image_server_url

    def _connect(self, config: ArcGISEnterpriseConfig) -> GIS:
        """Establish connection to ArcGIS Enterprise portal."""
        logger.info("Connecting to ArcGIS Enterprise at %s", config.portal_url)

        try:
            if config.auth_method == "username_password":
                gis = GIS(
                    url=config.portal_url,
                    username=config.username,
                    password=config.password,
                    verify_cert=config.verify_cert,
                )
            elif config.auth_method == "oauth":
                gis = GIS(
                    url=config.portal_url,
                    client_id=config.client_id,
                    verify_cert=config.verify_cert,
                )
            elif config.auth_method == "windows":
                # Windows Integrated Authentication (IWA / Kerberos)
                gis = GIS(url=config.portal_url, verify_cert=config.verify_cert)
            else:
                raise ImageryManagerError(
                    f"Unsupported auth method: {config.auth_method}"
                )
        except Exception as e:
            raise ImageryManagerError(
                f"Failed to connect to ArcGIS Enterprise: {e}"
            ) from e

        logger.info("Connected to ArcGIS Enterprise as %s", gis.properties.user.username)
        return gis

    def blob_url_to_cloud_store_path(self, blob_url: str) -> str:
        """
        Map a full Azure Blob Storage URL to a cloud data store relative path.

        Converts:
            https://<account>.blob.core.windows.net/<container>/path/to/cog.tif
        To:
            /cloudStores/<store_name>/path/to/cog.tif

        Args:
            blob_url: Full Azure Blob Storage URL.

        Returns:
            Cloud data store relative path usable by ArcGIS Image Server.
        """
        parsed = urlparse(blob_url)
        # The path is /<container>/path/to/file.tif — strip the container prefix
        path_parts = parsed.path.lstrip("/").split("/", 1)
        if len(path_parts) < 2:
            logger.warning("Cannot parse blob path from URL: %s", blob_url)
            return blob_url

        container = path_parts[0]
        relative_path = path_parts[1]

        # Verify the URL matches the expected storage account and container
        expected_host = f"{self._cloud_config.storage_account}.blob.core.windows.net"
        if parsed.hostname != expected_host:
            logger.warning(
                "Blob URL host '%s' does not match expected '%s'. Using URL as-is.",
                parsed.hostname, expected_host,
            )
            return blob_url

        if container != self._cloud_config.container:
            logger.warning(
                "Blob container '%s' does not match expected '%s'. Using URL as-is.",
                container, self._cloud_config.container,
            )
            return blob_url

        cloud_path = f"/cloudStores/{self._cloud_config.store_name}/{relative_path}"
        return cloud_path

    def find_image_collection(self) -> Optional[dict]:
        """
        Search for an existing image collection item in the Enterprise portal.

        Returns:
            The portal Item object if found, None otherwise.
        """
        collection_name = self._collection_config.name
        logger.info("Searching for image collection '%s'", collection_name)

        results = self._gis.content.search(
            query=f'title:"{collection_name}" AND type:"Image Collection"',
            max_items=10,
        )

        for item in results:
            if item.title == collection_name:
                logger.info("Found existing image collection: %s (id=%s)", item.title, item.id)
                return item

        logger.info("Image collection '%s' not found", collection_name)
        return None

    def get_existing_item_ids(self, collection_item) -> set[str]:
        """
        Query the image collection's catalog to get IDs of already-ingested items.

        Uses the imagery layer's query or export capabilities to retrieve the
        footprint table, extracting item identifiers for deduplication.

        Args:
            collection_item: The ArcGIS portal Item representing the image collection.

        Returns:
            Set of STAC item IDs that are already in the collection.
        """
        logger.info("Querying existing items in collection '%s'", collection_item.title)

        try:
            imagery_layer = ImageryLayer(collection_item.url, gis=self._gis)

            # Query the footprint/catalog table for raster names
            # The 'Name' field typically stores the raster identifier
            query_result = imagery_layer.query(
                where="1=1",
                out_fields="Name",
                return_geometry=False,
            )

            existing_ids = set()
            for feature in query_result.features:
                name = feature.attributes.get("Name", "")
                if name:
                    existing_ids.add(name)

            logger.info("Found %d existing items in collection", len(existing_ids))
            return existing_ids

        except Exception as e:
            logger.warning("Could not query existing items: %s. Assuming empty.", e)
            return set()

    def create_collection(
        self, initial_raster_paths: list[str]
    ) -> dict:
        """
        Create a new image collection with initial rasters.

        Args:
            initial_raster_paths: Cloud store paths to the first batch of rasters.

        Returns:
            The newly created portal Item.

        Raises:
            ImageryManagerError: If creation fails.
        """
        config = self._collection_config
        logger.info(
            "Creating image collection '%s' with %d initial rasters",
            config.name, len(initial_raster_paths),
        )

        try:
            result = create_image_collection(
                image_collection=config.name,
                input_rasters=initial_raster_paths,
                raster_type_name=config.raster_type_name,
                gis=self._gis,
                context={
                    "description": config.description,
                    "outSR": {"wkid": config.coordinate_system},
                },
            )
            logger.info("Image collection '%s' created successfully", config.name)
            return result
        except Exception as e:
            raise ImageryManagerError(
                f"Failed to create image collection '{config.name}': {e}"
            ) from e

    def add_rasters(
        self, collection_item, raster_paths: list[str], item_ids: list[str]
    ) -> dict:
        """
        Add new rasters to an existing image collection.

        Uses the imagery layer's add_rasters method or the raster analytics
        API to append rasters to the collection.

        Args:
            collection_item: The ArcGIS portal Item for the image collection.
            raster_paths: Cloud store paths to the rasters to add.
            item_ids: Corresponding STAC item IDs (used for naming/tracking).

        Returns:
            Result dict with status information.

        Raises:
            ImageryManagerError: If adding rasters fails.
        """
        logger.info(
            "Adding %d rasters to collection '%s'",
            len(raster_paths), collection_item.title,
        )

        try:
            imagery_layer = ImageryLayer(collection_item.url, gis=self._gis)

            # Build raster items with names for deduplication tracking
            raster_items = []
            for path, stac_id in zip(raster_paths, item_ids):
                raster_items.append({
                    "uri": path,
                    "name": stac_id,
                })

            result = imagery_layer.add_rasters(
                raster_type=self._collection_config.raster_type_name,
                item_ids=None,
                service_url=None,
                compute_statistics=False,
                build_pyramids=False,
                build_thumbnail=False,
                minimum_cell_size_factor=None,
                maximum_cell_size_factor=None,
                attributes=None,
                geodata_transforms=None,
                geodata_transform_apply_method=None,
                max_cell_size=None,
                min_dimension=None,
                spatial_reference=None,
                filter=None,
                process_items=None,
                context=None,
                raster_items=raster_items,
            )

            logger.info("Successfully added %d rasters", len(raster_paths))
            return result

        except Exception as e:
            raise ImageryManagerError(
                f"Failed to add rasters to collection: {e}"
            ) from e

    def prepare_new_items(
        self,
        stac_items: list[StacItemResult],
        existing_ids: set[str],
    ) -> tuple[list[str], list[str], list[StacItemResult]]:
        """
        Filter STAC items to only new ones and map URLs to cloud store paths.

        Args:
            stac_items: All STAC items from the search.
            existing_ids: Set of item IDs already in the collection.

        Returns:
            Tuple of (cloud_store_paths, item_ids, new_stac_items) for items
            not already in the collection.
        """
        cloud_paths = []
        item_ids = []
        new_items = []

        for item in stac_items:
            if item.item_id in existing_ids:
                logger.debug("Skipping already-ingested item: %s", item.item_id)
                continue

            cloud_path = self.blob_url_to_cloud_store_path(item.asset_href)
            cloud_paths.append(cloud_path)
            item_ids.append(item.item_id)
            new_items.append(item)

        logger.info(
            "Filtered %d STAC items: %d new, %d already in collection",
            len(stac_items), len(new_items), len(stac_items) - len(new_items),
        )
        return cloud_paths, item_ids, new_items

    @property
    def gis(self) -> GIS:
        """Return the underlying GIS connection."""
        return self._gis
