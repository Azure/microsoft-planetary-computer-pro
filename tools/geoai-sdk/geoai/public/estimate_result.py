"""
geoai.public.estimate_result

EstimateResult - Pre-run estimation results.
"""

import math
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class EstimateResult:
    """
    Pre-run estimation results for model execution.

    Provides visibility into job scope before committing to processing.
    Includes actual STAC search results to verify data availability.

    Attributes:
        stac_items_found: Total number of STAC items found across all AOIs
        stac_search_succeeded: Whether STAC search completed successfully
        aoi_area_km2: Total area in square kilometers across all AOIs
        total_aois: Number of AOIs (1 for single, N for multi-AOI)
        estimated_chips: Total estimated chip count across all AOIs
        chip_size_meters: Chip size in meters
        stride_meters: Stride in meters
        total_requests: Total inference requests (= chip count)
        concurrent_requests: Concurrent requests based on model config
        estimated_duration_minutes: Estimated total execution time in minutes (rounded up)
        stac_items_summary: List of STAC item summaries [{id, datetime, ...}]
        aoi_estimates: Per-AOI breakdown for multi-AOI (empty for single AOI)
        warnings: List of warning messages

    Example:
        >>> estimate = await model.estimate(input, constraint, params)
        >>> print(f"Found {estimate.stac_items_found} STAC items")
        >>> print(f"Estimated {estimate.estimated_chips} chips to process")
        >>> print(f"Will take ~{estimate.estimated_duration_minutes} minutes")
        >>> if estimate.warnings:
        ...     print(f"Warnings: {estimate.warnings}")
    """

    # Required fields (no defaults)
    stac_items_found: int
    stac_search_succeeded: bool
    aoi_area_km2: float
    total_aois: int
    estimated_chips: int
    chip_size_meters: int
    stride_meters: int
    total_requests: int
    concurrent_requests: int
    estimated_duration_minutes: int

    # Optional fields (with defaults)
    stac_items_summary: List[Dict[str, Any]] = field(default_factory=list)
    aoi_estimates: List[Dict[str, Any]] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    def __str__(self) -> str:
        """Human-readable summary of estimation."""
        lines = []
        lines.append("=" * 70)
        lines.append("Model Execution Estimate")
        lines.append("=" * 70)

        # AOI info
        if self.total_aois == 1:
            lines.append(f"Area: {self.aoi_area_km2:.2f} km²")
        else:
            lines.append(f"AOIs: {self.total_aois} areas totaling {self.aoi_area_km2:.2f} km²")

        # STAC results
        if self.stac_search_succeeded:
            lines.append(f"STAC items found: {self.stac_items_found}")
            if self.stac_items_found == 0:
                lines.append("  [WARNING] No imagery found for this AOI/datetime range")
        else:
            lines.append("  [ERROR] STAC search failed")

        # Processing estimates
        lines.append(f"\nProcessing Estimates:")
        lines.append(f"  Chip size: {self.chip_size_meters}m")
        lines.append(f"  Stride: {self.stride_meters}m")
        lines.append(f"  Estimated chips: {self.estimated_chips:,}")
        lines.append(f"  Inference requests: {self.total_requests:,}")
        lines.append(f"  Concurrent requests: {self.concurrent_requests}")

        if self.concurrent_requests > 0:
            parallel_rounds = (
                self.total_requests + self.concurrent_requests - 1
            ) // self.concurrent_requests
            lines.append(
                f"  ~{parallel_rounds:,} parallel rounds @ {self.concurrent_requests} concurrent"
            )

        # Duration estimate
        duration_hrs = self.estimated_duration_minutes / 60
        if duration_hrs >= 1:
            lines.append(f"  Estimated duration: ~{duration_hrs:.1f} hours")
        else:
            lines.append(f"  Estimated duration: ~{self.estimated_duration_minutes} minutes")

        # Per-AOI breakdown for multi-AOI
        if self.total_aois > 1 and self.aoi_estimates:
            lines.append(f"\nPer-AOI Breakdown:")
            for aoi_est in self.aoi_estimates[:5]:  # Show first 5
                lines.append(
                    f"  AOI {aoi_est['aoi_id']}: "
                    f"{aoi_est['area_km2']:.2f} km², "
                    f"{aoi_est['stac_items']} items, "
                    f"{aoi_est['estimated_chips']} chips"
                )
            if len(self.aoi_estimates) > 5:
                lines.append(f"  ... and {len(self.aoi_estimates) - 5} more AOIs")

        # Warnings
        if self.warnings:
            lines.append(f"\n[WARNING] Warnings:")
            for warning in self.warnings:
                lines.append(f"  • {warning}")

        lines.append("=" * 70)
        return "\n".join(lines)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "stac_items_found": self.stac_items_found,
            "stac_search_succeeded": self.stac_search_succeeded,
            "stac_items_summary": self.stac_items_summary,
            "aoi_area_km2": self.aoi_area_km2,
            "total_aois": self.total_aois,
            "estimated_chips": self.estimated_chips,
            "chip_size_meters": self.chip_size_meters,
            "stride_meters": self.stride_meters,
            "total_requests": self.total_requests,
            "concurrent_requests": self.concurrent_requests,
            "estimated_duration_minutes": self.estimated_duration_minutes,
            "aoi_estimates": self.aoi_estimates,
            "warnings": self.warnings,
        }
