"""
geoai.core.spatial.chipmaker

ChipMaker - Divide AOI into chips/patches for processing.
"""

import logging
import math
from typing import Dict, List

import geopandas as gpd
from shapely.geometry import box, mapping, shape

logger = logging.getLogger(__name__)


class ChipMaker:
    """
    ChipMaker - Divide AOI into chips/patches using Web Mercator projection.

    Extracted from AI Workflow patch-sampler service.

    The chip maker:
    1. Projects AOI geometry from WGS84 to Web Mercator (EPSG:3857)
    2. Creates a regular grid of chips with specified size and stride
    3. Converts chip geometries back to WGS84
    4. Returns list of chip dictionaries with metadata

    Example:
        >>> chipmaker = ChipMaker(chip_size=512, stride=256)
        >>> chips = chipmaker.create_chips(aoi_geometry)
        >>> print(f"Created {len(chips)} chips")
    """

    def __init__(self, chip_size: float = 512, stride: float = 256):
        """
        Initialize ChipMaker.

        :param chip_size: Chip size in meters (default: 512m)
        :param stride: Stride in meters (default: 256m for 50% overlap)
        """
        self.chip_size = chip_size
        self.stride = stride

    def create_chips(self, aoi_geometry: Dict, crs: str = "EPSG:4326") -> List[Dict]:
        """
        Divide AOI into chips using Web Mercator projection.

        Returns list of chip geometries with metadata:
        [
            {
                "chip_id": "chip_0_0",
                "geometry": {...},  # WGS84 GeoJSON
                "bounds": [minx, miny, maxx, maxy],
                "grid_position": {"x": 0, "y": 0},
                "index": 0
            },
            ...
        ]

        :param aoi_geometry: AOI geometry in GeoJSON format
        :param crs: Input CRS (default: EPSG:4326)
        :return: List of chip dictionaries
        """
        # Convert GeoJSON to shapely geometry
        aoi_geom = shape(aoi_geometry)

        # Create GeoDataFrame with original geometry
        aoi_gdf = gpd.GeoDataFrame(geometry=[aoi_geom], crs=crs)

        # Log original bounds
        orig_bounds = aoi_geom.bounds
        logger.info(
            f"Creating chips for AOI: bounds={orig_bounds}, "
            f"chip_size={self.chip_size}m, stride={self.stride}m"
        )

        # Project to Web Mercator for accurate distance-based gridding
        aoi_projected = aoi_gdf.to_crs("EPSG:3857").geometry.iloc[0]
        minx, miny, maxx, maxy = aoi_projected.bounds

        # Calculate grid dimensions - ensure at least 1 chip even if AOI is smaller than chip size
        x_steps = max(1, math.ceil((maxx - minx - self.chip_size) / self.stride) + 1)
        y_steps = max(1, math.ceil((maxy - miny - self.chip_size) / self.stride) + 1)

        total_patches = x_steps * y_steps
        bbox_width_km = (maxx - minx) / 1000
        bbox_height_km = (maxy - miny) / 1000

        logger.info(
            f"Chip grid: {x_steps} x {y_steps} = {total_patches} chips, "
            f"AOI size: {bbox_width_km:.2f} x {bbox_height_km:.2f} km"
        )

        # Generate all chip geometries in Web Mercator
        patch_geoms = []
        chip_list = []

        for i in range(x_steps):
            for j in range(y_steps):
                patch_minx = minx + i * self.stride
                patch_miny = miny + j * self.stride
                patch_maxx = patch_minx + self.chip_size
                patch_maxy = patch_miny + self.chip_size

                patch_geom = box(patch_minx, patch_miny, patch_maxx, patch_maxy)
                patch_geoms.append(patch_geom)

        # Convert all patches back to WGS84
        patch_gdf = gpd.GeoDataFrame(geometry=patch_geoms, crs="EPSG:3857").to_crs("EPSG:4326")

        # Build output list with metadata
        index = 0
        for i in range(x_steps):
            for j in range(y_steps):
                geom_wgs84 = patch_gdf.geometry.iloc[index]
                chip_dict = {
                    "chip_id": f"chip_{i}_{j}",
                    "geometry": mapping(geom_wgs84),  # GeoJSON format
                    "bounds": list(geom_wgs84.bounds),
                    "grid_position": {"x": i, "y": j},
                    "index": index,
                }
                chip_list.append(chip_dict)
                index += 1

        logger.info(f"Created {len(chip_list)} chips successfully")

        return chip_list
