"""
geoai.public.models.base

BaseModel - Abstract base class for all models.
"""

import logging
import os
from abc import ABC, abstractmethod
from math import ceil
from typing import Any, Dict, List, Optional

import geopandas as gpd
from shapely.geometry import box, shape

from geoai.core.models.spec_loader import ModelSpecLoader
from geoai.core.stac.resolution_detector import detect_resolution
from geoai.core.stac.searcher import STACSearcher
from geoai.public.estimate_result import EstimateResult
from geoai.shared.exceptions import ValidationError, ValidationResult
from geoai.shared.url_utils import is_trusted_domain

logger = logging.getLogger(__name__)


class BaseModel(ABC):
    """
    BaseModel - Abstract base class for all GeoAI models.

    All models inherit from this class and implement the run() method.

    This ensures a consistent interface across all models:
    - EOOS, MARS (AOI-based models)
    """

    # Subclasses must define this
    model_id: str = None
    _spec_cache: Dict[str, Any] = {}

    @classmethod
    def _load_spec(cls) -> Dict[str, Any]:
        """Load model specification (cached)."""
        if not cls.model_id:
            raise NotImplementedError(f"{cls.__name__} must define model_id")

        if cls.model_id not in cls._spec_cache:
            cls._spec_cache[cls.model_id] = ModelSpecLoader.load(cls.model_id)

        return cls._spec_cache[cls.model_id]

    @classmethod
    def get_supported_collections(cls) -> List[str]:
        """
        Get list of supported collections for this model.

        Returns:
            List of collection names (e.g., ['naip', 'sentinel-2-l2a'])

        Example:
            >>> from geoai import models
            >>> print(models.EOOS.get_supported_collections())
            ['naip', 'sentinel-2-l2a']
        """
        spec = cls._load_spec()
        return spec.get("data_requirements", {}).get("supported_collections", [])

    @classmethod
    def get_requirements(cls) -> Dict[str, Any]:
        """
        Get full data requirements for this model.

        Returns:
            Dictionary with required_bands, supported_collections, resolution, etc.

        Example:
            >>> from geoai import models
            >>> requirements = models.EOOS.get_requirements()
            >>> print(requirements['required_bands'])
            ['red', 'green', 'blue']
        """
        spec = cls._load_spec()
        return spec.get("data_requirements", {})

    @classmethod
    def get_info(cls) -> Dict[str, Any]:
        """
        Get model information (name, description, requirements).

        Returns:
            Dictionary with model metadata

        Example:
            >>> from geoai import models
            >>> info = models.EOOS.get_info()
            >>> print(info['model_name'])
            'EO-OS Object Detection'
        """
        spec = cls._load_spec()
        return {
            "model_id": spec.get("model_id"),
            "model_name": spec.get("model_name"),
            "model_type": spec.get("model_type"),
            "description": spec.get("description"),
            "data_requirements": spec.get("data_requirements", {}),
        }

    def _validate_input_compatibility(self, input) -> None:
        """
        Validate that Input is compatible with this model.

        Checks:
        - Collection is in supported_collections (only for Planetary Computer)

        Note: Collection validation only applies to public Planetary Computer.
        Private GeoCatalogs can use any collection name.

        Raises:
            ValueError: If input is incompatible
        """
        if not input.collection:
            raise ValueError(f"{self.__class__.__name__} requires input.collection to be specified")

        # Only validate collection names for Planetary Computer
        # Private GeoCatalogs can use custom collection names
        is_planetary_computer = is_trusted_domain(input.geocatalog_uri, ["planetarycomputer.microsoft.com"])

        if is_planetary_computer:
            supported = self.__class__.get_supported_collections()
            if input.collection not in supported:
                raise ValueError(
                    f"Collection '{input.collection}' is not supported by {self.__class__.__name__} on Planetary Computer.\n"
                    f"Supported Planetary Computer collections: {supported}\n"
                    f"Note: You can use custom collections with private GeoCatalogs.\n"
                    f"Hint: Use {self.__class__.__name__}.get_supported_collections() to see available options."
                )

    def __init__(
        self, endpoint: str, credential, num_instances: int = 1, concurrent_per_instance: int = 1
    ):
        """
        Initialize base model.

        :param endpoint: AI Foundry endpoint URL
        :param credential: Azure credential or API key
        :param num_instances: Number of deployed endpoint instances (default: 1)
        :param concurrent_per_instance: Max concurrent requests per instance (default: 1)

        Concurrency Calculation:
            inference_concurrent = num_instances × concurrent_per_instance
            fetch_concurrent = inference_concurrent × 2 (internal multiplier)

        The SDK uses a two-stage pipeline:
        - Stage 1 (Fetch/Preprocess): 2× chips prepared in parallel (automatic)
        - Stage 2 (Inference): Matches endpoint capacity, keeps endpoint saturated

        Examples:
            # Development (default): 1 inference, 2 fetch/preprocess
            model = EOOS(endpoint="...", credential=...)

            # Production: 15 inference, 30 fetch/preprocess
            model = EOOS(endpoint="...", credential=...,
                        num_instances=3, concurrent_per_instance=5)

            # High-throughput: 30 inference, 60 fetch/preprocess
            model = EOOS(endpoint="...", credential=...,
                        num_instances=3, concurrent_per_instance=10)

        Note: Configure these based on your Azure ML/AI Foundry deployment:
        - num_instances: Check your deployment's instance count
        - concurrent_per_instance: Check endpoint documentation for max concurrent requests
        """
        if not endpoint:
            raise ValueError("endpoint is required")

        if not credential:
            raise ValueError("credential is required")

        if num_instances < 1:
            raise ValueError("num_instances must be >= 1")

        if concurrent_per_instance < 1:
            raise ValueError("concurrent_per_instance must be >= 1")

        self.endpoint = endpoint
        self.credential = credential
        self.num_instances = num_instances
        self.concurrent_per_instance = concurrent_per_instance

        # Calculate concurrency limits
        # Internal multiplier of 2 balances performance and memory usage
        self.max_concurrent_requests = num_instances * concurrent_per_instance
        self.fetch_concurrent = min(
            self.max_concurrent_requests * 2, 40
        )  # Cap at 40 for memory safety

    @abstractmethod
    async def run(self, input, constraint, params: Dict[str, Any], output):
        """
        Run model inference.

        :param input: Input data source configuration
        :param constraint: Spatial/temporal constraints
        :param params: Model-specific parameters
        :param output: Output destination configuration
        :return: RunResult
        """
        raise NotImplementedError("Subclasses must implement run()")

    def _validate_bands_available(
        self, stac_item, required_bands: List[str]
    ) -> tuple[bool, List[str]]:
        """
        Validate that required bands are available in STAC item.

        :param stac_item: STAC item (pystac Item or dict)
        :param required_bands: List of required band names
        :return: (all_found: bool, found_bands: List[str])
        """
        found_bands = []

        # Handle pystac Item objects
        if hasattr(stac_item, "assets"):
            assets = stac_item.assets
        # Handle dict
        elif isinstance(stac_item, dict):
            assets = stac_item.get("assets", {})
        else:
            return False, []

        # Check for RGB bands specifically
        if required_bands == ["red", "green", "blue"]:
            # Option 1: "image" asset with 4 bands (NAIP style)
            if "image" in assets:
                found_bands = ["red", "green", "blue"]
                return True, found_bands
            # Option 2: Separate band assets
            for band in required_bands:
                if band in assets:
                    found_bands.append(band)
        else:
            # General case: check each required band
            for band in required_bands:
                if band in assets:
                    found_bands.append(band)

        all_found = len(found_bands) == len(required_bands)
        return all_found, found_bands

    def _validate_resolution_compatible(self, detected_resolution: float) -> tuple[bool, List[str]]:
        """
        Validate that detected resolution is compatible with model requirements.

        :param detected_resolution: Detected resolution in meters/pixel
        :return: (is_valid: bool, warnings: List[str])
        """
        warnings = []

        # Get resolution range from model spec
        resolution_range = self.spec.get("data_requirements", {}).get("resolution_range_meters")

        if not resolution_range:
            # No range specified, accept any resolution
            return True, warnings

        min_res = resolution_range.get("min", 0)
        max_res = resolution_range.get("max", float("inf"))
        optimal_res = resolution_range.get("optimal")

        # Check if outside acceptable range
        if detected_resolution < min_res:
            return False, [
                f"Resolution {detected_resolution}m is too fine (min: {min_res}m). Model may not perform well."
            ]
        if detected_resolution > max_res:
            return False, [
                f"Resolution {detected_resolution}m is too coarse (max: {max_res}m). Model may not perform well."
            ]

        # Check if suboptimal but acceptable
        if optimal_res and abs(detected_resolution - optimal_res) > 0.4:
            warnings.append(
                f"Resolution {detected_resolution}m differs from optimal {optimal_res}m. "
                f"Results may be suboptimal."
            )

        return True, warnings

    def _calculate_estimated_duration(
        self, total_chips: int, chip_size: int, num_aois: int = 1
    ) -> float:
        """
        Calculate estimated execution duration in seconds using empirical benchmarks.

        Formula (tuned from production benchmark data):
            speedup = 1 + min(concurrent - 1, MAX_BENEFIT) × EFFICIENCY
            total_time = FIXED_OVERHEAD + (total_chips × time_per_chip / speedup)

        Where time_per_chip is measured empirically from sequential runs and includes
        all overhead (fetch, preprocess, inference, geocatalog publishing).

        Benchmark data (41 chips @ 1024px):
            - Sequential (1 worker): 270s → 5.5s per chip
            - Parallel (10 workers): 175s → 1.68x speedup
            - Parallel (20 workers): 200s → 1.35x speedup (diminishing returns)

        :param total_chips: Total number of chips to process
        :param chip_size: Chip size in pixels (512, 1024, or 2048)
        :param num_aois: Number of AOIs (not used, kept for compatibility)
        :return: Estimated duration in seconds
        """
        import math

        from ...shared.performance_config import (
            EMPIRICAL_TIME_PER_CHIP_EOOS,
            EMPIRICAL_TIME_PER_CHIP_MARS,
            FIXED_OVERHEAD_SECONDS,
            FIXED_OVERHEAD_SECONDS_MARS,
            MAX_PARALLELISM_BENEFIT,
            PARALLELISM_EFFICIENCY,
        )

        # Select model-specific constants
        if hasattr(self, 'model_id') and 'mars' in self.model_id.lower():
            time_per_chip_table = EMPIRICAL_TIME_PER_CHIP_MARS
            fixed_overhead = FIXED_OVERHEAD_SECONDS_MARS
        else:
            time_per_chip_table = EMPIRICAL_TIME_PER_CHIP_EOOS
            fixed_overhead = FIXED_OVERHEAD_SECONDS

        # Get time per chip for this chip size
        if chip_size in time_per_chip_table:
            time_per_chip = time_per_chip_table[chip_size]
        else:
            # Interpolate/extrapolate for non-standard sizes
            # Linear interpolation between known sizes
            if chip_size < 512:
                time_per_chip = time_per_chip_table[512] * (chip_size / 512)
            elif chip_size > 2048:
                time_per_chip = time_per_chip_table[2048] * (chip_size / 2048)
            else:
                # Interpolate between 512 and 1024 or 1024 and 2048
                if chip_size <= 1024:
                    ratio = (chip_size - 512) / (1024 - 512)
                    time_per_chip = (
                        time_per_chip_table[512] * (1 - ratio)
                        + time_per_chip_table[1024] * ratio
                    )
                else:
                    ratio = (chip_size - 1024) / (2048 - 1024)
                    time_per_chip = (
                        time_per_chip_table[1024] * (1 - ratio)
                        + time_per_chip_table[2048] * ratio
                    )

        # Calculate parallelism speedup (empirical formula, not sqrt!)
        # speedup = 1 + min(additional_workers, cap) × efficiency
        concurrent = max(1, self.max_concurrent_requests)
        additional_workers = concurrent - 1
        capped_workers = min(additional_workers, MAX_PARALLELISM_BENEFIT)
        parallelism_speedup = 1.0 + (capped_workers * PARALLELISM_EFFICIENCY)

        # Calculate processing time with parallelism
        processing_time = (total_chips * time_per_chip) / parallelism_speedup

        # Total duration (GeoCatalog overhead is included in time_per_chip)
        total_duration = fixed_overhead + processing_time

        return total_duration

    async def validate_input(
        self, input, constraint, params: Optional[Dict[str, Any]] = None, output=None
    ) -> ValidationResult:
        """
        Validate input, constraint, parameters, model endpoint, and optionally output.

        This validation check verifies:
        - Input: Collection compatibility, imagery availability, bands, resolution
        - Constraint: AOI format, spatial/temporal constraints
        - Parameters: Valid ranges and types
        - Model Endpoint: Authentication and accessibility
        - Output: GeoCatalog and blob storage access

        :param input: Input data source configuration
        :param constraint: Spatial/temporal constraints
        :param params: Model-specific parameters (optional)
        :param output: Output destination configuration (optional, recommended)
        :return: ValidationResult with is_valid, errors, warnings, and detected data

        Example:
            >>> # Validate everything before running (recommended)
            >>> validation = await model.validate_input(input, constraint, params, output)
            >>> if not validation.is_valid:
            ...     print(f"Errors: {validation.errors}")
            ...     exit()
            >>> print(f"✓ Model endpoint authentication validated")
            >>> print(f"✓ Output destination accessible")
        """
        errors = []
        warnings = []
        detected_resolution = None
        bands_found = None
        stac_items_count = None

        # 1. Validate input source (endpoint, auth, collection exists)
        try:
            input_validation = await input.validate()
            errors.extend(input_validation.errors)
            warnings.extend(input_validation.warnings)
        except Exception as e:
            errors.append(f"Input validation failed: {str(e)}")

        # 2. Validate collection compatibility with model
        try:
            self._validate_input_compatibility(input)
        except ValueError as e:
            errors.append(str(e))
        except Exception as e:
            errors.append(f"Collection compatibility check failed: {str(e)}")

        # 3. Validate filter compatibility with collection
        if hasattr(constraint, "filter") and constraint.filter:
            filter_validation = self._validate_filter_compatibility(input, constraint)
            warnings.extend(filter_validation)

        # 4. Validate constraint type
        from geoai.public.aoi_constraint import Constraint

        if not isinstance(constraint, Constraint):
            errors.append(f"Expected Constraint, got {type(constraint).__name__}")

        # 5. Validate AOI format (can parse bbox/geometry/aois)
        try:
            if constraint.mode == "multi" and constraint.aois is not None:
                # Try to load AOIs to verify format
                if isinstance(constraint.aois, str):
                    # File path - check it exists and can be read
                    if not os.path.exists(constraint.aois):
                        errors.append(f"AOI file not found: {constraint.aois}")
                    else:
                        # Try to peek at file format
                        try:
                            import geopandas as gpd

                            if constraint.aois.endswith((".parquet", ".geoparquet")):
                                _ = gpd.read_parquet(constraint.aois)
                            else:
                                _ = gpd.read_file(constraint.aois)
                        except Exception as e:
                            errors.append(f"Cannot read AOI file: {str(e)}")
        except Exception as e:
            errors.append(f"AOI validation failed: {str(e)}")

        # 6. Validate parameters (if provided)
        if params:
            try:
                param_validation = self._validate_parameters(params)
                errors.extend(param_validation["errors"])
                warnings.extend(param_validation["warnings"])
            except Exception as e:
                errors.append(f"Parameter validation failed: {str(e)}")

        # 7. Query STAC to validate imagery availability, bands, and resolution
        # Only proceed if no critical errors so far
        if len(errors) == 0:
            try:
                from shapely.geometry import box, shape

                # Get geometry for first AOI (for multi-AOI, validate first one as sample)
                if constraint.mode == "single":
                    if constraint.bbox:
                        geometry = box(*constraint.bbox)
                    else:
                        geometry = constraint.geometry
                else:
                    # Multi-AOI: get first AOI from iterator
                    first_aoi = next(constraint.iter_aois(), None)
                    if first_aoi is None:
                        errors.append("No AOIs found in constraint")
                        geometry = None
                    else:
                        # Convert GeoJSON geometry dict to shapely geometry
                        if isinstance(first_aoi["geometry"], dict):
                            geometry = shape(first_aoi["geometry"])
                        else:
                            geometry = first_aoi["geometry"]

                if geometry is not None:
                    # Query STAC for sample
                    stac_items, stac_succeeded = await self._search_stac(
                        input, constraint, geometry
                    )

                    if not stac_succeeded:
                        errors.append("STAC search failed - unable to query catalog")
                    elif not stac_items or len(stac_items) == 0:
                        errors.append(
                            f"No imagery found for AOI in collection '{input.collection}' "
                            f"with datetime '{constraint.datetime}'"
                        )
                    else:
                        stac_items_count = len(stac_items)
                        logger.info(f"Found {stac_items_count} STAC items for validation")

                        # Detect resolution
                        detected_resolution = self._detect_resolution(stac_items)
                        logger.info(f"Detected resolution: {detected_resolution}m/pixel")

                        # Validate resolution compatibility
                        resolution_valid, resolution_warnings = (
                            self._validate_resolution_compatible(detected_resolution)
                        )
                        if not resolution_valid:
                            errors.extend(resolution_warnings)
                        else:
                            warnings.extend(resolution_warnings)

                        # Validate bands availability
                        required_bands = self.spec.get("data_requirements", {}).get(
                            "required_bands", []
                        )
                        if required_bands:
                            first_item = stac_items[0]
                            bands_available, bands_found = self._validate_bands_available(
                                first_item, required_bands
                            )

                            if not bands_available:
                                missing_bands = set(required_bands) - set(bands_found)
                                errors.append(
                                    f"Collection '{input.collection}' missing required bands: {list(missing_bands)}. "
                                    f"Found bands: {bands_found}. Required: {required_bands}"
                                )
                            else:
                                logger.info(f"All required bands found: {bands_found}")

            except Exception as e:
                logger.exception(f"STAC validation failed: {e}")
                warnings.append(f"Unable to validate imagery availability: {str(e)}")

        # 8. Validate model endpoint authentication
        # Only proceed if no critical errors so far
        if len(errors) == 0:
            try:
                from geoai.core.models.model_client import ModelClient

                # Create temporary client for validation
                temp_client = ModelClient(
                    endpoint=self.endpoint, credential=self.credential, model_spec=self.spec
                )

                is_valid, error_msg = await temp_client.validate_auth()
                if not is_valid:
                    errors.append(f"Model endpoint authentication failed: {error_msg}")
                else:
                    logger.info("✓ Model endpoint authentication validated successfully")

            except Exception as e:
                logger.warning(f"Could not validate model endpoint: {e}")
                warnings.append(f"Unable to validate model endpoint authentication: {str(e)}")

        # 9. Validate output destination (NEW! - if provided)
        if output and len(errors) == 0:
            try:
                output_validation = await output.validate()
                errors.extend(output_validation.errors)
                warnings.extend(output_validation.warnings)

                if output_validation.is_valid:
                    logger.info("✓ Output destination validated successfully")

            except Exception as e:
                logger.warning(f"Could not validate output: {e}")
                warnings.append(f"Unable to validate output destination: {str(e)}")

        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            detected_resolution=detected_resolution,
            bands_found=bands_found,
            stac_items_count=stac_items_count,
        )

    def _validate_filter_compatibility(self, input, constraint) -> List[str]:
        """
        Validate that constraint filters are compatible with the collection.

        Returns list of warnings for incompatible filters.
        """
        warnings = []

        if not hasattr(constraint, "filter") or not constraint.filter:
            return warnings

        filter_dict = constraint.filter
        collection = input.collection.lower() if input.collection else ""

        # NAIP doesn't support cloud cover filters (aerial imagery, not satellite)
        if collection == "naip":
            filter_str = str(filter_dict).lower()
            if "cloud_cover" in filter_str or "eo:cloud_cover" in filter_str:
                warnings.append(
                    "Cloud cover filter will be ignored for NAIP collection. "
                    "NAIP is aerial imagery without cloud metadata. "
                    "Cloud cover filters only work with satellite collections (Sentinel, Landsat)."
                )

        return warnings

    def _validate_parameters(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate model parameters.

        Returns dict with 'errors' and 'warnings' lists.
        """
        errors = []
        warnings = []

        # Validate chip_size
        if "chip_size" in params:
            chip_size = params["chip_size"]
            if not isinstance(chip_size, int):
                errors.append(f"chip_size must be integer, got {type(chip_size).__name__}")
            elif chip_size < 128 or chip_size > 4096:
                warnings.append(f"chip_size={chip_size} is outside typical range [128-4096]")
            elif chip_size % 64 != 0:
                warnings.append(
                    f"chip_size={chip_size} is not a multiple of 64 (may cause model issues)"
                )

        # Validate stride
        if "stride" in params:
            stride = params["stride"]
            chip_size = params.get("chip_size", 512)
            if not isinstance(stride, int):
                errors.append(f"stride must be integer, got {type(stride).__name__}")
            elif stride < 1:
                errors.append(f"stride must be positive, got {stride}")
            elif stride > chip_size:
                warnings.append(
                    f"stride ({stride}) > chip_size ({chip_size}) will create gaps between chips"
                )

        # Validate threshold (if present)
        if "threshold" in params:
            threshold = params["threshold"]
            if not isinstance(threshold, (int, float)):
                errors.append(f"threshold must be numeric, got {type(threshold).__name__}")
            elif threshold < 0.0 or threshold > 1.0:
                errors.append(f"threshold must be in range [0.0, 1.0], got {threshold}")

        return {"errors": errors, "warnings": warnings}

    async def estimate(self, input, constraint, params: Dict[str, Any]) -> EstimateResult:
        """
        Estimate model execution scope before running.

        Performs validation and STAC search to verify data availability and calculates
        estimated chip count based on AOI geometry and parameters.

        :param input: Input data source configuration
        :param constraint: Spatial/temporal constraints (single or multi-AOI)
        :param params: Model parameters (chip_size, stride)
        :return: EstimateResult with STAC items, chip estimates, and warnings

        Example:
            >>> estimate = await model.estimate(input, constraint, params)
            >>> print(estimate)
            >>> if estimate.stac_items_found == 0:
            ...     print("No imagery found!")
            >>> else:
            ...     result = await model.run(input, constraint, params, output)
        """
        # Validate input first (fast checks without STAC search)
        validation_result = await self.validate_input(input, constraint, params)
        if not validation_result.is_valid:
            raise ValidationError(
                f"Input validation failed:\n"
                + "\n".join(f"  - {err}" for err in validation_result.errors),
                validation_result,
            )

        # Log warnings if any
        for warning in validation_result.warnings:
            logger.warning(warning)

        # Get chip parameters
        chip_size = params.get("chip_size", 512)
        stride = params.get("stride", chip_size)  # Default stride = chip_size (no overlap)

        # Check if single or multi-AOI
        if constraint.mode == "single":
            return await self._estimate_single_aoi(input, constraint, chip_size, stride)
        else:
            return await self._estimate_multi_aoi(input, constraint, chip_size, stride)

    async def _estimate_single_aoi(
        self, input, constraint, chip_size: int, stride: int
    ) -> EstimateResult:
        """Estimate for single AOI."""
        warnings = []

        # Get geometry
        if constraint.bbox:
            geometry = box(*constraint.bbox)
        else:
            geometry = constraint.geometry

        # Calculate area
        area_km2 = self._calculate_area_km2(geometry)

        # Perform STAC search
        stac_items, stac_succeeded = await self._search_stac(input, constraint, geometry)

        # Detect resolution from STAC items and convert pixels to meters
        resolution_m_per_px = self._detect_resolution(stac_items)
        chip_size_m = chip_size * resolution_m_per_px
        stride_m = stride * resolution_m_per_px

        # Calculate chips using converted meter values (pass both chip_size and stride)
        estimated_chips = self._calculate_chips(geometry, stride_m, chip_size_m)

        # Warnings
        if stac_items == 0:
            warnings.append("No STAC items found for this AOI/datetime range")
        if estimated_chips > 1000:
            warnings.append(f"Large job ({estimated_chips} chips) may take significant time")
        if area_km2 > 100:
            warnings.append(
                f"Large AOI ({area_km2:.1f} km²) - consider breaking into smaller areas"
            )

        # Calculate estimated duration
        estimated_duration = self._calculate_estimated_duration(
            estimated_chips, chip_size=chip_size, num_aois=1
        )

        return EstimateResult(
            stac_items_found=len(stac_items) if stac_items else 0,
            stac_search_succeeded=stac_succeeded,
            stac_items_summary=[
                self._summarize_stac_item(item) for item in (stac_items or [])[:10]
            ],
            aoi_area_km2=area_km2,
            total_aois=1,
            estimated_chips=estimated_chips,
            chip_size_meters=int(chip_size_m),
            stride_meters=int(stride_m),
            total_requests=estimated_chips,
            concurrent_requests=self.max_concurrent_requests,
            estimated_duration_minutes=ceil(estimated_duration / 60),
            aoi_estimates=[],
            warnings=warnings,
        )

    async def _estimate_multi_aoi(
        self, input, constraint, chip_size: int, stride: int
    ) -> EstimateResult:
        """Estimate for multi-AOI."""
        total_items = 0
        total_chips = 0
        total_area = 0.0
        aoi_estimates = []
        warnings = []
        all_items_summary = []
        all_searches_succeeded = True

        # Iterate through AOIs
        for aoi in constraint.iter_aois():
            aoi_id = aoi.get("id", "unknown")
            geometry_dict = aoi["geometry"]

            # Convert to shapely geometry if needed
            if isinstance(geometry_dict, dict):
                geometry = shape(geometry_dict)
            else:
                geometry = geometry_dict

            # Calculate area
            area_km2 = self._calculate_area_km2(geometry)
            total_area += area_km2

            # Perform STAC search for this AOI
            stac_items, stac_succeeded = await self._search_stac(input, constraint, geometry)

            # Detect resolution per AOI (different AOIs may have different resolutions)
            resolution_m_per_px = 0.6  # Default fallback
            if stac_items:
                resolution_m_per_px = self._detect_resolution(stac_items)

            if not stac_succeeded:
                all_searches_succeeded = False
                warnings.append(f"STAC search failed for AOI {aoi_id}")

            item_count = len(stac_items) if stac_items else 0
            total_items += item_count

            # Collect item summaries (limit to avoid too much data)
            if stac_items and len(all_items_summary) < 20:
                all_items_summary.extend(
                    [
                        self._summarize_stac_item(item)
                        for item in stac_items[: min(5, 20 - len(all_items_summary))]
                    ]
                )

            # Convert pixels to meters and calculate chips for this AOI (using per-AOI resolution)
            chip_size_m = chip_size * resolution_m_per_px
            stride_m = stride * resolution_m_per_px
            chips = self._calculate_chips(geometry, stride_m, chip_size_m)
            total_chips += chips

            # Warning if no items for this AOI
            if item_count == 0:
                warnings.append(f"No STAC items found for AOI {aoi_id}")

            # Per-AOI estimate (includes resolution for this specific AOI)
            aoi_estimates.append(
                {
                    "aoi_id": aoi_id,
                    "area_km2": area_km2,
                    "stac_items": item_count,
                    "estimated_chips": chips,
                    "resolution_m_per_px": resolution_m_per_px,
                }
            )

        # Overall warnings
        if total_chips > 5000:
            warnings.append(
                f"Very large job ({total_chips} chips across {len(aoi_estimates)} AOIs)"
            )

        # Use detected resolution or default for final calculations
        if resolution_m_per_px is None:
            resolution_m_per_px = 0.6
        chip_size_m = chip_size * resolution_m_per_px
        stride_m = stride * resolution_m_per_px

        # Calculate estimated duration (num_aois affects GeoCatalog write time)
        estimated_duration = self._calculate_estimated_duration(
            total_chips, chip_size=chip_size, num_aois=len(aoi_estimates)
        )

        return EstimateResult(
            stac_items_found=total_items,
            stac_search_succeeded=all_searches_succeeded,
            stac_items_summary=all_items_summary,
            aoi_area_km2=total_area,
            total_aois=len(aoi_estimates),
            estimated_chips=total_chips,
            chip_size_meters=int(chip_size_m),
            stride_meters=int(stride_m),
            total_requests=total_chips,
            concurrent_requests=self.max_concurrent_requests,
            estimated_duration_minutes=ceil(estimated_duration / 60),
            aoi_estimates=aoi_estimates,
            warnings=warnings,
        )

    async def _search_stac(self, input, constraint, geometry) -> tuple[List[Dict], bool]:
        """Perform STAC search for a geometry."""
        try:
            from shapely.geometry import mapping

            searcher = STACSearcher(
                geocatalog_uri=input.geocatalog_uri,
                collection=input.collection,
                credential=input.credential,
            )

            # Check for STAC pass-through mode
            if hasattr(constraint, "stac_search") and constraint.stac_search is not None:
                logger.info("Using pre-built STAC search for estimation")
                items = await searcher.search_from_external(constraint.stac_search)
            else:
                # Convert shapely geometry to GeoJSON dict
                geojson_geometry = mapping(geometry)

                # Extract bbox if available (faster query)
                bbox = getattr(constraint, "bbox", None)

                items = await searcher.search(
                    geometry=geojson_geometry,
                    bbox=bbox,
                    datetime=constraint.datetime,
                    filter=constraint.filter,
                )

            return items, True
        except Exception as e:
            logger.warning(f"STAC search failed: {e}")
            return None, False

    def _calculate_area_km2(self, geometry) -> float:
        """Calculate area in square kilometers (rough estimate)."""
        if hasattr(geometry, "bounds"):
            minx, miny, maxx, maxy = geometry.bounds
            # Rough conversion using degrees to km at equator
            width_km = (maxx - minx) * 111
            height_km = (maxy - miny) * 111
            return width_km * height_km
        return 0.0

    def _calculate_chips(self, geometry, stride: int, chip_size: int = None) -> int:
        """
        Calculate estimated number of chips for a geometry.
        Uses Web Mercator projection (same as chipmaker) for accuracy.

        :param geometry: Shapely geometry (WGS84)
        :param stride: Stride in meters
        :param chip_size: Chip size in meters (defaults to stride if not provided)
        :return: Estimated number of chips
        """
        if chip_size is None:
            chip_size = stride

        if hasattr(geometry, "bounds"):
            # Project to Web Mercator (EPSG:3857) for accurate meter-based measurements
            # This matches what chipmaker does
            gdf = gpd.GeoDataFrame(geometry=[geometry], crs="EPSG:4326")
            geometry_projected = gdf.to_crs("EPSG:3857").geometry.iloc[0]
            minx, miny, maxx, maxy = geometry_projected.bounds

            width_m = maxx - minx
            height_m = maxy - miny

            # Use the same formula as chipmaker for consistency:
            # x_steps = max(1, ceil((width - chip_size) / stride) + 1)
            num_chips_x = max(1, ceil((width_m - chip_size) / stride) + 1)
            num_chips_y = max(1, ceil((height_m - chip_size) / stride) + 1)

            logger.info(
                f"Chip estimation: {width_m:.1f}m × {height_m:.1f}m AOI, "
                f"chip={chip_size}m, stride={stride}m → {num_chips_x}×{num_chips_y} = {num_chips_x * num_chips_y} chips"
            )

            return num_chips_x * num_chips_y
        return 1

    def _detect_resolution(self, stac_items) -> float:
        """
        Detect native resolution from STAC items.
        Delegates to shared resolution detector utility.

        :param stac_items: List of STAC items
        :return: Resolution in meters per pixel
        """
        # Use shared resolution detector utility (no collection name available here)
        return detect_resolution(stac_items, collection_name=None)

    def _summarize_stac_item(self, item: Any) -> Dict[str, Any]:
        """Create summary of STAC item."""
        # Handle both pystac Item objects and dicts
        if hasattr(item, "id"):
            # pystac Item object
            return {
                "id": item.id,
                "datetime": item.datetime.isoformat() if item.datetime else "unknown",
                "cloud_cover": (
                    item.properties.get("eo:cloud_cover") if hasattr(item, "properties") else None
                ),
            }
        else:
            # Dict
            return {
                "id": item.get("id", "unknown"),
                "datetime": item.get("properties", {}).get("datetime", "unknown"),
                "cloud_cover": item.get("properties", {}).get("eo:cloud_cover"),
            }

    def __repr__(self):
        return f"{self.__class__.__name__}(endpoint='{self.endpoint}')"
