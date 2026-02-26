"""
ArcGIS Image Service publisher.

Manages publishing and refreshing imagery layers (image services) on
ArcGIS Enterprise using the ArcGIS API for Python.
"""

import logging
from typing import Optional

from arcgis.gis import GIS
from arcgis.raster import ImageryLayer

from .config import ImageCollectionConfig

logger = logging.getLogger(__name__)


class ServicePublisherError(Exception):
    """Raised when image service publishing operations fail."""
    pass


class ServicePublisher:
    """
    Publishes and refreshes imagery layers on ArcGIS Enterprise.

    After rasters are added to an image collection, this class handles
    publishing the collection as an imagery layer or refreshing an
    existing service to pick up new data.
    """

    def __init__(self, gis: GIS, collection_config: ImageCollectionConfig):
        """
        Initialize the service publisher.

        Args:
            gis: Authenticated GIS connection to ArcGIS Enterprise.
            collection_config: Image collection configuration.
        """
        self._gis = gis
        self._collection_config = collection_config

    def find_service(self) -> Optional[dict]:
        """
        Look for an existing imagery layer (image service) in the portal.

        Returns:
            The portal Item for the imagery layer if found, None otherwise.
        """
        name = self._collection_config.name
        logger.info("Searching for imagery layer '%s'", name)

        results = self._gis.content.search(
            query=f'title:"{name}" AND type:"Imagery Layer"',
            max_items=10,
        )

        for item in results:
            if item.title == name:
                logger.info(
                    "Found existing imagery layer: %s (url=%s)", item.title, item.url
                )
                return item

        logger.info("No existing imagery layer found for '%s'", name)
        return None

    def publish_service(self, collection_item) -> dict:
        """
        Publish an image collection as a new imagery layer.

        The image collection item is published to ArcGIS Image Server,
        creating a new image service accessible via the Enterprise portal.

        Args:
            collection_item: The portal Item for the image collection.

        Returns:
            The published imagery layer portal Item.

        Raises:
            ServicePublisherError: If publishing fails.
        """
        logger.info("Publishing image collection '%s' as imagery layer", collection_item.title)

        try:
            published_item = collection_item.publish()
            logger.info(
                "Imagery layer published: %s (url=%s)",
                published_item.title, published_item.url,
            )
            return published_item
        except Exception as e:
            raise ServicePublisherError(
                f"Failed to publish imagery layer: {e}"
            ) from e

    def refresh_service(self, service_item) -> bool:
        """
        Refresh an existing imagery layer to pick up newly added rasters.

        After rasters are added to the underlying image collection, the
        imagery layer service needs to be refreshed so the changes are
        reflected in the published service.

        Args:
            service_item: The portal Item for the existing imagery layer.

        Returns:
            True if refresh succeeded.

        Raises:
            ServicePublisherError: If refresh fails.
        """
        logger.info("Refreshing imagery layer '%s'", service_item.title)

        try:
            imagery_layer = ImageryLayer(service_item.url, gis=self._gis)
            # Refresh the service to pick up new rasters
            result = imagery_layer.refresh_service()
            logger.info("Imagery layer refreshed successfully")
            return result
        except Exception as e:
            raise ServicePublisherError(
                f"Failed to refresh imagery layer: {e}"
            ) from e

    def ensure_published(self, collection_item) -> dict:
        """
        Ensure the image collection is published as an imagery layer.

        If an imagery layer already exists, refresh it. Otherwise, publish
        a new one from the collection.

        Args:
            collection_item: The portal Item for the image collection.

        Returns:
            The imagery layer portal Item (existing or newly published).
        """
        existing_service = self.find_service()

        if existing_service:
            self.refresh_service(existing_service)
            return existing_service
        else:
            return self.publish_service(collection_item)
