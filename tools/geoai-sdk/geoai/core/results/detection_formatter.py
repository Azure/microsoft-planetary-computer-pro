"""
geoai.core.results.detection_formatter

DetectionFormatter - Format object detection results as GeoJSON.
"""

from typing import Dict, List, Optional


class DetectionFormatter:
    """
    DetectionFormatter - Format object detections as GeoJSON FeatureCollection.

    Handles both bbox-based detections (EOOS) and geometry-based detections (MARS).
    """

    def format(self, detections: List[Dict], metadata: Dict = None) -> Dict:
        """
        Format detections as GeoJSON FeatureCollection.

        Supports two detection formats:
        1. Bbox format (EOOS): {'bbox': [x,y,w,h], 'wgs84_bbox': (lon_min, lat_min, lon_max, lat_max), 'score': 0.9, 'label': 'plane'}
        2. Geometry format (MARS): {'geometry': {...}, 'wgs84_geometry': {...}, 'score': 0.9, 'label': 'Building'}

        :param detections: List of detection dicts (with WGS84 coordinates already converted)
        :param metadata: Optional metadata to include (model_id, timestamp, etc.)
        :return: GeoJSON FeatureCollection
        """
        features = []

        for det in detections:
            try:
                # Determine if this is a bbox or geometry detection
                if "wgs84_geometry" in det:
                    # Geometry format (MARS)
                    feature = self._create_geometry_feature(det)
                elif "wgs84_bbox" in det:
                    # Bbox format (EOOS)
                    feature = self._create_bbox_feature(det)
                else:
                    # Skip if no geographic coordinates
                    continue

                if feature:
                    features.append(feature)

            except Exception as e:
                # Log error but continue processing other detections
                import logging

                logging.warning(f"Failed to format detection: {e}")
                continue

        # Build FeatureCollection
        geojson = {"type": "FeatureCollection", "features": features}

        # Add metadata if provided
        if metadata:
            geojson["properties"] = metadata

        return geojson

    def _create_geometry_feature(self, detection: Dict) -> Optional[Dict]:
        """
        Create GeoJSON Feature from geometry detection (MARS).

        :param detection: Detection dict with 'wgs84_geometry', 'score', 'label'
        :return: GeoJSON Feature dict
        """
        geometry = detection.get("wgs84_geometry")

        if not geometry:
            return None

        return {
            "type": "Feature",
            "geometry": geometry,
            "properties": {
                "score": detection.get("score", 0.0),
                "label": detection.get("label", "unknown"),
                "class_name": detection.get("label", "unknown"),  # Alias for compatibility
            },
        }

    def _create_bbox_feature(self, detection: Dict) -> Optional[Dict]:
        """
        Create GeoJSON Feature from bbox detection (EOOS).

        Converts bbox to Polygon geometry.

        :param detection: Detection dict with 'wgs84_bbox', 'score', 'label'
        :return: GeoJSON Feature dict
        """
        wgs84_bbox = detection.get("wgs84_bbox")

        if not wgs84_bbox or len(wgs84_bbox) < 4:
            return None

        lon_min, lat_min, lon_max, lat_max = wgs84_bbox[:4]

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
                "score": detection.get("score", 0.0),
                "label": detection.get("label", "unknown"),
                "class_name": detection.get("label", "unknown"),  # Alias for compatibility
            },
        }
