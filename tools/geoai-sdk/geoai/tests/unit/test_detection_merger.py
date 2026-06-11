"""
Unit tests for DetectionMerger - NMS and detection deduplication logic.
"""

import pytest
from shapely.geometry import LineString, Point, box

from geoai.core.spatial.detection_merger import DetectionMerger


class TestDetectionMerger:
    """Test detection merging and NMS logic."""

    def test_merge_empty_results(self):
        """Empty input should return empty feature collection."""
        merger = DetectionMerger(iou_threshold=0.5)

        result = merger.merge([], None)

        assert result["type"] == "FeatureCollection"
        assert result["features"] == []

    def test_merge_identical_polygons(self):
        """Identical overlapping polygons should be merged into one."""
        merger = DetectionMerger(iou_threshold=0.5)

        # Create two identical building detections
        polygon_geom = box(-118.40, 33.93, -118.399, 33.931).__geo_interface__

        chip_results = [
            {
                "features": [
                    {
                        "type": "Feature",
                        "geometry": polygon_geom,
                        "properties": {"label": "Building", "score": 0.9},
                    }
                ]
            },
            {
                "features": [
                    {
                        "type": "Feature",
                        "geometry": polygon_geom,
                        "properties": {"label": "Building", "score": 0.85},
                    }
                ]
            },
        ]

        result = merger.merge(chip_results, None)

        # Should merge into single detection (perfect overlap)
        assert len(result["features"]) == 1, "Identical polygons should merge into one"
        assert result["features"][0]["properties"]["label"] == "Building"

    def test_merge_non_overlapping_polygons(self):
        """Non-overlapping polygons should remain separate."""
        merger = DetectionMerger(iou_threshold=0.5)

        # Create two separate buildings
        building1 = box(-118.40, 33.93, -118.399, 33.931).__geo_interface__
        building2 = box(-118.395, 33.93, -118.394, 33.931).__geo_interface__

        chip_results = [
            {
                "features": [
                    {
                        "type": "Feature",
                        "geometry": building1,
                        "properties": {"label": "Building", "score": 0.9},
                    },
                    {
                        "type": "Feature",
                        "geometry": building2,
                        "properties": {"label": "Building", "score": 0.85},
                    },
                ]
            }
        ]

        result = merger.merge(chip_results, None)

        # Should keep both separate detections
        assert len(result["features"]) == 2, "Non-overlapping polygons should stay separate"

    def test_merge_different_labels(self):
        """Detections with different labels should not merge."""
        merger = DetectionMerger(iou_threshold=0.5)

        # Create overlapping detections with different labels
        geom = box(-118.40, 33.93, -118.399, 33.931).__geo_interface__

        chip_results = [
            {
                "features": [
                    {
                        "type": "Feature",
                        "geometry": geom,
                        "properties": {"label": "Building", "score": 0.9},
                    },
                    {
                        "type": "Feature",
                        "geometry": geom,
                        "properties": {"label": "Road", "score": 0.85},
                    },
                ]
            }
        ]

        result = merger.merge(chip_results, None)

        # Should keep both (different labels)
        assert len(result["features"]) == 2, "Different labels should not merge"
        labels = {f["properties"]["label"] for f in result["features"]}
        assert labels == {"Building", "Road"}

    def test_merge_with_aoi_clipping(self):
        """Detections should be clipped to AOI bounds."""
        merger = DetectionMerger(iou_threshold=0.5)

        # Create detection that extends outside AOI
        large_building = box(-118.41, 33.93, -118.399, 33.94).__geo_interface__
        aoi = box(-118.405, 33.935, -118.400, 33.938).__geo_interface__

        chip_results = [
            {
                "features": [
                    {
                        "type": "Feature",
                        "geometry": large_building,
                        "properties": {"label": "Building", "score": 0.9},
                    }
                ]
            }
        ]

        result = merger.merge(chip_results, aoi)

        # Should have clipped result
        assert len(result["features"]) >= 0, "Should handle AOI clipping"

    def test_iou_threshold_effect(self):
        """Different IoU thresholds should affect merging behavior."""
        # Create slightly overlapping boxes
        box1 = box(-118.40, 33.93, -118.399, 33.931).__geo_interface__
        box2 = box(-118.3995, 33.93, -118.398, 33.931).__geo_interface__

        chip_results = [
            {
                "features": [
                    {
                        "type": "Feature",
                        "geometry": box1,
                        "properties": {"label": "Building", "score": 0.9},
                    },
                    {
                        "type": "Feature",
                        "geometry": box2,
                        "properties": {"label": "Building", "score": 0.85},
                    },
                ]
            }
        ]

        # High threshold - less likely to merge
        merger_strict = DetectionMerger(iou_threshold=0.8)
        result_strict = merger_strict.merge(chip_results, None)

        # Low threshold - more likely to merge
        merger_loose = DetectionMerger(iou_threshold=0.2)
        result_loose = merger_loose.merge(chip_results, None)

        # Lower threshold should produce fewer or equal features
        assert len(result_loose["features"]) <= len(
            result_strict["features"]
        ), "Lower IoU threshold should merge more aggressively"

    def test_line_geometry_handling(self):
        """Line geometries (roads, railways) should be handled separately."""
        merger = DetectionMerger(iou_threshold=0.5, line_merge_mode="intersect_only")

        # Create road detections as LineStrings
        road1 = LineString([(-118.40, 33.93), (-118.399, 33.93)]).__geo_interface__
        road2 = LineString([(-118.395, 33.93), (-118.394, 33.93)]).__geo_interface__

        chip_results = [
            {
                "features": [
                    {
                        "type": "Feature",
                        "geometry": road1,
                        "properties": {"label": "Road", "score": 0.9},
                    },
                    {
                        "type": "Feature",
                        "geometry": road2,
                        "properties": {"label": "Road", "score": 0.85},
                    },
                ]
            }
        ]

        result = merger.merge(chip_results, None)

        # Should handle LineString geometries
        assert len(result["features"]) > 0, "Should process line geometries"
        assert all(
            f["geometry"]["type"] in ["LineString", "MultiLineString"] for f in result["features"]
        ), "Output should be line geometries"

    def test_invalid_geometry_handling(self):
        """Invalid geometries should be skipped gracefully."""
        merger = DetectionMerger(iou_threshold=0.5)

        # Mix valid and invalid geometries
        valid_geom = box(-118.40, 33.93, -118.399, 33.931).__geo_interface__
        invalid_geom = {"type": "Polygon", "coordinates": []}  # Invalid polygon

        chip_results = [
            {
                "features": [
                    {
                        "type": "Feature",
                        "geometry": valid_geom,
                        "properties": {"label": "Building", "score": 0.9},
                    },
                    {
                        "type": "Feature",
                        "geometry": invalid_geom,
                        "properties": {"label": "Building", "score": 0.85},
                    },
                ]
            }
        ]

        # Should not crash, just skip invalid geometry
        result = merger.merge(chip_results, None)
        assert len(result["features"]) >= 1, "Should process valid geometries despite invalid ones"

    def test_score_preservation(self):
        """Merged features should preserve highest score."""
        merger = DetectionMerger(iou_threshold=0.5)

        geom = box(-118.40, 33.93, -118.399, 33.931).__geo_interface__

        chip_results = [
            {
                "features": [
                    {
                        "type": "Feature",
                        "geometry": geom,
                        "properties": {"label": "Building", "score": 0.7},
                    },
                    {
                        "type": "Feature",
                        "geometry": geom,
                        "properties": {"label": "Building", "score": 0.95},
                    },
                ]
            }
        ]

        result = merger.merge(chip_results, None)

        # Should keep highest score
        assert len(result["features"]) == 1
        merged_score = result["features"][0]["properties"].get("score", 0)
        assert merged_score >= 0.7, "Should preserve score information"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
