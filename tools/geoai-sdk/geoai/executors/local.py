"""
geoai.executors.local

LocalExecutor - Sequential execution on a single machine with progress tracking.
"""

import json
import logging
import os
import shutil
import tempfile
import uuid
import warnings
from typing import Any, Dict, List, Optional

import httpx
import numpy as np
import rasterio
from rasterio.errors import NodataShadowWarning
from rasterio.transform import Affine
from tqdm import tqdm

# Suppress rasterio nodata shadow warnings
warnings.filterwarnings("ignore", category=NodataShadowWarning)
import geopandas as gpd
from azure.storage.blob import BlobServiceClient
from PIL import Image
from rasterio.crs import CRS
from shapely.geometry import box
from shapely.geometry import shape as shapely_shape

from geoai.core.imagery.fetcher import ImageFetcher
from geoai.core.imagery.preprocessor import ImagePreprocessor
from geoai.core.models.payload_builder import PayloadBuilder
from geoai.core.models.response_parser import ResponseParser
from geoai.core.results.detection_formatter import DetectionFormatter
from geoai.core.results.geocatalog_writer import GeoCatalogWriter
from geoai.core.results.imagery_merger import ImageryMerger
from geoai.core.spatial.chipmaker import ChipMaker
from geoai.core.spatial.detection_merger import DetectionMerger
from geoai.core.stac.resolution_detector import detect_resolution
from geoai.core.stac.searcher import STACSearcher
from geoai.executors.base import BaseExecutor

logger = logging.getLogger(__name__)


