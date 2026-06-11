"""
Unit tests for geometry_utils - coordinate conversions and bbox operations.
"""

import pytest
from shapely.geometry import Polygon, box

from geoai.core.spatial.geometry_utils import bbox_to_geometry, geometry_to_bbox, union_bboxes


class TestGeometryUtils:
    """Test geometry utility functions."""

    def test_bbox_to_geometry_basic(self):
        """Convert bbox to GeoJSON Polygon."""
        bbox = [-118.42, 33.93, -118.40, 33.95]

        geometry = bbox_to_geometry(bbox)

        assert geometry["type"] == "Polygon"
        assert "coordinates" in geometry

        # First and last coordinate should be the same (closed polygon)
        coords = geometry["coordinates"][0]
        assert coords[0] == coords[-1]

        # Should have 5 coordinates (4 corners + closing point)
        assert len(coords) == 5

    def test_bbox_to_geometry_coordinates(self):
        """Verify bbox to geometry coordinate ordering."""
        bbox = [-118.42, 33.93, -118.40, 33.95]
        minx, miny, maxx, maxy = bbox

        geometry = bbox_to_geometry(bbox)
        coords = geometry["coordinates"][0]

        # Check corner coordinates
        assert coords[0] == [minx, miny]  # Bottom-left
        assert coords[1] == [maxx, miny]  # Bottom-right
        assert coords[2] == [maxx, maxy]  # Top-right
        assert coords[3] == [minx, maxy]  # Top-left
        assert coords[4] == [minx, miny]  # Close polygon

    def test_geometry_to_bbox_basic(self):
        """Extract bbox from GeoJSON geometry."""
        geometry = box(-118.42, 33.93, -118.40, 33.95).__geo_interface__

        bbox = geometry_to_bbox(geometry)

        assert len(bbox) == 4
        minx, miny, maxx, maxy = bbox

        # Verify bbox ordering
        assert minx < maxx
        assert miny < maxy

    def test_bbox_geometry_roundtrip(self):
        """Converting bbox -> geometry -> bbox should preserve values."""
        original_bbox = [-118.42, 33.93, -118.40, 33.95]

        # Convert to geometry and back
        geometry = bbox_to_geometry(original_bbox)
        recovered_bbox = geometry_to_bbox(geometry)

        # Should be approximately equal (allowing for floating point)
        for orig, recovered in zip(original_bbox, recovered_bbox):
            assert abs(orig - recovered) < 1e-10

    def test_geometry_to_bbox_polygon(self):
        """Extract bbox from complex polygon."""
        # Create polygon with more than 4 points
        polygon = Polygon(
            [
                (-118.42, 33.93),
                (-118.40, 33.93),
                (-118.39, 33.95),
                (-118.41, 33.96),
                (-118.42, 33.93),
            ]
        )

        bbox = geometry_to_bbox(polygon.__geo_interface__)

        assert len(bbox) == 4
        # Bbox should be tight around polygon
        minx, miny, maxx, maxy = bbox
        assert minx <= -118.42
        assert maxx >= -118.39
        assert miny <= 33.93
        assert maxy >= 33.96

    def test_union_bboxes_basic(self):
        """Union of two bboxes should contain both."""
        bbox1 = [-118.42, 33.93, -118.40, 33.95]
        bbox2 = [-118.39, 33.94, -118.37, 33.96]

        union = union_bboxes(bbox1, bbox2)

        assert len(union) == 4
        minx, miny, maxx, maxy = union

        # Union should contain both input bboxes
        assert minx <= -118.42  # Leftmost extent
        assert maxx >= -118.37  # Rightmost extent
        assert miny <= 33.93  # Bottom extent
        assert maxy >= 33.96  # Top extent

    def test_union_bboxes_overlapping(self):
        """Union of overlapping bboxes."""
        bbox1 = [-118.42, 33.93, -118.40, 33.95]
        bbox2 = [-118.41, 33.94, -118.39, 33.96]

        union = union_bboxes(bbox1, bbox2)

        minx, miny, maxx, maxy = union

        # Should span full extent
        assert minx == -118.42
        assert maxx == -118.39
        assert miny == 33.93
        assert maxy == 33.96

    def test_union_bboxes_single(self):
        """Union of single bbox should return itself."""
        bbox = [-118.42, 33.93, -118.40, 33.95]

        union = union_bboxes(bbox)

        assert union == bbox

    def test_union_bboxes_multiple(self):
        """Union of three or more bboxes."""
        bbox1 = [-118.42, 33.93, -118.40, 33.95]
        bbox2 = [-118.39, 33.94, -118.37, 33.96]
        bbox3 = [-118.41, 33.92, -118.38, 33.94]

        union = union_bboxes(bbox1, bbox2, bbox3)

        minx, miny, maxx, maxy = union

        # Should span all three bboxes
        assert minx <= -118.42
        assert maxx >= -118.37
        assert miny <= 33.92
        assert maxy >= 33.96

    def test_bbox_validation(self):
        """Bbox should have minx < maxx and miny < maxy."""
        bbox = [-118.42, 33.93, -118.40, 33.95]
        minx, miny, maxx, maxy = bbox

        assert minx < maxx, "minx should be less than maxx"
        assert miny < maxy, "miny should be less than maxy"

    def test_empty_bbox_union(self):
        """Union with no bboxes should handle gracefully."""
        # This might raise an error or return None - test behavior
        with pytest.raises((TypeError, ValueError)):
            union_bboxes()

    def test_geometry_to_bbox_point(self):
        """Extract bbox from point geometry."""
        from shapely.geometry import Point

        point = Point(-118.42, 33.93)
        bbox = geometry_to_bbox(point.__geo_interface__)

        assert len(bbox) == 4
        # Point bbox should have zero area
        minx, miny, maxx, maxy = bbox
        assert abs(minx - maxx) < 1e-10
        assert abs(miny - maxy) < 1e-10

    def test_geometry_to_bbox_linestring(self):
        """Extract bbox from LineString geometry."""
        from shapely.geometry import LineString

        line = LineString([(-118.42, 33.93), (-118.40, 33.95)])
        bbox = geometry_to_bbox(line.__geo_interface__)

        assert len(bbox) == 4
        minx, miny, maxx, maxy = bbox

        # Bbox should contain line endpoints
        assert minx == -118.42
        assert maxx == -118.40
        assert miny == 33.93
        assert maxy == 33.95


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
