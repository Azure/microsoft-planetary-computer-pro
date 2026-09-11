"""
geoai.core.spatial.detection_merger

DetectionMerger - Merge detection results across overlapping chips using NMS.
"""

from __future__ import annotations

import logging
from copy import deepcopy
from math import sqrt
from typing import Any, Dict, List

from shapely import make_valid
from shapely.errors import GEOSException
from shapely.geometry import LineString, MultiLineString, Point, mapping, shape
from shapely.ops import linemerge, unary_union

logger = logging.getLogger(__name__)


class DetectionMerger:
    """
    Merge overlapping detections from multiple chips.

    Areas (polygons) are deduplicated using IoU-based clustering.
    Lines support multiple merge modes for different use cases:
    - intersect_only: Only merge lines that physically intersect
    - targeted_endpoint_snap: Merge intersecting lines + snap compatible endpoints
    - seam_conflation: Pre-conflate near-parallel duplicate fragments before merging
    - road_cleanup: Specialized mode for road/railway network cleanup
    """

    def __init__(
        self,
        iou_threshold: float = 0.5,
        line_merge_mode: str = "intersect_only",
        line_snap_tolerance: float | None = None,
        min_line_length: float | None = None,
        prune_short_line_score_threshold: float | None = None,
        max_line_snap_tolerance: float = 2e-5,
        min_line_direction_alignment: float = 0.85,
        min_connector_alignment: float = 0.75,
    ):
        """
        Initialize DetectionMerger.

        :param iou_threshold: IoU threshold for area NMS (0.0-1.0)
        :param line_merge_mode: Line merge strategy - "intersect_only", "targeted_endpoint_snap",
                                "seam_conflation", or "road_cleanup"
        :param line_snap_tolerance: Optional endpoint snap tolerance in output CRS units
        :param min_line_length: Optional minimum line length for short-fragment pruning
        :param prune_short_line_score_threshold: Optional max score for pruning short fragments
        :param max_line_snap_tolerance: Upper bound for auto-calculated snap tolerance
        :param min_line_direction_alignment: Minimum cosine similarity between line tangents
        :param min_connector_alignment: Minimum cosine similarity between endpoint tangent and gap vector
        """
        self.iou_threshold = iou_threshold
        self.line_merge_mode = line_merge_mode
        self.line_snap_tolerance = line_snap_tolerance
        self.min_line_length = min_line_length
        self.prune_short_line_score_threshold = prune_short_line_score_threshold
        self.max_line_snap_tolerance = max_line_snap_tolerance
        self.min_line_direction_alignment = min_line_direction_alignment
        self.min_connector_alignment = min_connector_alignment

    def merge(self, chip_results: List[Dict], aoi_geometry: Dict) -> Dict:
        """
        Merge detection results from multiple chips using NMS.

        :param chip_results: List of chip result dicts with detections
        :param aoi_geometry: AOI geometry for clipping
        :return: Merged GeoJSON FeatureCollection
        """
        all_features = []
        for chip_result in chip_results:
            if "features" in chip_result:
                all_features.extend(chip_result["features"])
            elif "detections" in chip_result:
                all_features.extend(chip_result["detections"])

        if not all_features:
            return {"type": "FeatureCollection", "features": []}

        grouped_summary = self._summarize_input_groups(all_features)
        merged_features = self._merge_features(all_features, aoi_geometry)
        merged_summary = self._summarize_input_groups(merged_features)

        logger.info(
            "Merged %s detections from %s chips into %s features",
            len(all_features),
            len(chip_results),
            len(merged_features),
        )
        self._log_merge_summary(grouped_summary, merged_summary)

        return {"type": "FeatureCollection", "features": merged_features}

    def _merge_features(self, features: List[Dict], aoi_geometry: Dict) -> List[Dict]:
        """Group features by label and geometry family, then merge each group."""
        if not features:
            return []

        aoi_shape = self._normalize_geometry(shape(aoi_geometry)) if aoi_geometry else None
        grouped: Dict[tuple, List[Dict[str, Any]]] = {}

        for feature in features:
            geometry = feature.get("geometry")
            if not geometry:
                continue

            try:
                geom = self._normalize_geometry(shape(geometry))
            except Exception:
                logger.warning("Skipping invalid geometry during merge", exc_info=True)
                continue

            if geom is None or geom.is_empty:
                continue

            label = feature.get("properties", {}).get("label", "unknown")
            family = self._geometry_family(geom.geom_type)
            grouped.setdefault((label, family), []).append(
                {"feature": deepcopy(feature), "geometry": geom}
            )

        merged_features: List[Dict] = []
        for (_, family), members in grouped.items():
            if family == "area":
                merged_features.extend(self._merge_area_features(members, aoi_shape))
            elif family == "line":
                merged_features.extend(self._merge_line_features(members, aoi_shape))
            else:
                # Other geometry types: pass through as-is
                merged_features.extend([member["feature"] for member in members])

        return merged_features

    def _merge_area_features(self, members: List[Dict[str, Any]], aoi_shape) -> List[Dict]:
        """Merge area (polygon) features using IoU-based clustering."""
        merged = []
        consumed = set()

        for idx, member in enumerate(members):
            if idx in consumed:
                continue

            # Start a new cluster
            cluster = [idx]
            consumed.add(idx)
            changed = True

            # Grow cluster by adding overlapping polygons
            while changed:
                changed = False
                for other_idx, other in enumerate(members):
                    if other_idx in consumed:
                        continue
                    if any(
                        self._should_merge_areas(
                            members[cluster_idx]["geometry"], other["geometry"]
                        )
                        for cluster_idx in cluster
                    ):
                        cluster.append(other_idx)
                        consumed.add(other_idx)
                        changed = True

            # Merge all geometries in cluster
            cluster_members = [members[i] for i in cluster]
            union_geom = self._safe_unary_union([item["geometry"] for item in cluster_members])
            if union_geom is None:
                continue

            # Clip to AOI if provided
            if aoi_shape is not None:
                union_geom = self._safe_intersection(union_geom, aoi_shape)

            feature = self._build_merged_feature(cluster_members, union_geom)
            if feature:
                merged.append(feature)

        return merged

    def _merge_line_features(self, members: List[Dict[str, Any]], aoi_shape) -> List[Dict]:
        """Merge line features using mode-specific strategy."""
        raw_count = len(members)
        conflation_stats = None
        pre_merge_count = raw_count

        # Pre-conflation for seam_conflation and road_cleanup modes
        if self.line_merge_mode in {"seam_conflation", "road_cleanup"}:
            members, conflation_stats = self._conflate_line_members(members)
            pre_merge_count = len(members)

        merged = []
        consumed = set()

        for idx, member in enumerate(members):
            if idx in consumed:
                continue

            # Start a new cluster
            cluster = [idx]
            consumed.add(idx)
            changed = True

            # Grow cluster by adding intersecting/compatible lines
            while changed:
                changed = False
                for other_idx, other in enumerate(members):
                    if other_idx in consumed:
                        continue
                    if any(
                        self._should_merge_lines(
                            members[cluster_idx]["geometry"], other["geometry"]
                        )
                        for cluster_idx in cluster
                    ):
                        cluster.append(other_idx)
                        consumed.add(other_idx)
                        changed = True

            # Merge all line geometries in cluster
            cluster_members = [members[i] for i in cluster]
            union_geom = self._merge_line_cluster_geometries(
                [item["geometry"] for item in cluster_members]
            )
            if union_geom is None:
                continue

            # Apply Shapely's linemerge to join connected segments
            try:
                merged_geom = linemerge(union_geom)
            except Exception:
                merged_geom = union_geom

            # Clip to AOI if provided
            if aoi_shape is not None:
                merged_geom = self._safe_intersection(merged_geom, aoi_shape)

            feature = self._build_merged_feature(cluster_members, merged_geom)
            if feature:
                merged.append(feature)

        # Optional: prune short line fragments
        pre_prune_count = len(merged)
        pruned_count = 0
        if self.min_line_length is not None and self.prune_short_line_score_threshold is not None:
            merged = self._prune_short_line_features(merged)
            pruned_count = pre_prune_count - len(merged)

        # Log merge statistics
        if members:
            label = members[0]["feature"].get("properties", {}).get("label", "unknown")
            if conflation_stats is not None:
                logger.info(
                    "Line merge: label=%s raw=%s post_conflation=%s post_merge=%s final=%s mode=%s "
                    "pairs_considered=%s pairs_conflated=%s clusters=%s conflated_features=%s",
                    label,
                    raw_count,
                    pre_merge_count,
                    pre_prune_count,
                    len(merged),
                    self.line_merge_mode,
                    conflation_stats["pairs_considered"],
                    conflation_stats["pairs_conflated"],
                    conflation_stats["clusters_formed"],
                    conflation_stats["conflated_features"],
                )
            else:
                logger.info(
                    "Line merge: label=%s raw=%s post_merge=%s final=%s mode=%s",
                    label,
                    raw_count,
                    pre_prune_count,
                    len(merged),
                    self.line_merge_mode,
                )
            if pruned_count:
                logger.info("%s line pruning: pruned=%s", label, pruned_count)

        return merged

    def _should_merge_areas(self, geom1, geom2) -> bool:
        """Determine if two polygons should be merged based on IoU."""
        if not self._safe_intersects(geom1, geom2):
            return False

        intersection = self._safe_intersection(geom1, geom2)
        if intersection is None:
            return False
        intersection_area = intersection.area
        if intersection_area == 0:
            return False

        union_geom = self._safe_union(geom1, geom2)
        if union_geom is None:
            return False
        union_area = union_geom.area
        min_area = min(geom1.area, geom2.area)
        if union_area == 0 or min_area == 0:
            return False

        iou = intersection_area / union_area
        overlap_ratio = intersection_area / min_area
        return iou >= self.iou_threshold or overlap_ratio >= self.iou_threshold

    def _should_merge_lines(self, geom1, geom2) -> bool:
        """Determine if two lines should be merged based on mode and compatibility."""
        # Calculate adaptive buffer size based on spatial extent
        minx = min(geom1.bounds[0], geom2.bounds[0])
        miny = min(geom1.bounds[1], geom2.bounds[1])
        maxx = max(geom1.bounds[2], geom2.bounds[2])
        maxy = max(geom1.bounds[3], geom2.bounds[3])
        span = max(maxx - minx, maxy - miny, 1e-9)
        buffer_size = max(span * 0.001, 1e-9)

        # Check for intersection using buffered overlap
        if self._safe_intersects(geom1, geom2):
            buffered1 = geom1.buffer(buffer_size, cap_style=2, join_style=2)
            buffered2 = geom2.buffer(buffer_size, cap_style=2, join_style=2)
            if buffered1.is_empty or buffered2.is_empty:
                return False

            intersection = self._safe_intersection(buffered1, buffered2)
            if intersection is None:
                return False
            intersection_area = intersection.area
            min_area = min(buffered1.area, buffered2.area)
            if min_area == 0:
                return False

            overlap_ratio = intersection_area / min_area
            return overlap_ratio >= self.iou_threshold

        # For non-intersecting lines, only targeted modes support endpoint snapping
        if self.line_merge_mode not in {"targeted_endpoint_snap", "road_cleanup"}:
            return False

        snap_tolerance = self._get_line_snap_tolerance(geom1, geom2)
        endpoint_pair = self._find_compatible_endpoint_pair(geom1, geom2, snap_tolerance)
        return endpoint_pair is not None

    def _conflate_line_members(self, members: List[Dict[str, Any]]):
        """Pre-process lines to conflate near-parallel duplicates."""
        stats = {
            "pairs_considered": 0,
            "pairs_conflated": 0,
            "clusters_formed": 0,
            "conflated_features": 0,
            "rejected_angle": 0,
            "rejected_distance": 0,
            "rejected_overlap": 0,
        }
        if len(members) < 2:
            return members, stats

        # Build adjacency graph of conflatable line pairs
        adjacency = {idx: set() for idx in range(len(members))}
        conflation_metrics: Dict[tuple, Dict[str, float]] = {}

        for idx, member in enumerate(members):
            for other_idx in range(idx + 1, len(members)):
                other = members[other_idx]
                stats["pairs_considered"] += 1

                conflation_reason, rejection_reason = self._get_line_conflation_reason(
                    member["geometry"], other["geometry"]
                )

                if conflation_reason is not None:
                    adjacency[idx].add(other_idx)
                    adjacency[other_idx].add(idx)
                    conflation_metrics[(idx, other_idx)] = conflation_reason
                    stats["pairs_conflated"] += 1
                elif rejection_reason is not None:
                    stats[rejection_reason] += 1

        # Find connected components (clusters)
        reduced_members: List[Dict[str, Any]] = []
        visited = set()

        for idx in range(len(members)):
            if idx in visited:
                continue

            # DFS to find all members in this cluster
            stack = [idx]
            cluster = []
            while stack:
                current = stack.pop()
                if current in visited:
                    continue
                visited.add(current)
                cluster.append(current)
                stack.extend(adjacency[current] - visited)

            cluster_members = [members[cluster_idx] for cluster_idx in cluster]

            # Single-member cluster: pass through as-is
            if len(cluster_members) == 1:
                reduced_members.append(cluster_members[0])
                continue

            # Multi-member cluster: pick best representative
            stats["clusters_formed"] += 1
            best_member = max(
                cluster_members,
                key=lambda item: (
                    item["feature"].get("properties", {}).get("score", 0.0)
                    * max(item["geometry"].length, 1e-9),
                    item["geometry"].length,
                    item["feature"].get("properties", {}).get("score", 0.0),
                ),
            )

            feature = self._build_merged_feature(cluster_members, best_member["geometry"])
            if feature is None:
                continue

            properties = feature.setdefault("properties", {})
            merge_mode = (
                "road_cleanup" if self.line_merge_mode == "road_cleanup" else "seam_conflation"
            )
            properties["line_merge_mode"] = merge_mode
            properties["merged_from"] = len(cluster_members)
            stats["conflated_features"] += 1

            reduced_members.append(
                {
                    "feature": feature,
                    "geometry": best_member["geometry"],
                }
            )

        return reduced_members, stats

    def _get_line_conflation_reason(self, geom1, geom2):
        """Check if two lines should be conflated (near-parallel duplicates)."""
        line1 = self._get_primary_line(geom1)
        line2 = self._get_primary_line(geom2)
        if line1 is None or line2 is None:
            return None, None

        direction1 = self._line_direction(line1)
        direction2 = self._line_direction(line2)
        if direction1 is None or direction2 is None:
            return None, None

        # Check direction alignment (must be nearly parallel)
        direction_alignment = abs(self._dot_product(direction1, direction2))
        if direction_alignment < 0.95:
            return None, "rejected_angle"

        # Check lateral distance (must be close)
        distance_tolerance = self._get_line_snap_tolerance(geom1, geom2)
        lateral_distance = line1.distance(line2)
        if lateral_distance > distance_tolerance:
            return None, "rejected_distance"

        # Check projected overlap (must overlap significantly)
        overlap_ratio = self._projected_overlap_ratio(line1, line2, direction1, direction2)
        if overlap_ratio < 0.5:
            return None, "rejected_overlap"

        return {
            "distance": lateral_distance,
            "angle_alignment": direction_alignment,
            "overlap_ratio": overlap_ratio,
        }, None

    def _merge_line_cluster_geometries(self, geoms):
        """Merge multiple line geometries with optional endpoint snapping."""
        normalized = [self._normalize_geometry(geom) for geom in geoms]
        normalized = [geom for geom in normalized if geom is not None and not geom.is_empty]
        if not normalized:
            return None

        merged = normalized[0]
        for geom in normalized[1:]:
            # Apply endpoint snapping for targeted modes
            if self.line_merge_mode in {"targeted_endpoint_snap", "road_cleanup"}:
                tolerance = self._get_line_snap_tolerance(merged, geom)
                endpoint_pair = self._find_compatible_endpoint_pair(merged, geom, tolerance)
                if endpoint_pair is not None:
                    merged, geom = self._snap_endpoint_pair_to_midpoint(merged, geom, endpoint_pair)

            merged = self._safe_unary_union([merged, geom])
            if merged is None:
                return None

        return merged

    def _prune_short_line_features(self, features: List[Dict]) -> List[Dict]:
        """Remove short line fragments that lack confidence or neighbor support."""
        if self.min_line_length is None or not features:
            return features

        # Normalize geometries
        normalized = []
        for feature in features:
            geometry = feature.get("geometry")
            if not geometry:
                continue
            geom = self._normalize_geometry(shape(geometry))
            if geom is None or geom.is_empty:
                continue
            normalized.append((feature, geom))

        kept = []
        for feature, geom in normalized:
            label = feature.get("properties", {}).get("label")

            # Only prune Road and Railway features
            if label not in {"Road", "Railway"}:
                kept.append(feature)
                continue

            # Keep if longer than minimum
            if geom.length >= self.min_line_length:
                kept.append(feature)
                continue

            # Keep if high confidence score
            score = feature.get("properties", {}).get("score", 0.0)
            if (
                self.prune_short_line_score_threshold is not None
                and score > self.prune_short_line_score_threshold
            ):
                kept.append(feature)
                continue

            # Keep if connected to neighboring lines
            if self._line_has_neighbor_support(geom, normalized, feature):
                kept.append(feature)
                continue

        return kept

    def _line_has_neighbor_support(self, geom, normalized_features, current_feature: Dict) -> bool:
        """Check if a short line has neighboring lines within snap tolerance."""
        tolerance = self.line_snap_tolerance or self.max_line_snap_tolerance
        current_endpoints = self._get_line_endpoints(geom)

        for other_feature, other_geom in normalized_features:
            if other_feature is current_feature:
                continue
            for endpoint in current_endpoints:
                if endpoint["point"].distance(other_geom) <= tolerance:
                    return True

        return False

    def _get_line_snap_tolerance(self, geom1, geom2) -> float:
        """Calculate adaptive snap tolerance based on spatial extent."""
        if self.line_snap_tolerance is not None:
            return min(self.line_snap_tolerance, self.max_line_snap_tolerance)

        minx = min(geom1.bounds[0], geom2.bounds[0])
        miny = min(geom1.bounds[1], geom2.bounds[1])
        maxx = max(geom1.bounds[2], geom2.bounds[2])
        maxy = max(geom1.bounds[3], geom2.bounds[3])
        span = max(maxx - minx, maxy - miny, 1e-9)
        return min(max(span * 0.005, 1e-9), self.max_line_snap_tolerance)

    def _find_compatible_endpoint_pair(self, geom1, geom2, tolerance: float):
        """Find closest compatible endpoint pair within tolerance."""
        endpoints1 = self._get_line_endpoints(geom1)
        endpoints2 = self._get_line_endpoints(geom2)
        best_pair = None
        best_distance = None

        for point1 in endpoints1:
            for point2 in endpoints2:
                distance = point1["point"].distance(point2["point"])
                if distance > tolerance:
                    continue
                if not self._endpoint_pair_is_compatible(point1, point2, distance):
                    continue
                if best_distance is None or distance < best_distance:
                    best_pair = (point1, point2)
                    best_distance = distance

        return best_pair

    def _get_line_endpoints(self, geom) -> List[Dict[str, Any]]:
        """Extract endpoints with tangent vectors from line geometry."""
        endpoints = []
        for line_part_index, line in enumerate(self._iter_line_parts(geom)):
            coords = list(line.coords)
            if len(coords) < 2:
                continue
            endpoints.append(
                {
                    "line_part_index": line_part_index,
                    "position": "start",
                    "point": Point(coords[0]),
                    "tangent": self._normalize_vector(self._subtract_points(coords[1], coords[0])),
                }
            )
            endpoints.append(
                {
                    "line_part_index": line_part_index,
                    "position": "end",
                    "point": Point(coords[-1]),
                    "tangent": self._normalize_vector(
                        self._subtract_points(coords[-2], coords[-1])
                    ),
                }
            )
        return endpoints

    def _endpoint_pair_is_compatible(
        self, endpoint1: Dict[str, Any], endpoint2: Dict[str, Any], distance: float
    ) -> bool:
        """Check if two endpoints are geometrically compatible for snapping."""
        tangent1 = endpoint1["tangent"]
        tangent2 = endpoint2["tangent"]
        if tangent1 is None or tangent2 is None:
            return False

        # Check direction alignment
        direction_alignment = abs(self._dot_product(tangent1, tangent2))
        if direction_alignment < self.min_line_direction_alignment:
            return False

        if distance == 0:
            return True

        # Check connector alignment (gap vector should align with tangents)
        connector = self._normalize_vector(
            self._subtract_points(endpoint2["point"].coords[0], endpoint1["point"].coords[0])
        )
        if connector is None:
            return False

        alignment1 = abs(self._dot_product(tangent1, connector))
        alignment2 = abs(self._dot_product(tangent2, connector))
        return (
            alignment1 >= self.min_connector_alignment
            and alignment2 >= self.min_connector_alignment
        )

    def _snap_endpoint_pair_to_midpoint(self, geom1, geom2, endpoint_pair):
        """Snap two endpoints to their midpoint."""
        endpoint1, endpoint2 = endpoint_pair
        midpoint = (
            (endpoint1["point"].x + endpoint2["point"].x) / 2.0,
            (endpoint1["point"].y + endpoint2["point"].y) / 2.0,
        )
        updated_geom1 = self._replace_endpoint_coordinate(
            geom1, endpoint1["line_part_index"], endpoint1["position"], midpoint
        )
        updated_geom2 = self._replace_endpoint_coordinate(
            geom2, endpoint2["line_part_index"], endpoint2["position"], midpoint
        )
        return updated_geom1, updated_geom2

    def _replace_endpoint_coordinate(self, geom, line_part_index: int, position: str, new_coord):
        """Replace an endpoint coordinate in a line geometry."""
        if geom.geom_type == "LineString":
            coords = list(geom.coords)
            if position == "start":
                coords[0] = new_coord
            else:
                coords[-1] = new_coord
            return self._normalize_geometry(LineString(coords))

        if geom.geom_type == "MultiLineString":
            lines = []
            for idx, line in enumerate(geom.geoms):
                coords = list(line.coords)
                if idx == line_part_index:
                    if position == "start":
                        coords[0] = new_coord
                    else:
                        coords[-1] = new_coord
                lines.append(LineString(coords))
            return self._normalize_geometry(MultiLineString(lines))

        return geom

    def _get_primary_line(self, geom):
        """Get the longest line segment from a line geometry."""
        line_parts = list(self._iter_line_parts(geom))
        if not line_parts:
            return None
        return max(line_parts, key=lambda line: line.length)

    def _line_direction(self, line):
        """Calculate normalized direction vector of a line."""
        coords = list(line.coords)
        if len(coords) < 2:
            return None
        return self._normalize_vector(self._subtract_points(coords[-1], coords[0]))

    def _projected_overlap_ratio(self, line1, line2, direction1, direction2) -> float:
        """Calculate overlap ratio by projecting lines onto their average direction."""
        average_direction = self._normalize_vector(
            (
                direction1[0] + direction2[0],
                direction1[1] + direction2[1],
            )
        )
        if average_direction is None:
            average_direction = direction1

        projections1 = [self._project_point(coord, average_direction) for coord in line1.coords]
        projections2 = [self._project_point(coord, average_direction) for coord in line2.coords]
        min1, max1 = min(projections1), max(projections1)
        min2, max2 = min(projections2), max(projections2)
        overlap = min(max1, max2) - max(min1, min2)
        if overlap <= 0:
            return 0.0

        span1 = max1 - min1
        span2 = max2 - min2
        shorter_span = min(span1, span2)
        if shorter_span <= 0:
            return 0.0

        return overlap / shorter_span

    def _iter_line_parts(self, geom):
        """Iterate over line parts in LineString or MultiLineString."""
        if geom.geom_type == "LineString":
            yield geom
        elif geom.geom_type == "MultiLineString":
            for line in geom.geoms:
                yield line

    def _build_merged_feature(self, members: List[Dict[str, Any]], merged_geom) -> Dict | None:
        """Build a merged feature from cluster members with best properties."""
        merged_geom = self._normalize_geometry(merged_geom)
        if merged_geom is None or merged_geom.is_empty:
            return None

        # Use highest-scoring member as base
        best_member = max(
            members, key=lambda item: item["feature"].get("properties", {}).get("score", 0.0)
        )
        feature = deepcopy(best_member["feature"])
        properties = feature.setdefault("properties", {})

        # Collect chip IDs from all members
        chip_ids = []
        for member in members:
            chip_id = member["feature"].get("properties", {}).get("chip_id")
            if chip_id and chip_id not in chip_ids:
                chip_ids.append(chip_id)

        if chip_ids:
            properties["chip_ids"] = chip_ids
            if len(chip_ids) > 1:
                properties.pop("chip_id", None)

        feature["geometry"] = mapping(merged_geom)
        return feature

    def _geometry_family(self, geometry_type: str) -> str:
        """Classify geometry type into area/line/other family."""
        if geometry_type in {"Polygon", "MultiPolygon"}:
            return "area"
        if geometry_type in {"LineString", "MultiLineString"}:
            return "line"
        return "other"

    def _summarize_input_groups(self, features: List[Dict]) -> Dict[tuple, int]:
        """Summarize features by (label, geometry family) groups."""
        summary: Dict[tuple, int] = {}

        for feature in features:
            geometry = feature.get("geometry")
            if not geometry:
                continue

            try:
                geom = shape(geometry)
            except Exception:
                continue

            label = feature.get("properties", {}).get("label", "unknown")
            family = self._geometry_family(geom.geom_type)
            summary[(label, family)] = summary.get((label, family), 0) + 1

        return summary

    def _log_merge_summary(
        self, input_summary: Dict[tuple, int], output_summary: Dict[tuple, int]
    ) -> None:
        """Log before/after counts for each label/family group."""
        keys = sorted(set(input_summary) | set(output_summary))
        for label, family in keys:
            before = input_summary.get((label, family), 0)
            after = output_summary.get((label, family), 0)
            logger.info(
                "Merge summary: label=%s family=%s before=%s after=%s", label, family, before, after
            )

    def _subtract_points(self, point_a, point_b):
        """Vector subtraction."""
        return (point_a[0] - point_b[0], point_a[1] - point_b[1])

    def _project_point(self, point, direction) -> float:
        """Project point onto direction vector."""
        return (point[0] * direction[0]) + (point[1] * direction[1])

    def _normalize_vector(self, vector):
        """Normalize vector to unit length."""
        magnitude = sqrt(vector[0] ** 2 + vector[1] ** 2)
        if magnitude == 0:
            return None
        return (vector[0] / magnitude, vector[1] / magnitude)

    def _dot_product(self, vector1, vector2) -> float:
        """Calculate dot product of two vectors."""
        return vector1[0] * vector2[0] + vector1[1] * vector2[1]

    def _normalize_geometry(self, geom):
        """Repair and normalize geometry using make_valid."""
        if geom is None:
            return None

        try:
            normalized = make_valid(geom)
        except GEOSException:
            try:
                normalized = geom.buffer(0)
            except GEOSException:
                logger.warning("Failed to repair invalid geometry", exc_info=True)
                return None

        if normalized.is_empty:
            return None

        return normalized

    def _safe_intersects(self, geom1, geom2) -> bool:
        """Safe intersection test with fallback repair."""
        try:
            return geom1.intersects(geom2)
        except GEOSException:
            repaired1 = self._normalize_geometry(geom1)
            repaired2 = self._normalize_geometry(geom2)
            if repaired1 is None or repaired2 is None:
                return False
            try:
                return repaired1.intersects(repaired2)
            except GEOSException:
                return False

    def _safe_intersection(self, geom1, geom2):
        """Safe intersection with fallback repair."""
        try:
            return self._normalize_geometry(geom1.intersection(geom2))
        except GEOSException:
            repaired1 = self._normalize_geometry(geom1)
            repaired2 = self._normalize_geometry(geom2)
            if repaired1 is None or repaired2 is None:
                return None
            try:
                return self._normalize_geometry(repaired1.intersection(repaired2))
            except GEOSException:
                return None

    def _safe_union(self, geom1, geom2):
        """Safe union with fallback repair."""
        try:
            return self._normalize_geometry(geom1.union(geom2))
        except GEOSException:
            repaired1 = self._normalize_geometry(geom1)
            repaired2 = self._normalize_geometry(geom2)
            if repaired1 is None or repaired2 is None:
                return None
            try:
                return self._normalize_geometry(repaired1.union(repaired2))
            except GEOSException:
                return None

    def _safe_unary_union(self, geoms):
        """Safe unary union with fallback pairwise union."""
        normalized = [self._normalize_geometry(geom) for geom in geoms]
        normalized = [geom for geom in normalized if geom is not None and not geom.is_empty]
        if not normalized:
            return None

        try:
            return self._normalize_geometry(unary_union(normalized))
        except GEOSException:
            # Fallback: pairwise union
            merged = normalized[0]
            for geom in normalized[1:]:
                merged = self._safe_union(merged, geom)
                if merged is None:
                    return None
            return merged