class LocalExecutor(BaseExecutor):
    """
    LocalExecutor - Execute models sequentially on a single machine.

    Used by SDK for local execution with progress bars (tqdm).
    Handles AOI-based workflows for EOOS and MARS models.
    """

    def __init__(self, max_workers: int = 4):
        """
        Initialize LocalExecutor.

        :param max_workers: Number of threads for IO-bound operations
        """
        self.max_workers = max_workers
        self._model_client_cache = None  # Cache ModelClient to avoid recreating per chip

    def _apply_imagenet_normalization(
        self, band_arrays: Dict[str, np.ndarray], target_mean: List[float], target_std: List[float]
    ) -> Dict[str, np.ndarray]:
        """
        Apply ImageNet-style color normalization via preprocessor.
        Delegates to ImagePreprocessor.apply_imagenet_normalization().

        :param band_arrays: Dict of band_name -> uint8 array [0, 255]
        :param target_mean: Target mean per channel [R, G, B]
        :param target_std: Target std per channel [R, G, B]
        :return: Normalized band arrays (still uint8 [0, 255])
        """
        # Delegate to preprocessor utility
        preprocessor = ImagePreprocessor()
        return preprocessor.apply_imagenet_normalization(band_arrays, target_mean, target_std)

    def _resize_imagery_and_scale_transform(
        self, image_data: Dict, target_size: tuple, preprocessing_config: Dict = None
    ) -> Dict:
        """
        Resize imagery to target dimensions and scale the transform accordingly.

        :param image_data: Dict with 'arrays', 'transform', 'crs', etc.
        :param target_size: (width, height) in pixels
        :param preprocessing_config: Optional preprocessing config from model spec
        :return: Updated image_data dict with resized arrays and scaled transform
        """
        arrays = image_data["arrays"]
        original_transform = image_data["transform"]

        # Get current dimensions from first band
        first_band = next(iter(arrays.values()))
        original_height, original_width = first_band.shape
        target_width, target_height = target_size

        # If already correct size, return as-is
        if original_width == target_width and original_height == target_height:
            return image_data

        logger.debug(
            f"Resizing imagery: {original_width}×{original_height} → {target_width}×{target_height}"
        )

        # Resize each band
        resized_arrays = {}
        for band_name, band_array in arrays.items():
            # Store original dtype to preserve it
            original_dtype = band_array.dtype
            band_min = band_array.min()
            band_max = band_array.max()
            logger.debug(
                f"  Band {band_name}: dtype={original_dtype}, range=[{band_min:.2f}, {band_max:.2f}]"
            )

            # Normalize to uint8 for PIL resizing (PIL expects 0-255 range)
            # Use min-max normalization like AI Workflow to handle varying data ranges
            if band_array.dtype == np.uint8:
                # Already uint8, use as-is
                band_normalized = band_array
                logger.debug(f"  → Band {band_name}: already uint8, no normalization needed")
            elif band_array.dtype in [np.float32, np.float64]:
                # Float: use min-max normalization to handle any range (not just 0-1)
                if band_max > band_min:
                    band_normalized = (
                        (band_array - band_min) / (band_max - band_min) * 255.0
                    ).astype(np.uint8)
                    logger.debug(
                        f"  → Band {band_name}: float normalized from [{band_min:.2f}, {band_max:.2f}] → [0, 255]"
                    )
                else:
                    band_normalized = np.zeros_like(band_array, dtype=np.uint8)
                    logger.debug(f"  → Band {band_name}: float constant value, set to zeros")
            elif band_array.dtype == np.uint16:
                # uint16: use min-max normalization (NAIP typically uses 0-2000, not full 0-65535 range)
                # This matches AI Workflow's approach and prevents dark/black imagery
                if band_max > band_min:
                    band_normalized = (
                        (band_array - band_min) / (band_max - band_min) * 255.0
                    ).astype(np.uint8)
                    logger.debug(
                        f"  → Band {band_name}: uint16 normalized from [{band_min:.0f}, {band_max:.0f}] → [0, 255]"
                    )
                else:
                    band_normalized = np.zeros_like(band_array, dtype=np.uint8)
                    logger.debug(f"  → Band {band_name}: uint16 constant value, set to zeros")
            else:
                # Other integer types: use min-max normalization
                if band_max > band_min:
                    band_normalized = (
                        (band_array - band_min) / (band_max - band_min) * 255.0
                    ).astype(np.uint8)
                    logger.debug(
                        f"  → Band {band_name}: {original_dtype} normalized from [{band_min:.2f}, {band_max:.2f}] → [0, 255]"
                    )
                else:
                    band_normalized = np.clip(band_array, 0, 255).astype(np.uint8)
                    logger.debug(f"  → Band {band_name}: {original_dtype} clipped to [0, 255]")

            # Resize using PIL
            pil_img = Image.fromarray(band_normalized)
            pil_resized = pil_img.resize((target_width, target_height), Image.BILINEAR)
            resized_array = np.array(pil_resized)

            # Keep as uint8 (we've already normalized to 0-255 for all dtype)
            # This ensures consistent format for model inference and saving
            resized_arrays[band_name] = resized_array.astype(np.uint8)

        # Apply domain-specific color normalization if requested (e.g., ImageNet for EOOS)
        if preprocessing_config and preprocessing_config.get("color_normalization") == "imagenet":
            logger.debug("Applying ImageNet color normalization for domain adaptation")
            resized_arrays = self._apply_imagenet_normalization(
                resized_arrays,
                target_mean=preprocessing_config.get("target_mean_rgb", [123.675, 116.28, 103.53]),
                target_std=preprocessing_config.get("target_std_rgb", [58.395, 57.12, 57.375]),
            )

        # Scale the transform
        # Original transform maps original_width × original_height pixels to meters
        # New transform must map target_width × target_height pixels to the SAME meters
        # So pixel size changes: scale_factor = original_size / target_size

        scale_x = original_width / target_width
        scale_y = original_height / target_height

        # Affine transform: [pixel_width, 0, x_offset, 0, -pixel_height, y_offset]
        # Scale the pixel sizes
        scaled_transform = Affine(
            original_transform.a * scale_x,  # pixel width (scaled)
            original_transform.b,
            original_transform.c,  # x offset (same)
            original_transform.d,
            original_transform.e * scale_y,  # pixel height (scaled, usually negative)
            original_transform.f,  # y offset (same)
        )

        logger.debug(
            f"Scaled transform: pixel_size {original_transform.a:.4f}m → {scaled_transform.a:.4f}m"
        )

        # Update image_data
        resized_image_data = image_data.copy()
        resized_image_data["arrays"] = resized_arrays
        resized_image_data["transform"] = scaled_transform

        return resized_image_data

    async def execute(self, workflow_type: str, **kwargs) -> Dict[str, Any]:
        """
        Execute model based on workflow type.

        :param workflow_type: 'aoi_based' - Only AOI-based workflows supported (EOOS, MARS)
        :param kwargs: Workflow-specific parameters
        :return: Execution result
        """
        if workflow_type == "aoi_based":
            # Check if multi-AOI mode
            constraint = kwargs.get("constraint")
            if constraint and hasattr(constraint, "mode") and constraint.mode == "multi":
                return await self._execute_multi_aoi(**kwargs)
            else:
                # Single AOI mode (original behavior)
                return await self._execute_aoi_workflow(**kwargs)
        else:
            raise ValueError(
                f"Unknown workflow type: {workflow_type}. Only 'aoi_based' is supported."
            )

    async def _execute_aoi_workflow(
        self,
        aoi_geometry: Dict,
        model_spec: Dict,
        input_config: Dict,
        constraint_config: Dict,
        output_config: Dict,
        params: Dict,
        stac_items_override: List = None,  # Pre-fetched STAC items for multi-AOI
        constraint=None,  # Passed but not used (multi-AOI uses it)
        defer_publishing: bool = False,  # Skip GeoCatalog publishing and return publication data
        aoi_bbox: Optional[List[float]] = None,  # Bounding box for faster STAC queries
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Execute AOI-based workflow (EO-OS, MARS).

        Steps:
        1. Create chips from AOI
        2. Search STAC for imagery
        3. Fetch & preprocess imagery for each chip
        4. Build payloads & call model endpoint
        5. Parse responses
        6. Merge results (NMS for detections, pixel voting for segmentation)
        7. Write to GeoCatalog (or save locally)

        :return: Result dictionary with merged detection/segmentation data
        """
        import asyncio
        import logging
        import os
        import tempfile
        import uuid

        import httpx
        import rasterio
        from azure.storage.blob.aio import BlobServiceClient
        from shapely.geometry import shape as shapely_shape

        logger = logging.getLogger(__name__)

        # Extract parameters (now in pixels) - read defaults from parameters section
        chip_size_pixels = params.get("chip_size", model_spec["parameters"]["chip_size"]["default"])
        stride_pixels = params.get("stride", model_spec["parameters"]["stride"]["default"])
        # Threshold is optional - not all models support it (e.g., MARS)
        if "threshold" in model_spec["parameters"]:
            threshold = params.get("threshold", model_spec["parameters"]["threshold"]["default"])
        # Note: threshold variable not used directly, only passed in params dict to payload builder

        required_bands = model_spec["data_requirements"]["required_bands"]
        model_name = output_config.get("model_name", model_spec.get("id", "unknown-model"))

        # Generate run_id if not provided (for organizing blob storage)
        run_id = output_config.get("run_id") or str(uuid.uuid4())

        # Step 0: Search STAC for imagery (do this ONCE and reuse for resolution detection)
        if stac_items_override:
            # Use pre-fetched STAC items (multi-AOI optimization)
            stac_items = stac_items_override
            print(f"[INFO] Using {len(stac_items)} pre-fetched STAC items")
        elif constraint_config.get("stac_search"):
            # STAC pass-through mode
            print(f"[INFO] Using pre-built STAC search (pass-through mode)...")
            searcher = STACSearcher(
                geocatalog_uri=input_config["geocatalog_uri"],
                collection=input_config["collection"],
                credential=input_config.get("credential"),
            )

            stac_items = await searcher.search_from_external(constraint_config["stac_search"])
            print(f"   Found {len(stac_items)} STAC items")
        else:
            # Search STAC catalog
            print(f"[INFO] Searching STAC catalog for imagery...")
            searcher = STACSearcher(
                geocatalog_uri=input_config["geocatalog_uri"],
                collection=input_config["collection"],
                credential=input_config.get("credential"),
            )

            # Use passed bbox or extract from geometry for faster query
            if aoi_bbox is None:
                if hasattr(aoi_geometry, "bounds"):
                    aoi_bbox = list(aoi_geometry.bounds)
                elif isinstance(aoi_geometry, dict) and "coordinates" in aoi_geometry:
                    from shapely.geometry import shape
                    geom = shape(aoi_geometry)
                    aoi_bbox = list(geom.bounds)

            stac_items = await searcher.search(
                geometry=aoi_geometry,
                bbox=aoi_bbox,
                datetime=constraint_config.get("datetime"),
                filter=constraint_config.get("filter"),
            )

            print(f"   Found {len(stac_items)} STAC items")

        # Step 1: Detect native resolution from STAC items (reuse items from Step 0)
        if stac_items:
            native_resolution = detect_resolution(stac_items, collection_name=input_config.get("collection"))
            print(f"   Native resolution: {native_resolution}m/pixel")
        else:
            logger.warning("No STAC items found, using default resolution 0.6m")
            native_resolution = 0.6
            print(f"   Native resolution: {native_resolution}m/pixel (default)")

        # Step 2: Convert chip size and stride from pixels to meters
        chip_size_meters = chip_size_pixels * native_resolution
        stride_meters = stride_pixels * native_resolution

        logger.info(
            f"Starting AOI workflow: chip_size={chip_size_pixels}px ({chip_size_meters:.1f}m), "
            f"stride={stride_pixels}px ({stride_meters:.1f}m), run_id={run_id}"
        )
        print(
            f"📐 Chip parameters: {chip_size_pixels}×{chip_size_pixels}px = {chip_size_meters:.1f}×{chip_size_meters:.1f}m"
        )

        # Initialize blob storage client (required for STAC assets)
        blob_service_client = None
        chip_blob_paths = {}  # Track blob paths for each chip

        storage_url = output_config.get("storage_url")
        blob_container = output_config.get("blob_container", "sdk-results")

        if storage_url:
            # Use credential from Output object (Azure AD), not endpoint_credential (API key)
            credential = output_config.get("credential")

            blob_service_client = BlobServiceClient(account_url=storage_url, credential=credential)
            logger.info(
                f"Blob storage enabled: {storage_url}/{blob_container}/{model_name}/{run_id}"
            )
        else:
            logger.warning("No blob storage configured - STAC item assets will not be available")

        # Step 3: Create chips from AOI (using converted meter values)
        print(
            f"🔲 Creating chips (size={chip_size_pixels}px / {chip_size_meters:.1f}m, stride={stride_pixels}px / {stride_meters:.1f}m)..."
        )
        chipmaker = ChipMaker(chip_size=chip_size_meters, stride=stride_meters)
        chips = chipmaker.create_chips(aoi_geometry)
        print(f"   Created {len(chips)} chips")

        if not stac_items:
            raise ValueError("No STAC items found for AOI and constraints")

        # Step 2b: Get ALL intersecting STAC items per chip (for multi-tile merging)
        print(f"📅 Finding intersecting STAC items for each chip...")
        chip_to_items_map = self._get_all_intersecting_items(chips, stac_items)

        if not chip_to_items_map:
            raise ValueError("No STAC items cover any chips")

        coverage_pct = (len(chip_to_items_map) / len(chips)) * 100
        total_items = sum(len(items) for items in chip_to_items_map.values())
        unique_items = len(set(item.id for items in chip_to_items_map.values() for item in items))
        print(f"   Found {unique_items} unique STAC items, {coverage_pct:.1f}% chip coverage")
        print(
            f"   Multi-tile merging: {sum(1 for items in chip_to_items_map.values() if len(items) > 1)} chips span tile boundaries"
        )

        # Extract concurrency limits from output_config (passed from model)
        inference_concurrent = output_config.get("max_concurrent_requests", 1)
        fetch_concurrent = output_config.get("fetch_concurrent", 4)
        logger.info(
            f"Using two-stage pipeline: {fetch_concurrent} fetch/preprocess, {inference_concurrent} inference"
        )

        # Create two semaphores for pipeline stages
        fetch_semaphore = asyncio.Semaphore(fetch_concurrent)
        inference_semaphore = asyncio.Semaphore(inference_concurrent)

        # Step 3-5: Process chips with two-stage pipeline
        print(
            f"⚙️  Processing {len(chip_to_items_map)} chips (fetch: {fetch_concurrent}, inference: {inference_concurrent})..."
        )
        fetcher = ImageFetcher()
        preprocessor = ImagePreprocessor()

        # Initialize ModelClient once (reused for all chips)
        from ..core.models.coordinate_converter import CoordinateConverter
        from ..core.models.model_client import ModelClient

        model_client = ModelClient(
            endpoint=output_config["endpoint"],
            credential=output_config.get("endpoint_credential"),
            model_spec=model_spec,
        )

        # Define async function to process a single chip with two-stage pipeline
        async def process_single_chip(chip):
            """
            Process one chip with two-stage pipeline:
            Stage 1 (fetch_semaphore): Fetch and preprocess imagery
            Stage 2 (inference_semaphore): Run model inference
            Stage 3 (no throttle): Convert coordinates
            """
            # Skip chips without STAC item assignment
            if chip["chip_id"] not in chip_to_items_map:
                logger.debug(f"Chip {chip['chip_id']} has no STAC items, skipping")
                return None

            try:
                matching_items = chip_to_items_map[chip["chip_id"]]

                # === STAGE 1: Fetch and Preprocess (throttled by fetch_semaphore) ===
                async with fetch_semaphore:
                    # Fetch imagery for chip (with multi-tile merging if needed)
                    image_data = await fetcher.fetch_image(
                        stac_item=matching_items[0],
                        chip_geometry=chip["geometry"],
                        required_bands=required_bands,
                        use_pc_signing=True,
                        stac_items=matching_items,
                    )

                    # Split preprocessing: create two versions of the imagery
                    # Version 1: Natural NAIP (NO color normalization) - for saving and visualization
                    # Version 2: ImageNet normalized - for model inference only
                    target_size = (chip_size_pixels, chip_size_pixels)
                    preprocessing_config = model_spec.get("preprocessing")

                    # Create natural version (without color normalization)
                    image_data_natural = self._resize_imagery_and_scale_transform(
                        image_data, target_size, preprocessing_config=None
                    )

                    # Create inference version (with color normalization if specified)
                    image_data_inference = self._resize_imagery_and_scale_transform(
                        image_data, target_size, preprocessing_config
                    )

                    # Save NATURAL imagery to blob (not the colorized version)
                    if blob_service_client:
                        chip_tif_path = await self._save_chip_to_blob(
                            blob_service_client=blob_service_client,
                            blob_container=blob_container,
                            model_name=model_name,
                            run_id=run_id,
                            chip_id=chip["chip_id"],
                            image_data=image_data_natural,  # Use natural, not normalized
                            required_bands=required_bands,
                        )

                        if chip_tif_path:
                            chip["tif_blob_path"] = chip_tif_path
                            chip_blob_paths[chip["chip_id"]] = chip_tif_path
                            logger.debug(f"Saved chip {chip['chip_id']} to blob: {chip_tif_path}")

                    # Preprocess INFERENCE version for model (with normalization)
                    preprocessed = preprocessor.preprocess(
                        image_data=image_data_inference,  # Use normalized for model
                        target_bands=required_bands,
                        target_size=params.get("target_size_pixels"),
                        normalization="0-255",
                        output_format="bytes",
                    )

                    # Get transform for coordinate conversion (use natural version for consistency)
                    chip_transform = image_data_natural.get("transform")
                    chip_crs = image_data_natural.get("crs")
                # fetch_semaphore released - next chip can start fetching

                # === STAGE 2: Inference (throttled by inference_semaphore) ===
                async with inference_semaphore:
                    logger.debug(
                        f"🔥 Chip {chip['chip_id']}: Acquired inference slot, sending to endpoint"
                    )

                    # Retry logic for transient errors (connection, timeout, rate limiting, server errors)
                    max_retries = 3
                    retry_delays = [2, 5, 10]  # Exponential backoff: 2s, 5s, 10s

                    for attempt in range(max_retries):
                        try:
                            # Infer on single image (endpoint saturated by semaphore limit)
                            raw_detections = await model_client.infer(
                                image=preprocessed, params=params
                            )
                            break  # Success - exit retry loop

                        except (httpx.ConnectError, httpx.TimeoutException) as e:
                            # Connection failures or timeouts (connect, read, write, pool)
                            error_type = type(e).__name__
                            if attempt < max_retries - 1:
                                delay = retry_delays[attempt]
                                logger.warning(
                                    f"[WARNING] Chip {chip['chip_id']}: {error_type} (attempt {attempt + 1}/{max_retries}), "
                                    f"retrying in {delay}s... Error: {str(e)}"
                                )
                                await asyncio.sleep(delay)
                            else:
                                # All retries exhausted
                                logger.error(
                                    f"[ERROR] Chip {chip['chip_id']}: {error_type} failed after {max_retries} attempts"
                                )
                                raise  # Re-raise the exception

                        except httpx.HTTPStatusError as e:
                            # HTTP error status codes - only retry transient server errors
                            status_code = e.response.status_code

                            # Retry on: 429 (rate limit), 502 (bad gateway), 503 (service unavailable), 504 (gateway timeout)
                            if status_code in [429, 502, 503, 504]:
                                if attempt < max_retries - 1:
                                    delay = retry_delays[attempt]
                                    logger.warning(
                                        f"[WARNING] Chip {chip['chip_id']}: HTTP {status_code} (attempt {attempt + 1}/{max_retries}), "
                                        f"retrying in {delay}s..."
                                    )
                                    await asyncio.sleep(delay)
                                else:
                                    # All retries exhausted
                                    logger.error(
                                        f"[ERROR] Chip {chip['chip_id']}: HTTP {status_code} failed after {max_retries} attempts"
                                    )
                                    raise
                            else:
                                # Client error (4xx except 429) or other server error - don't retry
                                logger.error(
                                    f"[ERROR] Chip {chip['chip_id']}: HTTP {status_code} (non-retryable) - {e.response.text[:200]}"
                                )
                                raise

                    logger.debug(f"[DEBUG] Chip {chip['chip_id']}: Released inference slot")
                # inference_semaphore released - next chip can start inference

                # === STAGE 3: Coordinate Conversion (no throttling) ===
                # Convert pixel coordinates to WGS84 and create GeoJSON features
                chip_features = []
                for detection in raw_detections:
                    # Handle two detection formats: bbox (EOOS) and geometry (MARS)
                    if "bbox" in detection:
                        # Bbox format (EOOS)
                        wgs84_coords = CoordinateConverter.pixel_to_wgs84(
                            pixel_bbox=detection["bbox"],
                            transform=chip_transform,
                            source_crs=chip_crs,
                        )

                        if wgs84_coords:
                            lon_min, lat_min, lon_max, lat_max = wgs84_coords

                            det_feature = {
                                "type": "Feature",
                                "geometry": {
                                    "type": "Polygon",
                                    "coordinates": [
                                        [
                                            [lon_min, lat_min],
                                            [lon_max, lat_min],
                                            [lon_max, lat_max],
                                            [lon_min, lat_max],
                                            [lon_min, lat_min],
                                        ]
                                    ],
                                },
                                "properties": {
                                    "score": detection["score"],
                                    "label": detection["label"],
                                    "chip_id": chip["chip_id"],
                                },
                            }
                            chip_features.append(det_feature)

                    elif "geometry" in detection:
                        # Geometry format (MARS)
                        wgs84_geometry = CoordinateConverter.geometry_to_wgs84(
                            geometry=detection["geometry"],
                            transform=chip_transform,
                            source_crs=chip_crs,
                        )

                        if wgs84_geometry:
                            det_feature = {
                                "type": "Feature",
                                "geometry": wgs84_geometry,
                                "properties": {
                                    "score": detection["score"],
                                    "label": detection["label"],
                                    "chip_id": chip["chip_id"],
                                },
                            }
                            chip_features.append(det_feature)

                return chip_features

            except Exception as e:
                logger.warning(f"Failed to process chip {chip['chip_id']}: {e}", exc_info=True)
                return None

        # Launch all chip processing tasks concurrently
        chip_tasks = [process_single_chip(chip) for chip in chips]

        # Process with progress tracking
        all_detections = []
        successful_chips = 0

        for coro in tqdm(
            asyncio.as_completed(chip_tasks), total=len(chips), desc="Processing chips"
        ):
            result = await coro
            if result is not None:
                all_detections.extend(result)
                successful_chips += 1

        await fetcher.close()

        print(f"[SUCCESS] Processed {successful_chips}/{len(chips)} chips successfully")
        print(f"[INFO] Detected {len(all_detections)} objects before merging")

        # Step 6: Merge results with NMS
        # Select line merge mode based on model (SDK internal logic)
        model_name = output_config.get("model_name", "unknown")
        if model_name == "mars":
            line_merge_mode = "intersect_only"  # Tested best for road networks
        else:
            line_merge_mode = "intersect_only"  # Safe default for all models

        merger = DetectionMerger(
            iou_threshold=0.5, line_merge_mode=line_merge_mode  # Polygon overlap threshold
        )

        # Prepare chip results in format expected by merger
        chip_results = [{"features": all_detections}]  # Single chip result with all features
        merged_results = merger.merge(chip_results=chip_results, aoi_geometry=aoi_geometry)

        print(f"[INFO] {len(merged_results.get('features', []))} objects after NMS merging")

        # Step 7: Publish to GeoCatalog (always - this is the primary workflow)
        # Note: detections.geojson is saved by ImageryMerger if save_local=True
        # Note: detection_counts will be calculated from filtered results later
        geocatalog_uri = output_config.get("geocatalog_uri")

        result = {
            "workflow_type": "aoi_based",
            "total_chips": len(chips),
            "successful_chips": successful_chips,
            "detection_count": len(all_detections),
            "merged_results": merged_results,
        }

        if geocatalog_uri and blob_service_client:
            # For multi-AOI: defer publishing and return data for batch processing
            if defer_publishing:
                print(f"📦 Prepared results for batch publishing...")
            else:
                print(f"📡 Publishing results to GeoCatalog...")

            try:
                # Check if we have saved chips to blob
                if chip_blob_paths:
                    print(f"   Merging {len(chip_blob_paths)} chips from blob storage...")

                    # Download chips from blob to local temp directory (CONCURRENTLY)
                    temp_dir = tempfile.mkdtemp(prefix="sdk_chips_")
                    chip_local_paths = []

                    container_client = blob_service_client.get_container_client(blob_container)

                    async def download_chip(chip_id, blob_path):
                        """Download a single chip TIF from blob storage."""
                        blob_client = container_client.get_blob_client(blob_path)
                        local_path = os.path.join(temp_dir, f"{chip_id}.tif")

                        with open(local_path, "wb") as f:
                            download_stream = await blob_client.download_blob()
                            data = await download_stream.readall()
                            f.write(data)

                        logger.debug(f"Downloaded {blob_path} to {local_path}")
                        return local_path

                    # Download all chips concurrently
                    download_tasks = [
                        download_chip(chip_id, blob_path)
                        for chip_id, blob_path in chip_blob_paths.items()
                    ]
                    chip_local_paths = await asyncio.gather(*download_tasks)

                    # Merge imagery and create overlays
                    # Determine work directory based on save_local flag
                    save_local = output_config.get("save_local", False)

                    if save_local:
                        # Save locally: use output_dir with AOI-specific subdirectory for multi-AOI
                        output_dir = output_config.get("output_dir", "./output")
                        aoi_id = output_config.get(
                            "aoi_id"
                        )  # Multi-AOI passes aoi_id in output_config
                        if defer_publishing and aoi_id:
                            # Multi-AOI: use subdirectory per AOI
                            work_dir = os.path.join(output_dir, aoi_id)
                        else:
                            # Single AOI: use output_dir directly
                            work_dir = output_dir
                        os.makedirs(work_dir, exist_ok=True)
                    else:
                        # Don't save locally: use temp directory (will be deleted after upload)
                        work_dir = tempfile.mkdtemp(prefix="geoai_results_")

                    merger = ImageryMerger()
                    merged_tif, overlay_tif, overlay_jpg, geojson_path = (
                        await merger.merge_chips_and_create_overlay(
                            chip_images=chip_local_paths,
                            detections_geojson=merged_results,
                            output_dir=work_dir,
                            aoi_geometry=aoi_geometry,
                        )
                    )

                    # Upload merged results to blob under results/ folder (with AOI-specific path for multi-AOI)
                    aoi_id = output_config.get("aoi_id", aoi_geometry.get("id", "aoi"))
                    results_blob_prefix = f"{model_name}/{run_id}/results/{aoi_id}"

                    merged_tif_blob = await self._upload_file_to_blob(
                        blob_service_client,
                        blob_container,
                        merged_tif,
                        f"{results_blob_prefix}/merged_imagery.tif",
                    )
                    overlay_tif_blob = await self._upload_file_to_blob(
                        blob_service_client,
                        blob_container,
                        overlay_tif,
                        f"{results_blob_prefix}/final_overlay.tif",
                    )
                    overlay_jpg_blob = await self._upload_file_to_blob(
                        blob_service_client,
                        blob_container,
                        overlay_jpg,
                        f"{results_blob_prefix}/final_overlay.jpg",
                    )
                    geojson_blob = await self._upload_file_to_blob(
                        blob_service_client,
                        blob_container,
                        geojson_path,
                        f"{results_blob_prefix}/detections.geojson",
                    )

                    # Read the filtered detections from the saved geojson file
                    # (merge_chips_and_create_overlay filters detections to AOI)
                    with open(geojson_path, "r") as f:
                        filtered_results = json.load(f)
                    filtered_detection_count = len(filtered_results.get("features", []))

                    # Re-count detections by category from FILTERED results (within AOI bounds)
                    filtered_detection_counts = {}
                    for detection in filtered_results.get("features", []):
                        label = detection.get("properties", {}).get("label", "Unknown")
                        filtered_detection_counts[label] = (
                            filtered_detection_counts.get(label, 0) + 1
                        )

                    # Cleanup: Keep only GeoJSON + overlay.jpg if save_local=True, delete everything if save_local=False
                    if save_local:
                        # Delete large TIF files, keep only detections.geojson and final_overlay.jpg
                        try:
                            os.remove(merged_tif)
                            os.remove(overlay_tif)
                            logger.debug(f"Cleaned up TIF files from {work_dir}")
                            print(f"💾 Saved local files to: {work_dir}")
                        except Exception as e:
                            logger.warning(f"Failed to cleanup TIF files: {e}")
                    else:
                        # Delete temp directory
                        try:
                            shutil.rmtree(work_dir, ignore_errors=True)
                            logger.debug(f"Cleaned up temporary results directory: {work_dir}")
                        except Exception as e:
                            logger.warning(f"Failed to cleanup temp directory: {e}")

                    logger.info(
                        f"Detections: {len(all_detections)} total from chips → {filtered_detection_count} within AOI"
                    )

                    # Prepare publication data
                    publication_data = {
                        "results_geojson": filtered_results,
                        "overlay_tif_blob": overlay_tif_blob,
                        "overlay_jpg_blob": overlay_jpg_blob,
                        "geojson_blob": geojson_blob,
                        "metadata": {
                            "model_id": model_name,
                            "workflow_run_id": run_id,
                            "workflow_id": model_name,
                            "aoi_id": aoi_id,  # Use aoi_id extracted earlier for blob path
                            "bbox": list(shapely_shape(aoi_geometry).bounds),
                            "geometry": aoi_geometry,
                            "output_type": model_spec["model_type"],  # Use model_type from spec
                            "chip_count": len(chip_blob_paths),
                            "detection_count": filtered_detection_count,
                        },
                    }

                    # For multi-AOI: return data for batch publishing
                    if defer_publishing:
                        result["publication_data"] = publication_data
                        result["blob_service_client"] = blob_service_client
                        result["run_id"] = run_id
                        result["blob_base_path"] = f"{blob_container}/{model_name}/{run_id}"
                        result["detection_count_total"] = len(all_detections)
                        result["detection_count"] = filtered_detection_count
                        result["detection_counts"] = (
                            filtered_detection_counts  # Use filtered counts
                        )
                        result["merged_results"] = filtered_results
                        if save_local:
                            result["output_path"] = work_dir
                        print(f"   📦 Results prepared for batch publishing")
                    else:
                        # Single AOI: publish immediately
                        writer = GeoCatalogWriter(
                            geocatalog_uri,
                            output_config.get("credential"),
                            storage_account_key=output_config.get("storage_account_key"),
                        )

                        geocatalog_urls = await writer.write_results(
                            collection_name=output_config.get("collection_name", "geoai-results"),
                            results_batch=[publication_data],
                            blob_service_client=blob_service_client,
                            blob_container=blob_container,
                        )

                        if geocatalog_urls:
                            geocatalog_url = geocatalog_urls[0]
                            print(f"[SUCCESS] Published to GeoCatalog: {geocatalog_url}")
                            result["geocatalog_url"] = geocatalog_url
                            result["published"] = True
                        else:
                            print(f"[WARNING] Failed to publish to GeoCatalog")
                            result["published"] = False

                        result["run_id"] = run_id
                        result["blob_base_path"] = f"{blob_container}/{model_name}/{run_id}"
                        result["detection_count_total"] = len(all_detections)
                        result["detection_count"] = filtered_detection_count
                        result["detection_counts"] = (
                            filtered_detection_counts  # Use filtered counts
                        )
                        result["merged_results"] = filtered_results
                        if save_local:
                            result["output_path"] = work_dir

                    # Clean up temporary chip files
                    shutil.rmtree(temp_dir, ignore_errors=True)
                    logger.debug(f"Cleaned up temporary chip directory: {temp_dir}")
                else:
                    logger.warning(
                        "No chips were saved to blob storage, skipping merge and publish"
                    )
                    result["published"] = False

            except Exception as e:
                logger.error(f"Failed to publish to GeoCatalog: {e}", exc_info=True)
                print(f"[WARNING] Failed to publish to GeoCatalog: {e}")
                result["published"] = False

        # Close blob service client if it was created (but not for multi-AOI - multi-AOI executor will close it)
        if blob_service_client and not defer_publishing:
            await blob_service_client.close()

        return result

    async def _upload_file_to_blob(self, blob_service, container, file_path, blob_name):
        """Upload file to blob storage and return blob path."""
        import os

        container_client = blob_service.get_container_client(container)
        blob_client = container_client.get_blob_client(blob_name)

        with open(file_path, "rb") as data:
            await blob_client.upload_blob(data, overwrite=True)

        return blob_name

    async def _save_chip_to_blob(
        self,
        blob_service_client,
        blob_container: str,
        model_name: str,
        run_id: str,
        chip_id: str,
        image_data: Dict,
        required_bands: List[str],
    ) -> str:
        """
        Save chip imagery as TIF to blob storage.

        Blob path structure: <model_name>/<run_id>/chips/<chip_id>.tif

        :param blob_service_client: Azure BlobServiceClient
        :param blob_container: Blob container name
        :param model_name: Model identifier (e.g., 'eoos')
        :param run_id: Run identifier (UUID or user-provided)
        :param chip_id: Chip identifier (e.g., 'chip_0_0')
        :param image_data: Image data dict from fetcher (contains arrays, transform, crs)
        :param required_bands: List of band names
        :return: Blob path or None if save failed
        """
        import tempfile

        import numpy as np
        import rasterio
        from rasterio.transform import Affine

        try:
            # Stack bands into multi-band array (bands, height, width)
            band_arrays = []
            for band_name in required_bands:
                if band_name in image_data["arrays"]:
                    band_arrays.append(image_data["arrays"][band_name])

            if not band_arrays:
                return None

            # Stack bands
            stacked = np.stack(band_arrays, axis=0)

            # Create temporary TIF file (close immediately for Windows compatibility)
            tmp = tempfile.NamedTemporaryFile(suffix=".tif", delete=False)
            tmp_path = tmp.name
            tmp.close()  # Close handle immediately to avoid Windows file locking

            try:
                # Write TIF with proper metadata
                # Set nodata=0 so merger can skip black edge pixels
                with rasterio.open(
                    tmp_path,
                    "w",
                    driver="GTiff",
                    height=stacked.shape[1],
                    width=stacked.shape[2],
                    count=len(band_arrays),
                    dtype=stacked.dtype,
                    crs=image_data.get("crs", "EPSG:3857"),
                    transform=image_data.get("transform"),
                    compress="lzw",
                    nodata=0,
                ) as dst:
                    dst.write(stacked)

                # Upload to blob
                blob_path = f"{model_name}/{run_id}/chips/{chip_id}.tif"
                container_client = blob_service_client.get_container_client(blob_container)
                blob_client = container_client.get_blob_client(blob_path)

                with open(tmp_path, "rb") as data:
                    await blob_client.upload_blob(data, overwrite=True)

                return blob_path

            finally:
                # Clean up temp file
                import os

                try:
                    os.unlink(tmp_path)
                except Exception:
                    pass  # Ignore cleanup errors

                return blob_path

        except Exception as e:
            import logging

            logger = logging.getLogger(__name__)
            logger.error(f"Failed to save chip {chip_id} to blob: {e}")
            return None

    def _select_items_temporal_coherence(
        self, chips: List[Dict], stac_items: List
    ) -> Dict[str, Any]:
        """
        Select STAC items using Temporal Coherence with Fallback algorithm.

        Algorithm:
        1. Group STAC items by acquisition date
        2. Find date with best chip coverage (≥90% threshold)
        3. Use that date as primary, fill gaps with closest dates

        :param chips: List of chip dictionaries
        :param stac_items: List of STAC items
        :return: Dict mapping chip_id -> STAC item
        """
        import logging
        from collections import defaultdict
        from datetime import datetime

        from shapely.geometry import shape as shapely_shape

        logger = logging.getLogger(__name__)

        # Step 1: Group items by acquisition date
        items_by_date = defaultdict(list)
        for item in stac_items:
            # Get acquisition date (ignore time for grouping)
            if hasattr(item, "datetime") and item.datetime:
                date = item.datetime.date()
            elif "datetime" in item.properties:
                date = datetime.fromisoformat(
                    item.properties["datetime"].replace("Z", "+00:00")
                ).date()
            else:
                date = datetime(2000, 1, 1).date()  # Fallback date

            items_by_date[date].append(item)

        # Step 2: Sort dates (newest first)
        sorted_dates = sorted(items_by_date.keys(), reverse=True)

        logger.info(
            f"Found {len(sorted_dates)} unique acquisition dates: {sorted_dates[:5]}{'...' if len(sorted_dates) > 5 else ''}"
        )

        # Step 3: Calculate coverage for each date
        primary_date = None
        coverage_threshold = 0.90

        # Handle edge case: no chips created
        if not chips:
            logger.warning("No chips created, cannot select temporal coherence")
            return {}

        for date in sorted_dates:
            date_items = items_by_date[date]
            chip_coverage = self._calculate_chip_coverage(chips, date_items)
            coverage_pct = len(chip_coverage) / len(chips)

            logger.debug(
                f"Date {date}: {len(date_items)} items, covers {len(chip_coverage)}/{len(chips)} chips ({coverage_pct:.1%})"
            )

            if coverage_pct >= coverage_threshold:
                primary_date = date
                logger.info(f"Primary date selected: {date} (covers {coverage_pct:.1%} of chips)")
                break

        # If no date covers ≥90%, use most recent
        if primary_date is None:
            primary_date = sorted_dates[0]
            logger.info(f"No single date covers ≥90%, using most recent: {primary_date}")

        # Step 4: Assign chips to items from primary date
        primary_items = items_by_date[primary_date]
        chip_to_item = self._calculate_chip_coverage(chips, primary_items)

        # Step 5: Fill gaps with closest dates
        unassigned_chips = [c for c in chips if c["chip_id"] not in chip_to_item]

        if unassigned_chips:
            logger.info(f"Filling {len(unassigned_chips)} gaps with fallback dates")

            for chip in unassigned_chips:
                # Find closest date that covers this chip
                closest_item = self._find_closest_date_item(
                    chip, stac_items, primary_date, sorted_dates
                )
                if closest_item:
                    chip_to_item[chip["chip_id"]] = closest_item

        logger.info(f"Final assignment: {len(chip_to_item)}/{len(chips)} chips assigned")

        return chip_to_item

    def _get_all_intersecting_items(
        self, chips: List[Dict], stac_items: List
    ) -> Dict[str, List[Any]]:
        """
        Get ALL STAC items that intersect each chip (for multi-tile merging).
        This matches AI Workflow behavior where chips spanning tile boundaries
        get multiple items that are merged together.

        :param chips: List of chip dictionaries
        :param stac_items: List of STAC items
        :return: Dict mapping chip_id -> List[STAC items]
        """
        from collections import defaultdict
        from datetime import datetime

        from shapely.geometry import box
        from shapely.geometry import shape as shapely_shape

        chip_to_items = {}

        for chip in chips:
            chip_shape = shapely_shape(chip["geometry"])
            intersecting_items = []

            for item in stac_items:
                # Get item bbox
                if hasattr(item, "bbox"):
                    item_bbox = item.bbox
                elif "bbox" in item.properties:
                    item_bbox = item.properties["bbox"]
                else:
                    continue

                # Create item polygon from bbox
                item_shape = box(item_bbox[0], item_bbox[1], item_bbox[2], item_bbox[3])

                # Check intersection
                if chip_shape.intersects(item_shape):
                    intersecting_items.append(item)

            if intersecting_items:
                # Sort by acquisition date (newest first) for temporal consistency
                sorted_items = sorted(
                    intersecting_items,
                    key=lambda x: (
                        x.datetime
                        if hasattr(x, "datetime") and x.datetime
                        else datetime.fromisoformat(
                            x.properties.get("datetime", "2000-01-01T00:00:00Z").replace(
                                "Z", "+00:00"
                            )
                        )
                    ),
                    reverse=True,
                )

                # Limit to 5 items to avoid memory issues (same as AI Workflow)
                chip_to_items[chip["chip_id"]] = sorted_items[:5]

                if len(sorted_items) > 1:
                    logger.debug(
                        f"Chip {chip['chip_id']}: {len(sorted_items)} intersecting items (will merge)"
                    )

        return chip_to_items

    def _calculate_chip_coverage(self, chips: List[Dict], items: List) -> Dict[str, Any]:
        """
        Calculate which chips are covered by given STAC items.

        :param chips: List of chip dictionaries
        :param items: List of STAC items
        :return: Dict mapping chip_id -> best STAC item for that chip
        """
        from shapely.geometry import shape as shapely_shape

        chip_to_item = {}

        for chip in chips:
            chip_shape = shapely_shape(chip["geometry"])
            chip_bounds = chip_shape.bounds  # (minx, miny, maxx, maxy)

            # Find items that intersect this chip
            matching_items = []
            for item in items:
                item_bbox = item.bbox  # [minx, miny, maxx, maxy]

                # Quick bbox intersection check
                if not (
                    chip_bounds[2] < item_bbox[0]  # chip right < item left
                    or chip_bounds[0] > item_bbox[2]  # chip left > item right
                    or chip_bounds[3] < item_bbox[1]  # chip top < item bottom
                    or chip_bounds[1] > item_bbox[3]
                ):  # chip bottom > item top
                    matching_items.append(item)

            if matching_items:
                # Pick best item (by cloud cover, then most recent)
                best_item = self._select_best_item(matching_items)
                chip_to_item[chip["chip_id"]] = best_item

        return chip_to_item

    def _select_best_item(self, items: List) -> Any:
        """
        Select best STAC item based on quality metrics.

        Priority:
        1. Lowest cloud cover
        2. Best GSD (resolution)
        3. Most recent

        :param items: List of candidate STAC items
        :return: Best item
        """

        def item_score(item):
            # Lower score = better
            cloud_cover = item.properties.get("eo:cloud_cover", 100)  # Default: worst
            gsd = item.properties.get("gsd", 10)  # Default: 10m

            # Normalize: cloud_cover + gsd as tie-breaker
            return cloud_cover + (gsd * 0.1)

        return min(items, key=item_score)

    def _find_closest_date_item(
        self, chip: Dict, all_items: List, primary_date, sorted_dates: List
    ) -> Any:
        """
        Find STAC item with closest date that covers the chip.

        :param chip: Chip dictionary
        :param all_items: All available STAC items
        :param primary_date: Primary acquisition date
        :param sorted_dates: All dates sorted (newest first)
        :return: Best matching item or None
        """
        from shapely.geometry import shape as shapely_shape

        chip_shape = shapely_shape(chip["geometry"])
        chip_bounds = chip_shape.bounds

        # Try dates in order of closeness to primary_date
        for date in sorted_dates:
            if date == primary_date:
                continue  # Already tried

            # Find items from this date that cover the chip
            for item in all_items:
                item_date = None
                if hasattr(item, "datetime") and item.datetime:
                    item_date = item.datetime.date()

                if item_date == date:
                    item_bbox = item.bbox

                    # Check intersection
                    if not (
                        chip_bounds[2] < item_bbox[0]
                        or chip_bounds[0] > item_bbox[2]
                        or chip_bounds[3] < item_bbox[1]
                        or chip_bounds[1] > item_bbox[3]
                    ):
                        return item

        return None

    def _filter_stac_items_by_geometry(self, stac_items: List, geometry: Dict) -> List:
        """
        Filter STAC items to only those intersecting the given geometry.

        Used for multi-AOI workflows to pre-filter STAC items per AOI.

        :param stac_items: List of STAC items
        :param geometry: GeoJSON geometry
        :return: Filtered list of STAC items
        """
        from shapely.geometry import box
        from shapely.geometry import shape as shapely_shape

        geom_shape = shapely_shape(geometry)
        geom_bbox = geom_shape.bounds  # (minx, miny, maxx, maxy)

        filtered = []
        for item in stac_items:
            item_bbox = item.bbox  # [minx, miny, maxx, maxy]

            # Quick bbox intersection check
            if not (
                geom_bbox[2] < item_bbox[0]  # geom right < item left
                or geom_bbox[0] > item_bbox[2]  # geom left > item right
                or geom_bbox[3] < item_bbox[1]  # geom top < item bottom
                or geom_bbox[1] > item_bbox[3]
            ):  # geom bottom > item top

                # More precise geometry intersection
                item_box = box(item_bbox[0], item_bbox[1], item_bbox[2], item_bbox[3])
                if geom_shape.intersects(item_box):
                    filtered.append(item)

        return filtered

    async def _execute_multi_aoi(
        self,
        constraint,
        model_spec: Dict,
        input_config: Dict,
        constraint_config: Dict,
        output_config: Dict,
        params: Dict,
        aoi_geometry: Dict = None,  # Ignored for multi-AOI (gets AOIs from constraint)
        **kwargs,  # Catch any other extra kwargs
    ) -> Dict[str, Any]:
        """
        Execute workflow for multiple AOIs.

        Optimizations:
        - Search STAC once with union bbox
        - Filter per AOI
        - Process each AOI sequentially with concurrent chip processing
        - Update collection extent incrementally

        :return: Result dictionary with multi-AOI statistics
        """
        import logging

        from ..core.spatial.geometry_utils import union_bboxes
        from ..core.stac.searcher import STACSearcher

        logger = logging.getLogger(__name__)

        aois = list(constraint.iter_aois())
        num_aois = len(aois)

        logger.info(f"Starting multi-AOI workflow: {num_aois} AOIs")
        print(f"\n{'='*80}")
        print(f"🗺️  Multi-AOI Workflow: {num_aois} AOIs")
        print(f"{'='*80}\n")

        # Generate single run_id for entire multi-AOI workflow (if not provided by user)
        workflow_run_id = output_config.get("run_id") or str(uuid.uuid4())
        logger.info(f"Multi-AOI workflow run_id: {workflow_run_id}")

        # Check if using STAC pass-through mode
        stac_search_items = None
        if constraint_config.get("stac_search"):
            print(f"[INFO] Using pre-built STAC search for all AOIs...")
            searcher = STACSearcher(
                geocatalog_uri=input_config["geocatalog_uri"],
                collection=input_config["collection"],
                credential=input_config.get("credential"),
            )
            stac_search_items = await searcher.search_from_external(
                constraint_config["stac_search"]
            )
            print(f"   Found {len(stac_search_items)} STAC items from search")
            print(f"   Will filter items per AOI (skip AOIs with no coverage)\n")

        # Step 1: Process each AOI sequentially (each AOI gets its own STAC search)
        collection_bbox = None
        all_results = []
        skipped_aois = []
        collection_name = output_config.get("collection_name")

        for aoi_idx, aoi in enumerate(aois):
            print(f"{'='*80}")
            print(f"📍 Processing AOI {aoi_idx + 1}/{num_aois}: {aoi['id']}")
            print(f"   Bbox: {aoi['bbox']}")
            print(f"{'='*80}\n")

            # If using stac_search, filter items for this AOI
            aoi_stac_items = None
            if stac_search_items is not None:
                # Filter items that intersect this AOI
                from shapely.geometry import box, shape

                aoi_geom = (
                    shape(aoi["geometry"]) if isinstance(aoi["geometry"], dict) else aoi["geometry"]
                )

                aoi_stac_items = []
                for item in stac_search_items:
                    # Get item geometry
                    if hasattr(item, "geometry"):
                        item_geom = shape(item.geometry)
                    elif isinstance(item, dict) and "geometry" in item:
                        item_geom = shape(item["geometry"])
                    else:
                        continue

                    # Check intersection
                    if aoi_geom.intersects(item_geom):
                        aoi_stac_items.append(item)

                if not aoi_stac_items:
                    logger.warning(f"AOI {aoi['id']}: No imagery in search results, skipping")
                    print(f"[WARNING] No imagery coverage for this AOI (skipping)\n")
                    skipped_aois.append({"id": aoi["id"], "reason": "no_imagery_in_search"})
                    continue

                print(f"   Found {len(aoi_stac_items)} intersecting items from search\n")

            # Each AOI searches independently (no union optimization)
            # This is correct for geographically distant AOIs (e.g., LAX, JFK, SEA)

            # Process this AOI with existing optimized workflow (STAC search happens inside)
            try:
                # Pass bbox from AOI dict for faster STAC queries
                aoi_bbox = aoi.get("bbox")
                
                aoi_result = await self._execute_aoi_workflow(
                    aoi_geometry=aoi["geometry"],
                    aoi_bbox=aoi_bbox,
                    model_spec=model_spec,
                    input_config=input_config,
                    constraint_config=constraint_config,
                    output_config={
                        **output_config,
                        "run_id": workflow_run_id,  # Use shared run_id for all AOIs
                        "aoi_id": aoi["id"],
                        "aoi_index": aoi_idx,
                        "aoi_properties": aoi.get("properties", {}),
                        "collection_name": collection_name,
                    },
                    params=params,
                    stac_items_override=aoi_stac_items,  # Use filtered items if stac_search mode
                    defer_publishing=True,  # Defer publishing for batch processing
                )

                # Update collection extent incrementally
                if collection_bbox is None:
                    collection_bbox = aoi["bbox"]
                else:
                    collection_bbox = union_bboxes(collection_bbox, aoi["bbox"])

                all_results.append(
                    {"aoi_id": aoi["id"], "aoi_index": aoi_idx, "result": aoi_result}
                )

                print(f"[SUCCESS] AOI {aoi['id']} completed\n")

            except Exception as e:
                logger.error(f"Failed to process AOI {aoi['id']}: {e}", exc_info=True)
                print(f"[ERROR] AOI {aoi['id']} failed: {e}\n")
                continue

        print(f"{'='*80}")
        print(
            f"[SUCCESS] Multi-AOI workflow completed: {len(all_results)}/{num_aois} AOIs processed"
        )
        if skipped_aois:
            print(f"[WARNING] Skipped {len(skipped_aois)} AOIs (no imagery coverage):")
            for skipped in skipped_aois[:5]:  # Show first 5
                print(f"   - {skipped['id']}")
            if len(skipped_aois) > 5:
                print(f"   ... and {len(skipped_aois) - 5} more")
        print(f"{'='*80}\n")

        # Batch publish all results to GeoCatalog (always - primary workflow)
        if collection_name and all_results:
            print(f"📡 Publishing {len(all_results)} results to GeoCatalog in parallel...")

            try:
                from ..core.results.geocatalog_writer import GeoCatalogWriter

                # Collect all publication data
                publication_batch = []
                blob_service_client = None
                blob_container = None

                for aoi_result_dict in all_results:
                    aoi_result = aoi_result_dict["result"]
                    if "publication_data" in aoi_result:
                        publication_batch.append(aoi_result["publication_data"])
                        if blob_service_client is None:
                            blob_service_client = aoi_result.get("blob_service_client")
                            # Get blob_container from output_config
                            blob_container = output_config.get("blob_container", "sdk-results")

                if publication_batch and blob_service_client:
                    writer = GeoCatalogWriter(
                        geocatalog_uri=output_config["geocatalog_uri"],
                        credential=output_config.get("credential"),
                        storage_account_key=output_config.get("storage_account_key"),
                    )

                    # Batch publish all items in parallel
                    geocatalog_urls = await writer.write_results(
                        collection_name=collection_name,
                        results_batch=publication_batch,
                        blob_service_client=blob_service_client,
                        blob_container=blob_container,
                    )

                    # Update collection extent after all items published
                    if collection_bbox:
                        await writer.update_collection_extent(
                            collection_id=collection_name, new_extent_bbox=collection_bbox
                        )
                        print(f"[SUCCESS] Updated collection extent: {collection_bbox}")

                    print(
                        f"[SUCCESS] Published {len(geocatalog_urls)}/{len(publication_batch)} items to GeoCatalog"
                    )

                    # Update results with GeoCatalog URLs
                    for idx, (aoi_result_dict, url) in enumerate(zip(all_results, geocatalog_urls)):
                        if url:
                            aoi_result_dict["result"]["geocatalog_url"] = url
                            aoi_result_dict["result"]["published"] = True
                        else:
                            aoi_result_dict["result"]["published"] = False

                    # Close blob service client
                    if blob_service_client:
                        await blob_service_client.close()
                else:
                    logger.warning("No publication data available for batch publishing")

            except Exception as e:
                logger.error(f"Failed to batch publish to GeoCatalog: {e}", exc_info=True)
                print(f"[WARNING] Failed to batch publish to GeoCatalog: {e}")

        return {
            "mode": "multi_aoi",
            "total_aois": num_aois,
            "successful_aois": len(all_results),
            "skipped_aois": len(skipped_aois),
            "skipped_details": skipped_aois,
            "collection_bbox": collection_bbox,
            "collection_name": collection_name,
            "results": all_results,
        }
