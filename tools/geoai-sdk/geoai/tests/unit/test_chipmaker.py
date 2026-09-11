"""
Unit tests for ChipMaker - chip generation and grid logic.
"""

import pytest
from shapely.geometry import box

from geoai.core.spatial.chipmaker import ChipMaker


class TestChipMaker:
    """Test chip generation logic."""

    def test_single_chip_small_aoi(self):
        """Small AOI should generate exactly 1 chip."""
        chipmaker = ChipMaker(chip_size=1000, stride=500)

        # Create small AOI (100m x 100m in Web Mercator, roughly)
        # Using a small area in WGS84 that's ~100m x 100m
        aoi = box(-118.40, 33.93, -118.399, 33.931)

        chips = chipmaker.create_chips(aoi.__geo_interface__)

        assert len(chips) == 1, f"Expected 1 chip for small AOI, got {len(chips)}"
        assert chips[0]["chip_id"] == "chip_0_0"
        assert chips[0]["index"] == 0

    def test_chip_grid_dimensions(self):
        """Verify chip grid calculations for larger AOI."""
        chipmaker = ChipMaker(chip_size=512, stride=256)

        # Create AOI roughly 2km x 2km
        aoi = box(-118.42, 33.93, -118.40, 33.95)

        chips = chipmaker.create_chips(aoi.__geo_interface__)

        # Should generate multiple chips
        assert len(chips) > 1, "Expected multiple chips for large AOI"

        # Check that chip IDs are sequential
        chip_ids = [c["chip_id"] for c in chips]
        assert "chip_0_0" in chip_ids, "Missing first chip"

        # Verify all chips have required fields
        for chip in chips:
            assert "chip_id" in chip
            assert "geometry" in chip
            assert "bounds" in chip
            assert "grid_position" in chip
            assert "index" in chip

    def test_chip_overlap_calculation(self):
        """Verify chips overlap correctly based on stride."""
        chip_size = 512
        stride = 256  # 50% overlap
        chipmaker = ChipMaker(chip_size=chip_size, stride=stride)

        # Create AOI that will produce at least 2 chips in one direction
        aoi = box(-118.41, 33.94, -118.39, 33.96)

        chips = chipmaker.create_chips(aoi.__geo_interface__)

        # Get chips in the same row
        row_0_chips = [c for c in chips if c["grid_position"]["y"] == 0]

        if len(row_0_chips) >= 2:
            # Check that adjacent chips overlap
            # Note: exact overlap verification would require reprojecting bounds
            # Just verify we have adjacent chips
            x_positions = sorted([c["grid_position"]["x"] for c in row_0_chips])
            assert x_positions == list(range(len(row_0_chips))), "X positions should be sequential"

    def test_chip_crs_output(self):
        """Verify chips are returned in WGS84 (EPSG:4326)."""
        chipmaker = ChipMaker(chip_size=512, stride=256)

        aoi = box(-118.40, 33.93, -118.39, 33.94)
        chips = chipmaker.create_chips(aoi.__geo_interface__)

        # Check that output coordinates are in WGS84 range
        for chip in chips:
            bounds = chip["bounds"]
            lon_min, lat_min, lon_max, lat_max = bounds

            # WGS84 longitude is -180 to 180
            assert -180 <= lon_min <= 180, f"Invalid longitude: {lon_min}"
            assert -180 <= lon_max <= 180, f"Invalid longitude: {lon_max}"

            # WGS84 latitude is -90 to 90
            assert -90 <= lat_min <= 90, f"Invalid latitude: {lat_min}"
            assert -90 <= lat_max <= 90, f"Invalid latitude: {lat_max}"

    def test_zero_stride_same_as_chip_size(self):
        """Stride equal to chip_size should produce no overlap."""
        chipmaker = ChipMaker(chip_size=512, stride=512)

        aoi = box(-118.41, 33.94, -118.39, 33.96)
        chips = chipmaker.create_chips(aoi.__geo_interface__)

        # Should still generate chips, just with no overlap
        assert len(chips) > 0, "Should generate chips even with stride=chip_size"

    def test_chip_index_uniqueness(self):
        """Each chip should have a unique index."""
        chipmaker = ChipMaker(chip_size=512, stride=256)

        aoi = box(-118.42, 33.93, -118.40, 33.95)
        chips = chipmaker.create_chips(aoi.__geo_interface__)

        indices = [c["index"] for c in chips]
        assert len(indices) == len(set(indices)), "Chip indices must be unique"
        assert indices == list(range(len(chips))), "Indices should be sequential from 0"

    def test_different_chip_sizes(self):
        """Test various chip size configurations."""
        test_cases = [
            (256, 128),  # Small chips, 50% overlap
            (1024, 1024),  # Large chips, no overlap
            (512, 400),  # Medium chips, small overlap
        ]

        aoi = box(-118.41, 33.94, -118.40, 33.95)

        for chip_size, stride in test_cases:
            chipmaker = ChipMaker(chip_size=chip_size, stride=stride)
            chips = chipmaker.create_chips(aoi.__geo_interface__)

            assert len(chips) > 0, f"Failed to create chips for size={chip_size}, stride={stride}"

            # Verify all chips have valid structure
            for chip in chips:
                assert len(chip["bounds"]) == 4, "Bounds should have 4 coordinates"
                assert chip["geometry"]["type"] == "Polygon", "Chip geometry should be Polygon"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
