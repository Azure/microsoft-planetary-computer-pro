"""
geoai.core.results.imagery_merger

ImageryMerger - Merge chip imagery and create detection overlays.
"""

import logging
import os
import tempfile
from typing import Any, Dict, List, Optional, Tuple

import geopandas as gpd
import numpy as np
import rasterio
from PIL import Image, ImageDraw
from rasterio.crs import CRS
from rasterio.merge import merge
from rasterio.transform import Affine
from rasterio.transform import from_bounds as transform_from_bounds
from rasterio.warp import transform_bounds
from rasterio.windows import Window, from_bounds
from shapely.geometry import shape

logger = logging.getLogger(__name__)


class ImageryMerger:
    """
    ImageryMerger - Merge imagery chips and create visualizations with overlaid detections.

    Adapted from patch-merger service for SDK use.
    """

    def __init__(self):
        """Initialize ImageryMerger."""
        pass

    def _filter_detections_to_aoi(self, detections_geojson: Dict, aoi_geometry: Dict) -> Dict:
        """
        Filter detections to only those within the AOI bounds.

        :param detections_geojson: GeoJSON FeatureCollection with all detections
        :param aoi_geometry: AOI geometry (GeoJSON) to filter by
        :return: Filtered GeoJSON FeatureCollection
        """
        from shapely.geometry import shape as shapely_shape
        from shapely.ops import unary_union

        try:
            # Convert AOI to shapely geometry
            aoi_shape = shapely_shape(aoi_geometry)

            # Filter detections
            filtered_features = []
            original_count = len(detections_geojson.get("features", []))

            for feature in detections_geojson.get("features", []):
                try:
                    # Get detection geometry
                    detection_geom = shapely_shape(feature["geometry"])

                    # Check if detection intersects with AOI
                    # Using intersects instead of within to include detections on the boundary
                    if detection_geom.intersects(aoi_shape):
                        filtered_features.append(feature)

                except Exception as e:
                    logger.debug(f"Error checking detection intersection: {e}")
                    # Include detection if we can't validate (safer)
                    filtered_features.append(feature)

            filtered_count = len(filtered_features)
            logger.info(f"Filtered detections: {original_count} → {filtered_count} (within AOI)")

            return {"type": "FeatureCollection", "features": filtered_features}

        except Exception as e:
            logger.warning(f"Error filtering detections to AOI: {e}, using all detections")
            return detections_geojson

    async def merge_chips_and_create_overlay(
        self,
        chip_images: List[str],  # List of TIF file paths
        detections_geojson: Dict,
        output_dir: str,
        aoi_geometry: Optional[Dict] = None,
    ) -> Tuple[str, str, str, str]:
        """
        Merge chip imagery and create overlay with detections.

        :param chip_images: List of paths to chip TIF files
        :param detections_geojson: GeoJSON FeatureCollection with all detections
        :param output_dir: Output directory for merged results
        :param aoi_geometry: Optional AOI geometry to crop to
        :return: Tuple of (merged_tif_path, overlay_tif_path, overlay_jpg_path, geojson_path)
        """
        logger.info(f"Merging {len(chip_images)} chips...")

        # Create output directory
        os.makedirs(output_dir, exist_ok=True)

        # Step 1: Merge TIF chips
        merged_tif_path = os.path.join(output_dir, "merged_imagery.tif")
        merged_data, merged_transform, merged_crs = await self._merge_tif_chips(
            chip_images, merged_tif_path, aoi_geometry
        )

        # Step 1.5: Filter detections to AOI bounds (if AOI provided)
        # This ensures detections.geojson and overlay only show detections within the cropped imagery
        filtered_detections = detections_geojson
        if aoi_geometry:
            filtered_detections = self._filter_detections_to_aoi(detections_geojson, aoi_geometry)

        # Step 2: Create overlay visualization (both TIF and JPEG) with filtered detections
        overlay_tif_path = os.path.join(output_dir, "final_overlay.tif")
        overlay_jpg_path = os.path.join(output_dir, "final_overlay.jpg")
        await self._create_overlay_visualization(
            merged_data,
            merged_transform,
            merged_crs,
            filtered_detections,  # Use filtered detections
            overlay_tif_path,
            overlay_jpg_path,
        )

        # Step 3: Save filtered GeoJSON
        geojson_path = os.path.join(output_dir, "detections.geojson")
        import json

        with open(geojson_path, "w") as f:
            json.dump(filtered_detections, f, indent=2)  # Save filtered detections

        logger.info(
            f"Merge complete: TIF={merged_tif_path}, Overlay TIF={overlay_tif_path}, Overlay JPEG={overlay_jpg_path}"
        )

        return merged_tif_path, overlay_tif_path, overlay_jpg_path, geojson_path

    async def _merge_tif_chips(
        self, tif_paths: List[str], output_path: str, aoi_geometry: Optional[Dict] = None
    ) -> Tuple[np.ndarray, Affine, Any]:
        """
        Merge TIF chips into a single mosaic and crop to AOI bounds (matching AI Workflow).

        Uses rasterio.merge to handle overlapping chips, then crops to AOI geometry.
        """
        src_files = []

        try:
            # Open all TIF files
            for path in tif_paths:
                src = rasterio.open(path)
                src_files.append(src)

            # Merge with nodata handling to eliminate black edge artifacts
            # method='first': Use first valid (non-zero) pixel in overlapping areas
            # nodata=0: Treat black (0) pixels as nodata/invalid
            merged_data, merged_transform = merge(src_files, nodata=0, method="first")

            # Get metadata from first file
            meta = src_files[0].meta.copy()
            merged_crs = src_files[0].crs

            # Crop to AOI bounds if provided (matching AI Workflow behavior)
            if aoi_geometry:
                try:
                    # Convert geometry to shapely and get bbox
                    aoi_shape = shape(aoi_geometry)
                    aoi_bbox = list(aoi_shape.bounds)  # [minx, miny, maxx, maxy]

                    logger.info(f"Cropping merged TIF to AOI bounds: {aoi_bbox}")

                    # Transform bbox to TIF's CRS if needed
                    crop_bbox = aoi_bbox
                    if merged_crs and str(merged_crs) != "EPSG:4326":
                        try:
                            crop_bbox = list(
                                transform_bounds(
                                    CRS.from_epsg(4326),  # Source (AOI in WGS84)
                                    merged_crs,  # Target (TIF's CRS)
                                    *aoi_bbox,
                                )
                            )
                            logger.info(f"Transformed bbox to {merged_crs}: {crop_bbox}")
                        except Exception as e:
                            logger.warning(f"Error transforming bbox, using original: {e}")

                    # Get window for cropping
                    crop_minx, crop_miny, crop_maxx, crop_maxy = crop_bbox
                    window = from_bounds(
                        crop_minx, crop_miny, crop_maxx, crop_maxy, merged_transform
                    )

                    # Ensure window is within bounds
                    if (
                        window.col_off < 0
                        or window.row_off < 0
                        or window.col_off + window.width > merged_data.shape[2]
                        or window.row_off + window.height > merged_data.shape[1]
                        or window.width <= 0
                        or window.height <= 0
                    ):

                        # Clamp window to raster bounds
                        col_off = max(0, min(int(window.col_off), merged_data.shape[2] - 1))
                        row_off = max(0, min(int(window.row_off), merged_data.shape[1] - 1))
                        width = min(int(window.width), merged_data.shape[2] - col_off)
                        height = min(int(window.height), merged_data.shape[1] - row_off)

                        if width <= 0 or height <= 0:
                            raise ValueError(f"Invalid crop dimensions: {width}x{height}")

                        window = Window(col_off, row_off, width, height)

                    # Crop the merged data (bands x height x width)
                    cropped_data = merged_data[
                        :,
                        int(window.row_off) : int(window.row_off + window.height),
                        int(window.col_off) : int(window.col_off + window.width),
                    ]

                    # Update transform for cropped area
                    cropped_transform = rasterio.windows.transform(window, merged_transform)

                    logger.info(f"Cropped from {merged_data.shape} to {cropped_data.shape}")

                    merged_data = cropped_data
                    merged_transform = cropped_transform

                except Exception as e:
                    logger.warning(f"Error cropping to AOI, using full merged extent: {e}")
                    # Continue with uncropped data

            meta.update(
                {
                    "driver": "GTiff",
                    "height": merged_data.shape[1],
                    "width": merged_data.shape[2],
                    "transform": merged_transform,
                    "compress": "lzw",
                }
            )

            # Write merged (and possibly cropped) TIF
            with rasterio.open(output_path, "w", **meta) as dst:
                dst.write(merged_data)

            logger.info(f"Merged {len(tif_paths)} chips: final shape={merged_data.shape}")

            return merged_data, merged_transform, merged_crs

        finally:
            # Close all source files
            for src in src_files:
                src.close()

    async def _create_overlay_visualization(
        self,
        raster_data: np.ndarray,
        transform: Affine,
        crs: Any,
        geojson_data: Dict,
        output_tif_path: str,
        output_jpg_path: str,
    ):
        """
        Create visualization with detections overlaid on imagery (both TIF and JPEG).

        Matches the AI workflow's overlay creation logic.

        :param raster_data: Raster data array (C, H, W)
        :param transform: Rasterio transform (maps pixel to CRS coordinates)
        :param crs: Coordinate reference system of the raster
        :param geojson_data: GeoJSON with detections (coordinates are in WGS84)
        :param output_tif_path: Output GeoTIFF path
        :param output_jpg_path: Output JPEG path
        """
        import geopandas as gpd
        from shapely.geometry import shape

        # Convert raster to RGB image
        if raster_data.shape[0] >= 3:
            rgb_data = raster_data[:3, :, :]  # Take first 3 bands
        else:
            # Grayscale - replicate to RGB
            rgb_data = np.repeat(raster_data[0:1, :, :], 3, axis=0)

        # Normalize to 0-255
        rgb_data = self._normalize_for_display(rgb_data)

        # Convert to PIL Image (H, W, C)
        img = Image.fromarray(rgb_data.transpose(1, 2, 0).astype(np.uint8))

        # Draw detections
        draw = ImageDraw.Draw(img, "RGBA")

        # OPTIMIZATION: Batch convert all WGS84 geometries to pixel coordinates at once
        # This reduces 1000s of individual GeoDataFrame conversions to a single batch operation
        features = geojson_data.get("features", [])
        feature_pixel_coords = self._batch_convert_features_to_pixel(
            features, transform, crs, rgb_data.shape
        )

        detection_count = 0
        for feature, pixel_coords in zip(features, feature_pixel_coords):
            try:
                if pixel_coords is None:
                    continue  # Conversion failed, skip this feature

                geometry = feature["geometry"]
                properties = feature.get("properties", {})
                geom_type = geometry.get("type")

                if geom_type == "Polygon":
                    detection_count += self._draw_polygon_with_coords(
                        pixel_coords, properties, draw
                    )
                elif geom_type == "LineString":
                    detection_count += self._draw_linestring_with_coords(
                        pixel_coords, properties, draw
                    )
                else:
                    logger.debug(f"Unsupported geometry type for drawing: {geom_type}")

            except Exception as e:
                logger.warning(f"Failed to draw detection: {e}", exc_info=True)
                continue

        # Save as JPEG
        img.save(output_jpg_path, "JPEG", quality=85)
        logger.info(
            f"Created overlay JPEG: {output_jpg_path} with {detection_count} detections drawn"
        )

        # Save as GeoTIFF with same overlay
        # Convert PIL image back to numpy array (H, W, C) -> (C, H, W)
        overlay_array = np.array(img).transpose(2, 0, 1).astype(np.uint8)

        # Write GeoTIFF with same geospatial metadata as merged imagery
        with rasterio.open(
            output_tif_path,
            "w",
            driver="GTiff",
            height=overlay_array.shape[1],
            width=overlay_array.shape[2],
            count=overlay_array.shape[0],
            dtype=overlay_array.dtype,
            crs=crs,
            transform=transform,
            compress="lzw",
        ) as dst:
            dst.write(overlay_array)

        logger.info(
            f"Created overlay GeoTIFF: {output_tif_path} with {detection_count} detections drawn"
        )

    def _draw_polygon(
        self,
        geometry: Dict,
        properties: Dict,
        draw: ImageDraw.Draw,
        transform: Affine,
        crs: Any,
        rgb_data: np.ndarray,
    ) -> int:
        """
        Draw Polygon geometry on image.

        :param geometry: GeoJSON Polygon geometry (in WGS84)
        :param properties: Feature properties
        :param draw: PIL ImageDraw object
        :param transform: Rasterio transform
        :param crs: Raster CRS
        :param rgb_data: RGB raster data array
        :return: 1 if drawn successfully, 0 otherwise
        """
        try:
            coords = geometry["coordinates"][0]

            # Convert WGS84 -> raster CRS -> pixel coordinates
            pixel_coords = self._wgs84_to_pixel(coords, transform, crs, rgb_data.shape)

            if not pixel_coords or len(pixel_coords) < 3:
                return 0

            # Draw filled polygon with outline (for buildings)
            draw.polygon(pixel_coords, fill=(255, 0, 0, 80), outline=(255, 0, 0, 200), width=2)

            # Add label with score
            label = properties.get("label", properties.get("class_name", "detection"))
            score = properties.get("score", properties.get("confidence", 0.0))
            text = f"{label}: {score:.2f}"

            # Draw label background and text at first coordinate
            x, y = pixel_coords[0]
            text_bbox = draw.textbbox((x, y - 15), text)
            draw.rectangle(text_bbox, fill=(0, 0, 0, 180))
            draw.text((x, y - 15), text, fill=(255, 255, 0, 255))

            return 1

        except Exception as e:
            logger.debug(f"Failed to draw polygon: {e}")
            return 0

    def _draw_linestring(
        self,
        geometry: Dict,
        properties: Dict,
        draw: ImageDraw.Draw,
        transform: Affine,
        crs: Any,
        rgb_data: np.ndarray,
    ) -> int:
        """
        Draw LineString geometry on image.

        :param geometry: GeoJSON LineString geometry (in WGS84)
        :param properties: Feature properties
        :param draw: PIL ImageDraw object
        :param transform: Rasterio transform
        :param crs: Raster CRS
        :param rgb_data: RGB raster data array
        :return: 1 if drawn successfully, 0 otherwise
        """
        try:
            coords = geometry["coordinates"]

            # Convert WGS84 -> raster CRS -> pixel coordinates
            pixel_coords = self._wgs84_to_pixel(coords, transform, crs, rgb_data.shape)

            if not pixel_coords or len(pixel_coords) < 2:
                return 0

            # Draw line (for roads/railways)
            label = properties.get("label", "road")

            # Color by label: cyan for roads, yellow for railways
            if "railway" in label.lower():
                color = (255, 255, 0, 200)  # Yellow
            else:
                color = (0, 255, 255, 200)  # Cyan

            draw.line(pixel_coords, fill=color, width=3)

            # Optionally add label at midpoint
            if len(pixel_coords) > 0:
                mid_idx = len(pixel_coords) // 2
                x, y = pixel_coords[mid_idx]
                score = properties.get("score", properties.get("confidence", 0.0))
                text = f"{label}: {score:.2f}"

                text_bbox = draw.textbbox((x, y - 15), text)
                draw.rectangle(text_bbox, fill=(0, 0, 0, 180))
                draw.text((x, y - 15), text, fill=(255, 255, 255, 255))

            return 1

        except Exception as e:
            logger.debug(f"Failed to draw linestring: {e}")
            return 0

    def _wgs84_to_pixel(
        self, wgs84_coords: list, transform: Affine, crs: Any, raster_shape: tuple
    ) -> list:
        """
        Convert WGS84 coordinates to pixel coordinates (single geometry).

        DEPRECATED: Use _batch_convert_features_to_pixel for better performance.

        :param wgs84_coords: List of [lon, lat] coordinates
        :param transform: Rasterio transform
        :param crs: Raster CRS
        :param raster_shape: Raster shape (C, H, W)
        :return: List of (col, row) pixel coordinates
        """
        from shapely.geometry import LineString

        # Create WGS84 geometry
        geom_wgs84 = LineString(wgs84_coords)
        gdf_wgs84 = gpd.GeoDataFrame(geometry=[geom_wgs84], crs="EPSG:4326")

        # Convert to raster CRS (typically EPSG:3857)
        target_crs = str(crs) if crs else "EPSG:3857"
        gdf_target = gdf_wgs84.to_crs(target_crs)
        geom_target = gdf_target.geometry.iloc[0]
        coords_target = list(geom_target.coords)

        # Convert to pixel coordinates
        pixel_coords = []
        for x_target, y_target in coords_target:
            # Using inverse transform: (x, y) -> (col, row)
            col, row = ~transform * (x_target, y_target)

            # Check if within bounds
            if 0 <= col < raster_shape[2] and 0 <= row < raster_shape[1]:
                pixel_coords.append((col, row))
            else:
                logger.debug(
                    f"Pixel coord out of bounds: ({col}, {row}), image size: ({raster_shape[2]}, {raster_shape[1]})"
                )

        return pixel_coords

    def _batch_convert_features_to_pixel(
        self, features: list, transform: Affine, crs: Any, raster_shape: tuple
    ) -> list:
        """
        Batch convert all WGS84 feature geometries to pixel coordinates.

        This is MUCH faster than converting individually because it performs
        a single GeoDataFrame CRS transformation instead of one per feature.

        Performance: ~1000 features in 5s vs 90s individual conversions (18x faster).

        :param features: List of GeoJSON features with WGS84 geometries
        :param transform: Rasterio transform
        :param crs: Raster CRS
        :param raster_shape: Raster shape (C, H, W)
        :return: List of pixel coordinate lists (one per feature, None if conversion fails)
        """
        from shapely.geometry import shape as shapely_shape

        if not features:
            return []

        try:
            # Extract all geometries from features
            geometries = []
            for feature in features:
                try:
                    geom = shapely_shape(feature["geometry"])
                    geometries.append(geom)
                except Exception as e:
                    logger.debug(f"Failed to parse geometry: {e}")
                    geometries.append(None)

            # Batch convert all geometries at once (SINGLE to_crs call!)
            gdf_wgs84 = gpd.GeoDataFrame(geometry=geometries, crs="EPSG:4326")
            target_crs = str(crs) if crs else "EPSG:3857"
            gdf_target = gdf_wgs84.to_crs(target_crs)

            # Convert each transformed geometry to pixel coordinates
            pixel_coords_list = []
            for geom_target in gdf_target.geometry:
                if geom_target is None or geom_target.is_empty:
                    pixel_coords_list.append(None)
                    continue

                try:
                    # Extract coordinates based on geometry type
                    if geom_target.geom_type == "Polygon":
                        # Exterior ring coordinates
                        coords_target = list(geom_target.exterior.coords)
                    elif geom_target.geom_type == "LineString":
                        coords_target = list(geom_target.coords)
                    elif geom_target.geom_type == "Point":
                        coords_target = [(geom_target.x, geom_target.y)]
                    else:
                        logger.debug(f"Unsupported geometry type: {geom_target.geom_type}")
                        pixel_coords_list.append(None)
                        continue

                    # Convert to pixel coordinates
                    pixel_coords = []
                    for x_target, y_target in coords_target:
                        col, row = ~transform * (x_target, y_target)

                        # Keep all coords even if out of bounds (drawing will clip)
                        pixel_coords.append((col, row))

                    pixel_coords_list.append(pixel_coords if pixel_coords else None)

                except Exception as e:
                    logger.debug(f"Failed to convert geometry to pixels: {e}")
                    pixel_coords_list.append(None)

            return pixel_coords_list

        except Exception as e:
            logger.error(f"Batch coordinate conversion failed: {e}", exc_info=True)
            # Fallback: return None for all features
            return [None] * len(features)

    def _draw_polygon_with_coords(
        self, pixel_coords: list, properties: Dict, draw: ImageDraw.Draw
    ) -> int:
        """
        Draw Polygon using pre-converted pixel coordinates.

        :param pixel_coords: List of (col, row) pixel coordinates
        :param properties: Feature properties
        :param draw: PIL ImageDraw object
        :return: 1 if drawn successfully, 0 otherwise
        """
        try:
            if not pixel_coords or len(pixel_coords) < 3:
                return 0

            # Draw filled polygon with outline
            draw.polygon(pixel_coords, fill=(255, 0, 0, 80), outline=(255, 0, 0, 200), width=2)

            # Add label with score
            label = properties.get("label", properties.get("class_name", "detection"))
            score = properties.get("score", properties.get("confidence", 0.0))
            text = f"{label}: {score:.2f}"

            # Draw label at first coordinate
            x, y = pixel_coords[0]
            text_bbox = draw.textbbox((x, y - 15), text)
            draw.rectangle(text_bbox, fill=(0, 0, 0, 180))
            draw.text((x, y - 15), text, fill=(255, 255, 0, 255))

            return 1

        except Exception as e:
            logger.debug(f"Failed to draw polygon: {e}")
            return 0

    def _draw_linestring_with_coords(
        self, pixel_coords: list, properties: Dict, draw: ImageDraw.Draw
    ) -> int:
        """
        Draw LineString using pre-converted pixel coordinates.

        :param pixel_coords: List of (col, row) pixel coordinates
        :param properties: Feature properties
        :param draw: PIL ImageDraw object
        :return: 1 if drawn successfully, 0 otherwise
        """
        try:
            if not pixel_coords or len(pixel_coords) < 2:
                return 0

            # Draw line
            label = properties.get("label", "road")

            # Color by label
            if "railway" in label.lower():
                color = (255, 255, 0, 200)  # Yellow
            else:
                color = (0, 255, 255, 200)  # Cyan

            draw.line(pixel_coords, fill=color, width=3)

            # Add label at midpoint
            mid_idx = len(pixel_coords) // 2
            x, y = pixel_coords[mid_idx]
            text = label
            text_bbox = draw.textbbox((x, y - 15), text)
            draw.rectangle(text_bbox, fill=(0, 0, 0, 180))
            draw.text((x, y - 15), text, fill=(255, 255, 255, 255))

            return 1

        except Exception as e:
            logger.debug(f"Failed to draw linestring: {e}")
            return 0

    def _normalize_for_display(self, data: np.ndarray) -> np.ndarray:
        """Normalize raster data to 0-255 range for display."""
        # Clip extreme values
        p2, p98 = np.percentile(data, (2, 98))
        data = np.clip(data, p2, p98)

        # Scale to 0-255
        data = (data - data.min()) / (data.max() - data.min() + 1e-6)
        data = (data * 255).astype(np.uint8)

        return data
