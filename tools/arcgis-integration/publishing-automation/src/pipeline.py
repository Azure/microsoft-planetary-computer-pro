"""
Pipeline orchestrator for the ArcGIS Publishing Automation.

Coordinates the full workflow: STAC query → diff against existing items →
add new rasters to image collection → publish/refresh imagery layer.
"""

import logging
from dataclasses import dataclass
from typing import Optional

from .config import PipelineConfig
from .imagery_manager import ImageryManager
from .service_publisher import ServicePublisher
from .stac_client import StacClient

logger = logging.getLogger(__name__)


@dataclass
class PipelineResult:
    """Results from a pipeline execution."""
    items_discovered: int = 0
    items_new: int = 0
    items_skipped: int = 0
    items_added: int = 0
    collection_created: bool = False
    service_published: bool = False
    service_refreshed: bool = False
    service_url: Optional[str] = None
    error: Optional[str] = None

    @property
    def success(self) -> bool:
        return self.error is None


def run(config: PipelineConfig, dry_run: bool = False) -> PipelineResult:
    """
    Execute the publishing automation pipeline.

    Steps:
        1. Query MPC Pro GeoCatalog for STAC items matching the configuration.
        2. Connect to ArcGIS Enterprise and find or create the image collection.
        3. Query the image collection for already-ingested items.
        4. Compute the set of truly new items (STAC results - existing items).
        5. Add new rasters to the image collection (mapped to cloud store paths).
        6. Publish or refresh the imagery layer on ArcGIS Image Server.

    Args:
        config: Validated pipeline configuration.
        dry_run: If True, query and report but do not modify anything.

    Returns:
        PipelineResult with counts and status information.
    """
    result = PipelineResult()

    # ---- Step 1: STAC Query ----
    logger.info("=" * 60)
    logger.info("Step 1: Querying MPC Pro GeoCatalog")
    logger.info("=" * 60)

    try:
        stac_client = StacClient(config.geocatalog)
        stac_items = stac_client.search(
            config.stac_query,
            source_asset_key=config.image_collection.source_asset_key,
        )
        result.items_discovered = len(stac_items)
        logger.info("Discovered %d STAC items", result.items_discovered)
    except Exception as e:
        result.error = f"STAC query failed: {e}"
        logger.error(result.error)
        return result
    finally:
        stac_client.close()

    if result.items_discovered == 0:
        logger.info("No items found matching the query. Nothing to do.")
        return result

    # ---- Step 2: Connect to ArcGIS Enterprise ----
    logger.info("=" * 60)
    logger.info("Step 2: Connecting to ArcGIS Enterprise")
    logger.info("=" * 60)

    try:
        imagery_mgr = ImageryManager(
            enterprise_config=config.arcgis_enterprise,
            cloud_store_config=config.cloud_store,
            image_collection_config=config.image_collection,
        )
    except Exception as e:
        result.error = f"ArcGIS Enterprise connection failed: {e}"
        logger.error(result.error)
        return result

    # ---- Step 3: Find or create the image collection ----
    logger.info("=" * 60)
    logger.info("Step 3: Finding or creating image collection")
    logger.info("=" * 60)

    collection_item = imagery_mgr.find_image_collection()

    if collection_item is None:
        if not config.image_collection.create_if_missing:
            result.error = (
                f"Image collection '{config.image_collection.name}' not found "
                f"and create_if_missing is False"
            )
            logger.error(result.error)
            return result

        # We'll create the collection with the first batch of items
        existing_ids: set[str] = set()
        logger.info("Image collection will be created with initial rasters")
    else:
        # ---- Step 3b: Query existing items for deduplication ----
        existing_ids = imagery_mgr.get_existing_item_ids(collection_item)

    # ---- Step 4: Compute new items ----
    logger.info("=" * 60)
    logger.info("Step 4: Computing new items to add")
    logger.info("=" * 60)

    cloud_paths, item_ids, new_items = imagery_mgr.prepare_new_items(
        stac_items, existing_ids
    )
    result.items_new = len(new_items)
    result.items_skipped = result.items_discovered - result.items_new

    logger.info(
        "New: %d | Already in collection: %d | Total discovered: %d",
        result.items_new, result.items_skipped, result.items_discovered,
    )

    if result.items_new == 0:
        logger.info("No new items to add. Pipeline complete.")
        return result

    # ---- Dry run check ----
    if dry_run:
        logger.info("=" * 60)
        logger.info("DRY RUN: Would add the following %d items:", result.items_new)
        logger.info("=" * 60)
        for item, path in zip(new_items, cloud_paths):
            logger.info(
                "  %s (%s) → %s", item.item_id, item.collection, path
            )
        return result

    # ---- Step 5: Add rasters to image collection ----
    logger.info("=" * 60)
    logger.info("Step 5: Adding %d new rasters to image collection", result.items_new)
    logger.info("=" * 60)

    try:
        if collection_item is None:
            # Create new collection with initial rasters
            collection_item = imagery_mgr.create_collection(cloud_paths)
            result.collection_created = True
            result.items_added = len(cloud_paths)
        else:
            # Add rasters to existing collection
            imagery_mgr.add_rasters(collection_item, cloud_paths, item_ids)
            result.items_added = len(cloud_paths)
    except Exception as e:
        result.error = f"Failed to add rasters: {e}"
        logger.error(result.error)
        return result

    # ---- Step 6: Publish or refresh imagery layer ----
    logger.info("=" * 60)
    logger.info("Step 6: Publishing / refreshing imagery layer")
    logger.info("=" * 60)

    try:
        publisher = ServicePublisher(imagery_mgr.gis, config.image_collection)
        service_item = publisher.ensure_published(collection_item)

        if result.collection_created:
            result.service_published = True
        else:
            result.service_refreshed = True

        result.service_url = getattr(service_item, "url", None)
    except Exception as e:
        result.error = f"Service publishing failed: {e}"
        logger.error(result.error)
        return result

    # ---- Summary ----
    logger.info("=" * 60)
    logger.info("Pipeline Complete")
    logger.info("=" * 60)
    logger.info("  Items discovered:  %d", result.items_discovered)
    logger.info("  Items new:         %d", result.items_new)
    logger.info("  Items skipped:     %d", result.items_skipped)
    logger.info("  Items added:       %d", result.items_added)
    logger.info("  Collection created: %s", result.collection_created)
    logger.info("  Service published:  %s", result.service_published)
    logger.info("  Service refreshed:  %s", result.service_refreshed)
    if result.service_url:
        logger.info("  Service URL:       %s", result.service_url)

    return result
