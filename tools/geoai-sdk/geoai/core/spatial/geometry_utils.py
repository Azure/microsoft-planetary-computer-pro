"""
geoai.core.spatial.geometry_utils

Geometry utility functions for spatial operations.
"""

from typing import Dict, List, Tuple, Union

from shapely.geometry import box, mapping, shape


def bbox_to_geometry(bbox: List[float]) -> Dict:
    """
    Convert bounding box to GeoJSON Polygon.

    :param bbox: [minx, miny, maxx, maxy]
    :return: GeoJSON Polygon geometry
    """
    minx, miny, maxx, maxy = bbox
    return {
        "type": "Polygon",
        "coordinates": [[[minx, miny], [maxx, miny], [maxx, maxy], [minx, maxy], [minx, miny]]],
    }


def geometry_to_bbox(geometry: Dict) -> List[float]:
    """
    Extract bounding box from GeoJSON geometry.

    :param geometry: GeoJSON geometry
    :return: [minx, miny, maxx, maxy]
    """
    geom = shape(geometry)
    bounds = geom.bounds  # (minx, miny, maxx, maxy)
    return list(bounds)


def union_bboxes(*bboxes: List[float]) -> List[float]:
    """
    Compute union of multiple bounding boxes.

    Returns the smallest bbox that contains all input bboxes.

    :param bboxes: Variable number of bboxes [minx, miny, maxx, maxy]
    :return: Union bbox [minx, miny, maxx, maxy]

    Example:
        >>> bbox1 = [-122.5, 37.5, -122.0, 38.0]
        >>> bbox2 = [-123.0, 37.0, -122.3, 37.8]
        >>> union_bboxes(bbox1, bbox2)
        [-123.0, 37.0, -122.0, 38.0]
    """
    if not bboxes:
        raise ValueError("At least one bbox required")

    if len(bboxes) == 1:
        return bboxes[0]

    # Extract min/max values across all bboxes
    min_x = min(bbox[0] for bbox in bboxes)
    min_y = min(bbox[1] for bbox in bboxes)
    max_x = max(bbox[2] for bbox in bboxes)
    max_y = max(bbox[3] for bbox in bboxes)

    return [min_x, min_y, max_x, max_y]


def intersects_bbox(geometry: Dict, bbox: List[float]) -> bool:
    """
    Check if a geometry intersects a bounding box.

    :param geometry: GeoJSON geometry
    :param bbox: [minx, miny, maxx, maxy]
    :return: True if geometry intersects bbox
    """
    geom_shape = shape(geometry)
    bbox_shape = box(bbox[0], bbox[1], bbox[2], bbox[3])
    return geom_shape.intersects(bbox_shape)
