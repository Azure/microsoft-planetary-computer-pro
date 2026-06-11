"""
geoai.core.models.coordinate_converter

CoordinateConverter - Convert between pixel and geographic coordinates.
"""

import logging
from typing import Any, Dict, Optional, Tuple

import geopandas as gpd
from rasterio.transform import Affine
from shapely.geometry import box

logger = logging.getLogger(__name__)


class CoordinateConverter:
    """
    CoordinateConverter - Convert between pixel and geographic coordinate systems.

    Handles conversion from model output pixel coordinates to WGS84 geographic
    coordinates for GeoJSON output.

    Example:

      ```python
      converter = CoordinateConverter()

      # Convert pixel bbox to WGS84
      wgs84_coords = converter.pixel_to_wgs84(
          pixel_bbox=[10, 20, 100, 80],  # [x, y, w, h]
          transform=chip_transform,
          source_crs="EPSG:3857"
      )
      ```
    """

    @staticmethod
    def pixel_to_wgs84(
        pixel_bbox: list, transform: Affine, source_crs: Any
    ) -> Optional[Tuple[float, float, float, float]]:
        """
        Convert pixel bounding box to WGS84 geographic coordinates.

        The model returns bounding boxes in pixel coordinates (x, y, w, h).
        This converts them to WGS84 (lon, lat) for GeoJSON storage.

        :param pixel_bbox: List [x, y, w, h] in pixel coordinates
        :param transform: Rasterio Affine transform from image metadata
        :param source_crs: Source CRS (string like "EPSG:3857" or rasterio CRS object)
        :return: Tuple of (lon_min, lat_min, lon_max, lat_max) in WGS84, or None if conversion fails
        """
        if len(pixel_bbox) < 4:
            logger.warning(f"Invalid pixel_bbox: {pixel_bbox}")
            return None

        # Parse [x, y, w, h] format
        pixel_x, pixel_y, pixel_w, pixel_h = pixel_bbox[:4]
        pixel_xmin = pixel_x
        pixel_ymin = pixel_y
        pixel_xmax = pixel_x + pixel_w
        pixel_ymax = pixel_y + pixel_h

        return CoordinateConverter._convert_bbox_to_wgs84(
            pixel_xmin, pixel_ymin, pixel_xmax, pixel_ymax, transform, source_crs
        )

    @staticmethod
    def geometry_to_wgs84(geometry: Dict, transform: Affine, source_crs: Any) -> Optional[Dict]:
        """
        Convert GeoJSON geometry from pixel coordinates to WGS84 geographic coordinates.

        MARS returns geometries with coordinates in pixel space. This converts them
        to WGS84 (lon, lat) for proper GeoJSON output.

        Supported geometry types:
        - Polygon: Building footprints
        - LineString: Roads, railways

        :param geometry: GeoJSON geometry dict with pixel coordinates
        :param transform: Rasterio Affine transform from image metadata
        :param source_crs: Source CRS (string like "EPSG:3857" or rasterio CRS object)
        :return: Geometry dict with WGS84 coordinates, or None if conversion fails
        """
        try:
            if transform is None:
                logger.warning("No transform available for coordinate conversion")
                return None

            geom_type = geometry.get("type")
            coords = geometry.get("coordinates")

            if not geom_type or not coords:
                logger.warning(f"Invalid geometry: {geometry}")
                return None

            # Parse source CRS
            source_epsg = CoordinateConverter._parse_crs_to_epsg(source_crs)

            if geom_type == "Polygon":
                # Polygon: List of rings (outer + holes)
                wgs84_rings = []
                for ring in coords:
                    wgs84_ring = CoordinateConverter._convert_coordinate_list(
                        ring, transform, source_epsg
                    )
                    if wgs84_ring:
                        wgs84_rings.append(wgs84_ring)

                return {"type": "Polygon", "coordinates": wgs84_rings}

            elif geom_type == "LineString":
                # LineString: Single list of coordinates
                wgs84_coords = CoordinateConverter._convert_coordinate_list(
                    coords, transform, source_epsg
                )

                return {"type": "LineString", "coordinates": wgs84_coords}

            elif geom_type == "MultiPolygon":
                # MultiPolygon: List of polygons
                wgs84_polygons = []
                for polygon in coords:
                    wgs84_rings = []
                    for ring in polygon:
                        wgs84_ring = CoordinateConverter._convert_coordinate_list(
                            ring, transform, source_epsg
                        )
                        if wgs84_ring:
                            wgs84_rings.append(wgs84_ring)
                    if wgs84_rings:
                        wgs84_polygons.append(wgs84_rings)

                return {"type": "MultiPolygon", "coordinates": wgs84_polygons}

            else:
                logger.warning(f"Unsupported geometry type: {geom_type}")
                return None

        except Exception as e:
            logger.error(f"Failed to convert geometry coordinates: {e}", exc_info=True)
            return None

    @staticmethod
    def _convert_coordinate_list(coords: list, transform: Affine, source_epsg: int) -> list:
        """
        Convert a list of pixel coordinates to WGS84.

        :param coords: List of [x, y] pixel coordinates
        :param transform: Rasterio Affine transform
        :param source_epsg: Source EPSG code
        :return: List of [lon, lat] WGS84 coordinates
        """
        wgs84_coords = []

        for pixel_x, pixel_y in coords:
            # Convert pixel to source CRS
            x_src, y_src = transform * (pixel_x, pixel_y)

            # Convert to WGS84
            if source_epsg == 4326:
                # Already in WGS84
                wgs84_coords.append([x_src, y_src])
            else:
                # Convert from source CRS to WGS84
                from shapely.geometry import Point

                point = Point(x_src, y_src)
                gdf = gpd.GeoDataFrame(geometry=[point], crs=f"EPSG:{source_epsg}")
                gdf_wgs84 = gdf.to_crs("EPSG:4326")
                point_wgs84 = gdf_wgs84.geometry.iloc[0]
                wgs84_coords.append([point_wgs84.x, point_wgs84.y])

        return wgs84_coords

    @staticmethod
    def _convert_bbox_to_wgs84(
        pixel_xmin: float,
        pixel_ymin: float,
        pixel_xmax: float,
        pixel_ymax: float,
        transform: Affine,
        source_crs: Any,
    ) -> Optional[Tuple[float, float, float, float]]:
        """
        Convert pixel coordinates to WGS84 geographic coordinates.

        :param pixel_xmin: Left pixel coordinate
        :param pixel_ymin: Top pixel coordinate
        :param pixel_xmax: Right pixel coordinate
        :param pixel_ymax: Bottom pixel coordinate
        :param transform: Rasterio Affine transform from image metadata
        :param source_crs: Source CRS from image metadata
        :return: Tuple of (lon_min, lat_min, lon_max, lat_max) in WGS84, or None if conversion fails
        """
        try:
            if transform is None:
                logger.warning("No transform available for coordinate conversion")
                return None

            # Convert pixel coordinates to source CRS coordinates
            # Transform maps (col, row) -> (x, y) in the source CRS
            x_min_src, y_min_src = transform * (pixel_xmin, pixel_ymin)
            x_max_src, y_max_src = transform * (pixel_xmax, pixel_ymax)

            # Parse source CRS
            source_epsg = CoordinateConverter._parse_crs_to_epsg(source_crs)

            # Convert to WGS84 based on source EPSG
            if source_epsg == 4326:
                # Already in WGS84
                return (x_min_src, y_min_src, x_max_src, y_max_src)
            else:
                # Convert from source CRS to WGS84
                bbox_geom = box(x_min_src, y_min_src, x_max_src, y_max_src)
                gdf = gpd.GeoDataFrame(geometry=[bbox_geom], crs=f"EPSG:{source_epsg}")
                gdf_wgs84 = gdf.to_crs("EPSG:4326")
                bbox_wgs84 = gdf_wgs84.geometry.iloc[0].bounds
                return (bbox_wgs84[0], bbox_wgs84[1], bbox_wgs84[2], bbox_wgs84[3])

        except Exception as e:
            logger.error(f"Failed to convert bbox coordinates: {e}", exc_info=True)
            return None

    @staticmethod
    def _parse_crs_to_epsg(source_crs: Any) -> int:
        """
        Parse CRS to EPSG code.

        :param source_crs: CRS (string like "EPSG:3857" or rasterio CRS object)
        :return: EPSG code (defaults to 3857 if unknown)
        """
        # Handle string format
        if isinstance(source_crs, str):
            if source_crs.startswith("EPSG:"):
                try:
                    return int(source_crs.split(":")[1])
                except ValueError:
                    logger.warning(f"Invalid EPSG format: {source_crs}, defaulting to 3857")
                    return 3857
            else:
                logger.warning(f"Unknown CRS format: {source_crs}, defaulting to 3857")
                return 3857

        # Handle rasterio CRS object
        elif source_crs and hasattr(source_crs, "to_epsg"):
            epsg = source_crs.to_epsg()
            if epsg:
                return epsg

        # Default to Web Mercator (common for web imagery)
        logger.debug("No CRS information, defaulting to EPSG:3857 (Web Mercator)")
        return 3857

    @staticmethod
    def create_geojson_feature(detection: Dict, chip_id: str) -> Dict:
        """
        Create GeoJSON Feature from normalized detection with WGS84 coordinates.

        :param detection: Detection dict with 'bbox' (WGS84 coords), 'score', 'label'
        :param chip_id: Chip identifier
        :return: GeoJSON Feature dict
        """
        lon_min, lat_min, lon_max, lat_max = detection["wgs84_bbox"]

        return {
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
                "chip_id": chip_id,
            },
        }
