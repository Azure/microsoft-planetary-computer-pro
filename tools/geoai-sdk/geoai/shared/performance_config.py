"""
Performance estimation configuration for GeoAI SDK operations.

Values are empirically measured from production benchmark runs.
"""

# Time per chip (seconds, sequential processing)
EMPIRICAL_TIME_PER_CHIP_EOOS = {
    512: 2.5,
    1024: 5.5,
    2048: 11.0,
}

EMPIRICAL_TIME_PER_CHIP_MARS = {
    512: 4.6,
    1024: 18.0,
    2048: 36.0,
}

# Fixed overhead (seconds)
FIXED_OVERHEAD_SECONDS = 45.0
FIXED_OVERHEAD_SECONDS_MARS = 75.0

# Parallelism speedup: 1 + min(concurrent - 1, max_benefit) × efficiency
MAX_PARALLELISM_BENEFIT = 10
PARALLELISM_EFFICIENCY = 0.075

# Default performance estimates (seconds)
PERFORMANCE_DEFAULTS = {
    # Infrastructure operations (same for all models)
    "estimated_stac_search_seconds": 4.0,  # STAC catalog search per AOI
    "estimated_merge_seconds": 3.0,  # Imagery merging per AOI
    "estimated_geocatalog_collection_seconds": 25.0,  # GeoCatalog collection creation
    "estimated_geocatalog_item_seconds": 12.0,  # GeoCatalog item write (max per parallel batch)
    "geocatalog_item_batch_size": 50,  # Parallel batch size for item creation
    "estimated_per_request_seconds": 7.5,
}
