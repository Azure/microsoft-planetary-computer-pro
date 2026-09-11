"""
geoai.public.run_result

RunResult classes - Model execution results returned to users.
"""

from typing import Any, Dict, Optional


class RunResult:
    """
    RunResult - Results from AOI-based model execution.

    Returned by EO-OS and MARS models after successful execution.

    Attributes:
        total_chips: Number of chips processed
        successful_chips: Number of successful chips
        failed_chips: Number of failed chips
        detection_count: Total number of detections (objects or features)
        merged_results: Merged GeoJSON FeatureCollection
        geocatalog_url: URL to view results in GeoCatalog (if published)
        output_url: Direct URL to results file
        output_path: Local file path where results were saved
        published: Whether results were successfully published to GeoCatalog
        run_id: Unique identifier for this run (user-provided or auto-generated)
        blob_base_path: Base path in blob storage for this run's artifacts

    Example:
        >>> result = model.run(input, constraint, params, output)
        >>> print(f"Processed {result.total_chips} chips")
        >>> print(f"Detected {result.detection_count} objects")
        >>> if result.published:
        >>>     print(f"View at: {result.geocatalog_url}")
    """

    def __init__(self, result_data: Dict[str, Any]):
        """
        Initialize RunResult from executor result data.

        :param result_data: Result dictionary from executor
        """
        # Check if multi-AOI result
        if result_data.get("mode") == "multi_aoi":
            # Aggregate results from all AOIs
            all_aoi_results = result_data.get("results", [])

            self.total_chips = sum(r["result"].get("total_chips", 0) for r in all_aoi_results)
            self.successful_chips = sum(
                r["result"].get("successful_chips", 0) for r in all_aoi_results
            )
            self.failed_chips = sum(r["result"].get("failed_chips", 0) for r in all_aoi_results)
            self.detection_count = sum(
                r["result"].get("detection_count", 0) for r in all_aoi_results
            )

            # Multi-AOI specific fields
            self.total_aois = result_data.get("total_aois", 0)
            self.successful_aois = result_data.get("successful_aois", 0)
            self.collection_name = result_data.get("collection_name", "")
            self.collection_bbox = result_data.get("collection_bbox", [])

            # No single merged_results for multi-AOI
            self.merged_results = None
            self.geocatalog_url = ""  # Multiple URLs, one per AOI
            self.output_url = ""
            self.output_path = ""
            self.published = any(r["result"].get("published", False) for r in all_aoi_results)
            self.run_id = ""
            self.blob_base_path = ""
        else:
            # Single AOI result
            self.total_chips = result_data.get("total_chips", 0)
            self.successful_chips = result_data.get("successful_chips", 0)
            self.failed_chips = result_data.get("failed_chips", 0)

            merged_results = result_data.get("merged_results", {})
            self.detection_count = len(merged_results.get("features", []))
            self.merged_results = merged_results

            self.geocatalog_url = result_data.get("geocatalog_url", "")
            self.output_url = result_data.get("output_url", "")
            self.output_path = result_data.get("output_path", "")  # Local file path
            self.published = result_data.get(
                "published", False
            )  # Whether results were published to GeoCatalog

            # Blob storage and run information
            self.run_id = result_data.get("run_id", "")
            self.blob_base_path = result_data.get("blob_base_path", "")

            # Multi-AOI fields set to None for single AOI
            self.total_aois = None
            self.successful_aois = None
            self.collection_name = None
            self.collection_bbox = None

        self._raw_result = result_data

    @property
    def success_rate(self) -> float:
        """Calculate success rate as percentage"""
        if self.total_chips == 0:
            return 0.0
        return (self.successful_chips / self.total_chips) * 100

    def __repr__(self):
        return (
            f"RunResult("
            f"chips={self.total_chips}, "
            f"detections={self.detection_count}, "
            f"success_rate={self.success_rate:.1f}%)"
        )
