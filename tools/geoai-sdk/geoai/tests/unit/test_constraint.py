"""
Unit tests for Constraint - multi-AOI logic and geometry handling.
"""

import tempfile

import geopandas as gpd
import pytest
from shapely.geometry import box

from geoai.public.aoi_constraint import Constraint


class TestConstraint:
    """Test constraint validation and multi-AOI logic."""

    def test_bbox_constraint(self):
        """Single AOI from bbox should work."""
        constraint = Constraint(
            bbox=[-118.42, 33.93, -118.40, 33.95], datetime="2020-01-01/2023-12-31"
        )

        assert constraint.mode == "single"
        assert constraint.bbox is not None
        assert constraint.geometry is not None
        assert constraint.datetime == "2020-01-01/2023-12-31"

    def test_geometry_constraint(self):
        """Single AOI from GeoJSON geometry should work."""
        geom = box(-118.42, 33.93, -118.40, 33.95).__geo_interface__

        constraint = Constraint(geometry=geom, datetime="2020-01-01/2023-12-31")

        assert constraint.mode == "single"
        assert constraint.geometry is not None
        assert constraint.bbox is not None  # Should auto-calculate bbox

    def test_multi_aoi_geodataframe(self):
        """Multi-AOI from GeoDataFrame should work."""
        # Create GeoDataFrame with multiple AOIs
        gdf = gpd.GeoDataFrame(
            {
                "id": ["aoi1", "aoi2", "aoi3"],
                "name": ["Area 1", "Area 2", "Area 3"],
                "geometry": [
                    box(-118.42, 33.93, -118.41, 33.94),
                    box(-118.40, 33.93, -118.39, 33.94),
                    box(-118.38, 33.93, -118.37, 33.94),
                ],
            },
            crs="EPSG:4326",
        )

        constraint = Constraint(aois=gdf, datetime="2020-01-01/2023-12-31")

        assert constraint.mode == "multi"
        assert constraint.aois is not None
        assert len(constraint.aois) == 3

    def test_multi_aoi_iteration(self):
        """Should be able to iterate over AOIs."""
        gdf = gpd.GeoDataFrame(
            {
                "id": ["aoi1", "aoi2"],
                "geometry": [
                    box(-118.42, 33.93, -118.41, 33.94),
                    box(-118.40, 33.93, -118.39, 33.94),
                ],
            },
            crs="EPSG:4326",
        )

        constraint = Constraint(aois=gdf, datetime="2020-01-01/2023-12-31")

        # Iterate through AOIs
        aoi_list = list(constraint.iter_aois())

        assert len(aoi_list) == 2
        for aoi in aoi_list:
            assert "id" in aoi
            assert "geometry" in aoi
            assert "bbox" in aoi

    def test_multi_aoi_geoparquet_file(self):
        """Multi-AOI from GeoParquet file should work."""
        # Create temporary GeoParquet file
        gdf = gpd.GeoDataFrame(
            {
                "id": ["test1", "test2"],
                "geometry": [
                    box(-118.42, 33.93, -118.41, 33.94),
                    box(-118.40, 33.93, -118.39, 33.94),
                ],
            },
            crs="EPSG:4326",
        )

        with tempfile.NamedTemporaryFile(suffix=".geoparquet", delete=False) as tmp:
            gdf.to_parquet(tmp.name)
            tmp_path = tmp.name

        try:
            constraint = Constraint(aois=tmp_path, datetime="2020-01-01/2023-12-31")

            assert constraint.mode == "multi"
            assert len(constraint.aois) == 2
        finally:
            import os

            os.unlink(tmp_path)

    def test_missing_aoi_error(self):
        """Should raise error when no AOI provided."""
        with pytest.raises(ValueError, match="Must provide bbox, geometry, aois"):
            Constraint(datetime="2020-01-01/2023-12-31")

    def test_multiple_aoi_types_error(self):
        """Should raise error when multiple AOI types provided."""
        with pytest.raises(ValueError, match="Provide only ONE of"):
            Constraint(
                bbox=[-118.42, 33.93, -118.40, 33.95],
                geometry=box(-118.42, 33.93, -118.40, 33.95).__geo_interface__,
                datetime="2020-01-01/2023-12-31",
            )

    def test_filter_parameter(self):
        """Should accept CQL2 filter."""
        constraint = Constraint(
            bbox=[-118.42, 33.93, -118.40, 33.95],
            datetime="2020-01-01/2023-12-31",
            filter={"eo:cloud_cover": {"lt": 10}},
        )

        assert constraint.filter == {"eo:cloud_cover": {"lt": 10}}

    def test_aoi_with_properties(self):
        """AOIs should preserve custom properties."""
        gdf = gpd.GeoDataFrame(
            {
                "id": ["building1"],
                "name": ["Main Building"],
                "area_m2": [1000],
                "geometry": [box(-118.42, 33.93, -118.41, 33.94)],
            },
            crs="EPSG:4326",
        )

        constraint = Constraint(aois=gdf, datetime="2020-01-01/2023-12-31")

        aoi = list(constraint.iter_aois())[0]
        assert aoi["properties"]["name"] == "Main Building"
        assert aoi["properties"]["area_m2"] == 1000

    def test_invalid_bbox(self):
        """Should validate bbox format."""
        with pytest.raises(ValueError):
            Constraint(
                bbox=[-118.42, 33.93], datetime="2020-01-01/2023-12-31"  # Missing coordinates
            )

    def test_file_not_found_error(self):
        """Should raise error for missing AOI file."""
        with pytest.raises(FileNotFoundError):
            Constraint(aois="nonexistent_file.geoparquet", datetime="2020-01-01/2023-12-31")

    def test_stac_search_passthrough(self):
        """Should accept pre-built STAC search."""

        # Mock STAC search object
        class MockSearch:
            def get_all_items(self):
                return []

        search = MockSearch()

        constraint = Constraint(bbox=[-118.42, 33.93, -118.40, 33.95], stac_search=search)

        assert constraint.stac_search is search
        assert constraint.datetime is None  # Ignored in pass-through mode

    def test_single_aoi_has_no_aois_list(self):
        """Single AOI mode should not have aois list."""
        constraint = Constraint(
            bbox=[-118.42, 33.93, -118.40, 33.95], datetime="2020-01-01/2023-12-31"
        )

        assert constraint.mode == "single"
        assert constraint.aois is None

    def test_multi_aoi_has_no_single_geometry(self):
        """Multi-AOI mode should not have single geometry."""
        gdf = gpd.GeoDataFrame(
            {"id": ["aoi1"], "geometry": [box(-118.42, 33.93, -118.41, 33.94)]}, crs="EPSG:4326"
        )

        constraint = Constraint(aois=gdf, datetime="2020-01-01/2023-12-31")

        assert constraint.mode == "multi"
        assert constraint.geometry is None
        assert constraint.bbox is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
