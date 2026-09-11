"""
geoai.core.imagery.fetcher

ImageFetcher - Download and read imagery from STAC items.
"""

import logging
from typing import Any, Dict, List, Optional

import geopandas as gpd
import httpx
import numpy as np
import rasterio
from rasterio.io import MemoryFile
from rasterio.mask import mask as rasterio_mask
from rasterio.merge import merge as rasterio_merge
from rasterio.warp import Resampling, calculate_default_transform, reproject
from shapely.geometry import mapping, shape

from geoai.shared.url_utils import is_trusted_domain

logger = logging.getLogger(__name__)


class ImageFetcher:
    """
    ImageFetcher - Download and read imagery from STAC item assets.

    Handles:
    - COG (Cloud-Optimized GeoTIFF) downloads
    - Planetary Computer signing
    - Partial reads (windowed reads for chips)
    - Multi-band imagery
    """

    def __init__(self, timeout: int = 60):
        """
        Initialize ImageFetcher.

        :param timeout: HTTP timeout in seconds
        """
        self.timeout = timeout
        self._http_client = None

    def _get_http_client(self):
        """Get or create HTTP client (lazy initialization)"""
        if self._http_client is None:
            self._http_client = httpx.AsyncClient(timeout=self.timeout)
        return self._http_client

    async def fetch_image(
        self,
        stac_item: Any,
        chip_geometry: Dict,
        required_bands: List[str],
        use_pc_signing: bool = True,
        stac_items: Optional[List[Any]] = None,
    ) -> Dict[str, Any]:
        """
        Fetch imagery for a chip from one or more STAC items.
        When multiple items are provided, merges them to handle tile boundaries.

        :param stac_item: PySTAC Item object (primary item, for backward compatibility)
        :param chip_geometry: GeoJSON geometry defining the chip bounds
        :param required_bands: List of required bands (e.g., ["red", "green", "blue"])
        :param use_pc_signing: Whether to sign Planetary Computer URLs
        :param stac_items: Optional list of all intersecting STAC items (for multi-tile merging)
        :return: Dict with arrays, transform, crs, etc.
        """
        # Use multi-tile approach if multiple items provided
        if stac_items and len(stac_items) > 1:
            logger.debug(f"Multi-tile fetch: merging {len(stac_items)} STAC items for chip")
            return await self._fetch_and_merge_multiple_items(
                stac_items, chip_geometry, required_bands, use_pc_signing
            )

        # Single-item approach (original behavior)
        try:
            # Sign URLs if using Planetary Computer
            if use_pc_signing and is_trusted_domain(
                str(stac_item.get_self_href()), ["planetarycomputer.microsoft.com"]
            ):
                try:
                    import planetary_computer

                    stac_item = planetary_computer.sign(stac_item)
                    logger.debug(f"Signed Planetary Computer STAC item: {stac_item.id}")
                except ImportError:
                    logger.warning("planetary-computer package not installed, URLs not signed")

            # Read imagery for each band
            band_arrays = {}
            reference_transform = None
            reference_crs = None
            reference_shape = None

            chip_shape = shape(chip_geometry)

            # NAIP uses "image" asset with 4 bands (RGBN)
            if "image" in stac_item.assets and required_bands == ["red", "green", "blue"]:
                # Handle NAIP 4-band image
                asset = stac_item.assets["image"]
                asset_href = asset.href

                logger.debug(f"Reading NAIP 4-band image from {asset_href}")

                # Process with proper CRS handling (same as inference service)
                clipped_data, meta = self._process_raster_with_crs_handling(
                    asset_href, chip_shape, stac_item.id
                )

                if clipped_data is not None:
                    # NAIP bands: [R, G, B, NIR] - extract RGB
                    # clipped_data shape is (bands, height, width)
                    if clipped_data.shape[0] >= 3:
                        # Extract individual 2D arrays for each band
                        band_arrays["red"] = clipped_data[0]
                        band_arrays["green"] = clipped_data[1]
                        band_arrays["blue"] = clipped_data[2]

                        reference_transform = meta["transform"]
                        reference_crs = meta["crs"]
                        reference_shape = clipped_data.shape
            else:
                # Handle other collections with separate band assets
                for band_name in required_bands:
                    if band_name not in stac_item.assets:
                        logger.warning(f"Band {band_name} not found in STAC item {stac_item.id}")
                        continue

                    asset = stac_item.assets[band_name]
                    asset_href = asset.href

                    logger.debug(f"Reading band {band_name} from {asset_href}")

                    # Process with proper CRS handling
                    clipped_data, meta = self._process_raster_with_crs_handling(
                        asset_href, chip_shape, stac_item.id
                    )

                    if clipped_data is not None:
                        # Store reference info from first band
                        if reference_transform is None:
                            reference_transform = meta["transform"]
                            reference_crs = meta["crs"]
                            reference_shape = clipped_data.shape

                        # Remove extra dimension if present (single band becomes 2D)
                        if clipped_data.ndim == 3 and clipped_data.shape[0] == 1:
                            clipped_data = clipped_data[0]

                        band_arrays[band_name] = clipped_data

            if not band_arrays:
                raise ValueError(f"No bands fetched from STAC item {stac_item.id}")

            logger.debug(
                f"Fetched {len(band_arrays)} bands from STAC item {stac_item.id}, "
                f"shape={reference_shape}"
            )

            return {
                "arrays": band_arrays,
                "transform": reference_transform,
                "crs": reference_crs,
                "shape": reference_shape,
                "stac_item_id": stac_item.id,
            }

        except Exception as e:
            logger.error(f"Failed to fetch imagery from STAC item {stac_item.id}: {e}")
            raise

    async def _fetch_and_merge_multiple_items(
        self,
        stac_items: List[Any],
        chip_geometry: Dict,
        required_bands: List[str],
        use_pc_signing: bool,
    ) -> Dict[str, Any]:
        """
        Fetch imagery from multiple STAC items and merge using rasterio.merge().
        This handles chips that span NAIP tile boundaries.

        :param stac_items: List of STAC items that intersect the chip
        :param chip_geometry: GeoJSON geometry defining the chip bounds
        :param required_bands: List of required bands
        :param use_pc_signing: Whether to sign Planetary Computer URLs
        :return: Dict with merged arrays, transform, crs, etc.
        """
        try:
            chip_shape = shape(chip_geometry)

            # Step 1: Sign all items if needed
            signed_items = []
            for item in stac_items:
                if use_pc_signing and is_trusted_domain(
                    str(item.get_self_href()), ["planetarycomputer.microsoft.com"]
                ):
                    try:
                        import planetary_computer

                        item = planetary_computer.sign(item)
                    except ImportError:
                        pass
                signed_items.append(item)

            logger.debug(
                f"Processing {len(signed_items)} STAC items: {[item.id for item in signed_items]}"
            )

            # Step 2: Process each item to get partial imagery
            item_datasets = []  # Will hold MemoryFile datasets for merging
            temp_memfiles = []  # Keep MemoryFiles alive

            for item in signed_items:
                logger.debug(f"Processing STAC item {item.id}")

                # NAIP uses "image" asset with 4 bands (RGBN)
                if "image" in item.assets and required_bands == ["red", "green", "blue"]:
                    asset = item.assets["image"]
                    asset_href = asset.href

                    # Process with CRS handling
                    clipped_data, meta = self._process_raster_with_crs_handling(
                        asset_href, chip_shape, item.id
                    )

                    if clipped_data is not None and clipped_data.shape[0] >= 3:
                        # Extract RGB bands (3 bands, not 4)
                        rgb_data = clipped_data[:3]  # Take R, G, B only

                        # Create in-memory dataset for merging
                        memfile = MemoryFile()
                        temp_memfiles.append(memfile)

                        with memfile.open(
                            driver="GTiff",
                            height=rgb_data.shape[1],
                            width=rgb_data.shape[2],
                            count=3,
                            dtype=rgb_data.dtype,
                            crs=meta["crs"],
                            transform=meta["transform"],
                        ) as dataset:
                            dataset.write(rgb_data)

                        # Open for reading and add to list
                        reader = memfile.open()
                        item_datasets.append(reader)
                        logger.debug(f"Added {item.id}: shape={rgb_data.shape}")

            if not item_datasets:
                raise ValueError(f"No valid imagery fetched from {len(signed_items)} STAC items")

            # Step 3: Merge using rasterio.merge() (same as AI Workflow)
            logger.debug(f"Merging {len(item_datasets)} datasets...")
            merged_array, merged_transform = rasterio_merge(item_datasets, nodata=0)

            # Get CRS from first dataset
            reference_crs = item_datasets[0].crs

            # Step 4: Crop merged result to exact chip geometry
            # Convert chip geometry to Web Mercator (same CRS as merged result)
            chip_shape_web_mercator = (
                gpd.GeoSeries([chip_shape], crs="EPSG:4326").to_crs(reference_crs).iloc[0]
            )

            with MemoryFile() as merged_memfile:
                with merged_memfile.open(
                    driver="GTiff",
                    height=merged_array.shape[1],
                    width=merged_array.shape[2],
                    count=merged_array.shape[0],
                    dtype=merged_array.dtype,
                    crs=reference_crs,
                    transform=merged_transform,
                ) as merged_dataset:
                    merged_dataset.write(merged_array)

                # Crop to exact chip bounds (now in matching CRS)
                # all_touched=True ensures edge pixels are included, preventing black borders
                with merged_memfile.open() as src:
                    cropped_image, cropped_transform = rasterio_mask(
                        src,
                        [mapping(chip_shape_web_mercator)],
                        crop=True,
                        filled=True,
                        nodata=0,
                        all_touched=True,
                    )

            # Step 5: Extract individual bands
            band_arrays = {
                "red": cropped_image[0],
                "green": cropped_image[1],
                "blue": cropped_image[2],
            }

            # Cleanup
            for ds in item_datasets:
                try:
                    ds.close()
                except:
                    pass
            for mf in temp_memfiles:
                try:
                    mf.close()
                except:
                    pass

            logger.debug(
                f"Successfully merged {len(signed_items)} items → final shape={cropped_image.shape}"
            )

            return {
                "arrays": band_arrays,
                "transform": cropped_transform,
                "crs": reference_crs,
                "shape": cropped_image.shape,
                "stac_item_id": f"merged_{len(signed_items)}_items",
            }

        except Exception as e:
            logger.error(f"Failed to fetch and merge multiple STAC items: {e}")
            raise

    def _process_raster_with_crs_handling(
        self, asset_href: str, chip_geom_wgs84: Any, item_id: str
    ) -> tuple[Optional[np.ndarray], Optional[Dict]]:
        """
        Process raster with proper CRS handling and buffering.

        This implements the same logic as the production inference service:
        1. Transform chip geometry from WGS84 to Web Mercator
        2. Buffer the geometry to handle edge cases
        3. Reproject to source CRS and download buffered area
        4. Reproject back to Web Mercator
        5. Crop to exact chip geometry

        :param asset_href: URL to the raster asset
        :param chip_geom_wgs84: Chip geometry in WGS84 (shapely geometry)
        :param item_id: STAC item ID for logging
        :return: Tuple of (array, metadata) or (None, None) on failure
        """
        try:
            logger.debug(f"Processing raster with CRS handling: {asset_href}")

            with rasterio.open(asset_href) as src:
                # Extract source metadata
                src_resolution = abs(src.transform.a)
                src_crs = src.crs

                # Always use Web Mercator (EPSG:3857) for processing
                # This matches the coordinate system used in ChipMaker
                target_crs = "EPSG:3857"

                # Transform chip geometry from WGS84 to Web Mercator
                chip_geom_web_mercator = (
                    gpd.GeoSeries([chip_geom_wgs84], crs="EPSG:4326").to_crs(target_crs).iloc[0]
                )

                # Buffer the patch geometry to ensure full coverage
                # Use 100 pixels worth of buffer to handle pixel misalignment
                buffer_distance = src_resolution * 100
                buffered_chip = chip_geom_web_mercator.buffer(buffer_distance)

                # Reproject geometries to source CRS for masking
                chip_geom_src_crs = (
                    gpd.GeoSeries([chip_geom_web_mercator], crs=target_crs).to_crs(src.crs).iloc[0]
                )
                buffered_chip_src_crs = (
                    gpd.GeoSeries([buffered_chip], crs=target_crs).to_crs(src.crs).iloc[0]
                )

                # Download imagery for the buffered area (in source CRS)
                # all_touched=True ensures edge pixels are included, preventing black borders
                buffered_image, buffered_transform = rasterio_mask(
                    src,
                    [mapping(buffered_chip_src_crs)],
                    crop=True,
                    filled=True,
                    nodata=0,
                    all_touched=True,
                )

                # Create metadata for buffered image
                buffered_meta = src.meta.copy()
                buffered_meta.update(
                    {
                        "driver": "GTiff",
                        "height": buffered_image.shape[1],
                        "width": buffered_image.shape[2],
                        "transform": buffered_transform,
                        "crs": src.crs,
                    }
                )

                # Reproject buffered image to Web Mercator
                with MemoryFile() as temp_memfile:
                    with temp_memfile.open(**buffered_meta) as temp_dataset:
                        temp_dataset.write(buffered_image)

                    # Calculate destination transform and dimensions
                    dst_transform, dst_width, dst_height = calculate_default_transform(
                        src.crs,
                        target_crs,
                        buffered_image.shape[2],
                        buffered_image.shape[1],
                        *temp_dataset.bounds,
                    )

                    # Create reprojected array
                    reprojected_array = np.zeros(
                        (buffered_image.shape[0], dst_height, dst_width), dtype=buffered_image.dtype
                    )

                    # Reproject to Web Mercator
                    reproject(
                        source=buffered_image,
                        destination=reprojected_array,
                        src_transform=buffered_transform,
                        src_crs=src.crs,
                        dst_transform=dst_transform,
                        dst_crs=target_crs,
                        resampling=Resampling.bilinear,
                    )

                    # Create metadata for reprojected image
                    reprojected_meta = buffered_meta.copy()
                    reprojected_meta.update(
                        {
                            "driver": "GTiff",
                            "crs": target_crs,
                            "transform": dst_transform,
                            "width": dst_width,
                            "height": dst_height,
                        }
                    )

                    # Crop to exact chip geometry from reprojected image
                    with MemoryFile() as reprojected_memfile:
                        with reprojected_memfile.open(**reprojected_meta) as reprojected_dataset:
                            reprojected_dataset.write(reprojected_array)

                        # Final crop to exact chip geometry (in Web Mercator)
                        # all_touched=True ensures edge pixels are included, preventing black borders
                        with reprojected_memfile.open() as reprojected_src:
                            out_image, out_transform = rasterio_mask(
                                reprojected_src,
                                [mapping(chip_geom_web_mercator)],
                                crop=True,
                                filled=True,
                                nodata=0,
                                all_touched=True,
                            )

                # Calculate actual resolution in meters (now in Web Mercator)
                resolution_meters = abs(out_transform.a)

                meta = {
                    "driver": "GTiff",
                    "count": out_image.shape[0],
                    "height": out_image.shape[1],
                    "width": out_image.shape[2],
                    "transform": out_transform,
                    "crs": target_crs,  # All outputs in Web Mercator
                    "dtype": out_image.dtype,
                    "source_resolution": resolution_meters,
                }

                logger.debug(
                    f"Successfully processed raster for {item_id}: "
                    f"shape={out_image.shape}, resolution={resolution_meters:.2f}m"
                )

                return out_image, meta

        except Exception as e:
            logger.error(f"Failed to process raster for {item_id}: {e}")
            return None, None

    async def close(self):
        """Close HTTP client"""
        if self._http_client:
            await self._http_client.aclose()
