"""
geoai.public.models.mars

MARS - Map generation and object detection model.
"""

import logging
from typing import Any, Dict

from geoai.core.models.spec_loader import ModelSpecLoader
from geoai.executors.local import LocalExecutor
from geoai.public.aoi_constraint import Constraint
from geoai.public.models.base import BaseModel
from geoai.public.run_result import RunResult
from geoai.shared.exceptions import ValidationError

logger = logging.getLogger(__name__)


class MARS(BaseModel):
    """
    MARS - Map generation and Road/Area/Structure detection model.

    Specialized for:
    - Road network extraction
    - Building footprints
    - Land use classification

    Example:
        >>> model = geoai.models.MARS(
        ...     endpoint="https://mars.ai.azure.com",
        ...     credential=credential
        ... )
        >>>
        >>> result = await model.run(
        ...     input=input,
        ...     constraint=constraint,
        ...     params={"chip_size": 512, "threshold": 0.6},
        ...     output=output
        ... )
    """

    # Model specification ID
    model_id = "microsoft/mars-map-autoregressive"

    def __init__(
        self, endpoint: str, credential, num_instances: int = 1, concurrent_per_instance: int = 1
    ):
        """
        Initialize MARS model.

        :param endpoint: AI Foundry endpoint URL for MARS
        :param credential: Azure credential or API key
        :param num_instances: Number of deployed endpoint instances (default: 1)
        :param concurrent_per_instance: Max concurrent requests per instance (default: 1)

        Example:
            # Production deployment
            model = geoai.models.MARS(
                endpoint="https://mars.eastus.inference.ml.azure.com/score",
                credential=credential,
                num_instances=3,
                concurrent_per_instance=10
            )
        """
        super().__init__(endpoint, credential, num_instances, concurrent_per_instance)
        self.spec = ModelSpecLoader.load("microsoft/mars-map-autoregressive")
        self.executor = LocalExecutor()

    async def run(self, input, constraint: Constraint, params: Dict[str, Any], output) -> RunResult:
        """
        Run MARS model on AOI.

        :param input: Input data source (requires collection="naip" or similar)
        :param constraint: AOI constraint
        :param params: Model parameters:
            - chip_size: int (default: 512) - Chip size in pixels
            - stride: int (default: 512) - Stride in pixels
            - threshold: float (default: 0.6) - Confidence threshold
            - categories: list (optional) - Filter to specific categories ["Building", "Road", "Railway"]
        :param output: Output destination

        :return: RunResult with detection statistics
        :raises ValidationError: If input validation fails
        """
        # Validate input, constraint, and parameters
        logger.info("Validating input configuration...")
        validation_result = await self.validate_input(input, constraint, params)

        if not validation_result.is_valid:
            raise ValidationError(
                f"Input validation failed:\n"
                + "\n".join(f"  - {err}" for err in validation_result.errors),
                validation_result=validation_result,
            )

        # Log warnings (non-fatal)
        for warning in validation_result.warnings:
            logger.warning(warning)

        logger.info("✓ Input validation passed")

        # Constraint type already validated in validate_input()
        if not isinstance(constraint, Constraint):
            raise TypeError(f"MARS requires Constraint, got {type(constraint).__name__}")

        # Execute via LocalExecutor (handles both single and multi-AOI)
        result = await self.executor.execute(
            workflow_type="aoi_based",
            constraint=constraint,  # Pass full constraint object
            aoi_geometry=(
                constraint.geometry if constraint.mode == "single" else None
            ),  # For single AOI
            model_spec=self.spec,
            input_config={
                "geocatalog_uri": input.geocatalog_uri,
                "collection": input.collection,
                "credential": self.credential,
            },
            constraint_config={
                "datetime": constraint.datetime,
                "filter": constraint.filter,
                "stac_search": getattr(constraint, "stac_search", None),  # STAC pass-through
            },
            output_config={
                # GeoCatalog (required)
                "geocatalog_uri": output.geocatalog_uri,
                "collection_name": output.collection_name,
                "credential": output.credential,
                # Model endpoint
                "endpoint": self.endpoint,
                "endpoint_credential": self.credential,
                "model_name": "mars",
                # Blob storage (required for STAC assets)
                "storage_url": output.storage_url,
                "blob_container": output.blob_container,
                "storage_account_key": output.storage_account_key,
                "run_id": output.run_id,
                # Local output (opt-in)
                "save_local": output.save_local,
                "output_dir": output.output_dir,
                # Concurrency control
                "max_concurrent_requests": self.max_concurrent_requests,
                "fetch_concurrent": self.fetch_concurrent,
            },
            params=params,
        )

        return RunResult(result)
