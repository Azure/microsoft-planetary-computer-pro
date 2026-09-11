"""
geoai.public.models.mars

MARS - Map generation and object detection model.
"""

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from geoai.core.models.spec_loader import ModelSpecLoader
from geoai.executors.local import LocalExecutor
from geoai.public.aoi_constraint import Constraint
from geoai.public.models.base import BaseModel
from geoai.public.run_result import RunResult
from geoai.shared.exceptions import ValidationError

logger = logging.getLogger(__name__)


class MARS(BaseModel):
    """
    MARS - Map generation and Building/Road/Railway/Water extraction model.

    Specialized for:
    - Building footprints (Polygon)
    - Road network extraction (LineString)
    - Railway extraction (LineString)
    - Water segmentation (Polygon)

    In addition to ``run()`` (vector extraction via ``/score``), MARS exposes
    ``render_map()`` to rasterize imagery + GeoJSON features into a styled
    cartographic basemap PNG via the ``/map:render`` endpoint.

    Example:
        >>> model = geoai.models.MARS(
        ...     endpoint="https://mars.ai.azure.com",
        ...     credential=credential
        ... )
        >>>
        >>> result = await model.run(
        ...     input=input,
        ...     constraint=constraint,
        ...     params={"chip_size": 512, "categories": ["Building", "Water"]},
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
            - categories: list (optional) - Filter to specific categories.
              Available: ["Building", "Road", "Railway", "Water"]. Building and
              Water are returned as polygons; Road and Railway as lines.
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

    @property
    def render_themes(self) -> List[str]:
        """
        List the cartographic theme presets supported by ``/map:render``.

        :return: List of theme names (e.g. ["default", "dark", "standard_oil", "streets"])
        """
        return list(self.spec.get("map_render", {}).get("themes", []))

    async def render_map(
        self,
        image: Union[bytes, str, Path],
        geojson: Union[bytes, str, Path, Dict, List],
        tile_size: int = 1024,
        coordinate_space: str = "geographic",
        theme: str = "default",
        color_map: Optional[Dict[str, str]] = None,
        timeout: float = 300.0,
    ) -> bytes:
        """
        Render a styled cartographic basemap PNG from imagery + GeoJSON features.

        Uses the MARS ``/map:render`` endpoint (derived automatically from this
        model's scoring endpoint). This is a stateless call: pass an image and
        the GeoJSON features to rasterize, and receive PNG bytes back.

        :param image: GeoTIFF image as bytes or a path to a ``.tif`` file.
        :param geojson: GeoJSON FeatureCollection / list of features as a dict,
            list, JSON string, bytes, or a path to a ``.geojson`` file. Use the
            output of a MARS run, or the raw ``/score`` output with
            ``coordinate_space="pixel"``.
        :param tile_size: Output tile size in pixels (longer side). Default: 1024.
        :param coordinate_space: ``"geographic"`` for georeferenced features
            (e.g. run output) or ``"pixel"`` for raw ``/score`` pixel-space
            output. Default: "geographic".
        :param theme: Named cartographic theme preset. See ``render_themes``.
            Default: "default".
        :param color_map: Optional mapping of category name to hex color that
            overrides the built-in palette (e.g. ``{"Water": "#1a6fb0"}``).
        :param timeout: Read timeout in seconds. Default: 300.
        :return: Rendered PNG image as bytes.

        Example:
            >>> png = await model.render_map(
            ...     image="chip.tif",
            ...     geojson=score_output,
            ...     coordinate_space="pixel",
            ...     theme="streets",
            ... )
            >>> Path("basemap.png").write_bytes(png)
        """
        from geoai.core.models.map_renderer import MapRenderer

        renderer = MapRenderer(
            endpoint=self.endpoint,
            credential=self.credential,
            model_spec=self.spec,
        )

        return await renderer.render(
            image=image,
            geojson=geojson,
            tile_size=tile_size,
            coordinate_space=coordinate_space,
            theme=theme,
            color_map=color_map,
            timeout=timeout,
        )
