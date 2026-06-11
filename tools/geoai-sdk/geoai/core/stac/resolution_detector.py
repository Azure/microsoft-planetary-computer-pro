"""
geoai.core.stac.resolution_detector

ResolutionDetector - Detect spatial resolution from STAC items.
"""

import logging
from typing import Any, List, Optional

logger = logging.getLogger(__name__)


def detect_resolution(stac_items: List[Any], collection_name: Optional[str] = None) -> float:
    """
    Detect native resolution from STAC items.

    Resolution detection priority:
    1. Item-level gsd property (STAC standard)
    2. Asset-level gsd (some catalogs store here)
    3. Collection-level defaults (fallback)
    4. Global default (0.6m for NAIP)

    :param stac_items: List of STAC items (pystac Item objects or dicts)
    :param collection_name: Optional collection name for fallback defaults
    :return: Resolution in meters per pixel

    Example:
        >>> from geoai.core.stac.resolution_detector import detect_resolution
        >>> resolution = detect_resolution(stac_items, collection_name="naip")
        >>> print(f"Detected resolution: {resolution}m/pixel")
    """
    if not stac_items:
        logger.info("No STAC items provided, using default resolution: 0.6m/pixel")
        return 0.6

    # Sort items by datetime (newest first) for consistent resolution detection
    try:
        sorted_items = sorted(
            stac_items,
            key=lambda item: (
                item.properties.get("datetime", "")
                if hasattr(item, "properties")
                else item.get("properties", {}).get("datetime", "")
            ),
            reverse=True,
        )
        first_item = sorted_items[0]
        logger.info(
            f"Sorted {len(stac_items)} STAC items by date, using newest for resolution detection"
        )
    except Exception as e:
        logger.warning(f"Failed to sort STAC items by date: {e}, using first item")
        first_item = stac_items[0]

    try:
        # Method 1: Item-level gsd property (pystac Item)
        if hasattr(first_item, "properties"):
            gsd = first_item.properties.get("gsd")
            if gsd:
                logger.info(f"Detected resolution from item.properties.gsd: {gsd}m/pixel")
                return float(gsd)

            # Method 2: Asset-level gsd (some catalogs)
            if hasattr(first_item, "assets") and first_item.assets:
                for asset_key, asset in first_item.assets.items():
                    if hasattr(asset, "extra_fields") and "gsd" in asset.extra_fields:
                        gsd = asset.extra_fields["gsd"]
                        logger.info(
                            f"Detected resolution from asset '{asset_key}' gsd: {gsd}m/pixel"
                        )
                        return float(gsd)

        # Method 1b: Item-level gsd property (dict)
        elif isinstance(first_item, dict):
            gsd = first_item.get("properties", {}).get("gsd")
            if gsd:
                logger.info(f"Detected resolution from item dict gsd: {gsd}m/pixel")
                return float(gsd)

        # Method 3: Collection-level defaults
        if collection_name:
            collection_defaults = {
                "naip": 0.6,
                "sentinel-2-l2a": 10.0,
                "sentinel-1-grd": 10.0,
                "landsat-c2-l2": 30.0,
            }
            if collection_name.lower() in collection_defaults:
                gsd = collection_defaults[collection_name.lower()]
                logger.info(
                    f"Using collection default resolution for '{collection_name}': {gsd}m/pixel"
                )
                return float(gsd)

        # No gsd found
        logger.warning("No gsd property found in STAC item, using default: 0.6m/pixel")

    except Exception as e:
        logger.warning(f"Failed to detect resolution from STAC item: {e}")

    # Method 4: Global default (NAIP resolution)
    logger.info("Using default NAIP resolution: 0.6m/pixel")
    return 0.6
