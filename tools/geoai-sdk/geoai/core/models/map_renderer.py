"""
geoai.core.models.map_renderer

MapRenderer - Client for the MARS ``/map:render`` endpoint.

The render endpoint rasterizes a georeferenced image (GeoTIFF) plus a set of
extracted GeoJSON features into a styled cartographic basemap PNG. It is a separate
endpoint from ``/score`` (which returns vector features) and is served by the
same deployment, so its URL is derived from the model's scoring endpoint.
"""

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import httpx

from geoai.shared.auth import build_auth_headers

logger = logging.getLogger(__name__)

# GeoJSON coordinate spaces accepted by the render endpoint
VALID_COORDINATE_SPACES = ("geographic", "pixel")

# Endpoint path suffixes that identify a scoring/inference endpoint and should be
# stripped before appending the render path.
_KNOWN_ENDPOINT_SUFFIXES = ("/map:render", "/map:extract", "/score")


class MapRenderer:
    """
    MapRenderer - Render styled cartographic basemap PNGs from imagery + GeoJSON.

    :param endpoint: Model endpoint URL. Accepts the scoring endpoint
        (e.g. ``https://mars.eastus.inference.ml.azure.com/score``), the base
        endpoint, or an explicit ``/map:render`` URL. The correct render URL is
        derived automatically.
    :param credential: API key (str) or Azure credential object.
    :param model_spec: Model specification dictionary (must contain a
        ``map_render`` section).

    Example:

      ```python
      spec = ModelSpecLoader.load("microsoft/mars-map-autoregressive")
      renderer = MapRenderer(
          endpoint="https://mars.eastus.inference.ml.azure.com/score",
          credential="api_key_or_credential",
          model_spec=spec,
      )

      png_bytes = await renderer.render(
          image="chip.tif",
          geojson=feature_collection,
          coordinate_space="pixel",
          theme="streets",
      )
      ```
    """

    def __init__(self, endpoint: str, credential: Any, model_spec: Dict):
        if not endpoint:
            raise ValueError("endpoint is required for MapRenderer")

        self.credential = credential
        self.spec = model_spec
        self.render_spec = model_spec.get("map_render", {}) or {}

        if not self.render_spec:
            raise ValueError(
                f"Model '{model_spec.get('model_id', 'unknown')}' does not declare a "
                "'map_render' section in its spec; the /map:render endpoint is not supported."
            )

        render_path = self.render_spec.get("endpoint_path", "/map:render")
        self.endpoint = self._resolve_render_endpoint(endpoint, render_path)
        self.supported_themes: List[str] = list(self.render_spec.get("themes", []))

        logger.info(f"Initialized MapRenderer, render endpoint: {self.endpoint}")

    @staticmethod
    def _resolve_render_endpoint(endpoint: str, render_path: str) -> str:
        """
        Derive the ``/map:render`` URL from a scoring or base endpoint URL.

        :param endpoint: Scoring, base, or render endpoint URL
        :param render_path: Render path from spec (e.g. ``/map:render``)
        :return: Fully-qualified render endpoint URL
        """
        cleaned = (endpoint or "").rstrip("/")

        # Already a render endpoint
        if cleaned.endswith(render_path):
            return cleaned

        # Strip a known scoring/inference suffix if present
        for suffix in _KNOWN_ENDPOINT_SUFFIXES:
            if cleaned.endswith(suffix):
                cleaned = cleaned[: -len(suffix)]
                break

        cleaned = cleaned.rstrip("/")
        return f"{cleaned}{render_path}"

    def _validate_theme(self, theme: str) -> None:
        if self.supported_themes and theme not in self.supported_themes:
            raise ValueError(
                f"Unknown theme '{theme}'. Supported themes: {sorted(self.supported_themes)}"
            )

    @staticmethod
    def _read_image_bytes(image: Union[bytes, str, Path]) -> tuple[bytes, str]:
        """Normalize the image input to (bytes, filename)."""
        if isinstance(image, bytes):
            return image, "image.tif"
        if isinstance(image, (str, Path)):
            path = Path(image)
            if not path.exists():
                raise FileNotFoundError(f"Image file not found: {path}")
            return path.read_bytes(), path.name
        raise TypeError(f"Unsupported image type: {type(image).__name__}. Expected bytes or path.")

    @staticmethod
    def _read_geojson_bytes(geojson: Union[bytes, str, Path, Dict, List]) -> bytes:
        """Normalize the GeoJSON input to raw JSON bytes."""
        if isinstance(geojson, bytes):
            return geojson
        if isinstance(geojson, (dict, list)):
            return json.dumps(geojson).encode("utf-8")
        if isinstance(geojson, (str, Path)):
            path = Path(geojson)
            # Treat as a filesystem path only when it actually exists; otherwise
            # assume the string is raw GeoJSON content.
            try:
                if path.exists():
                    return path.read_bytes()
            except OSError:
                pass
            if isinstance(geojson, Path):
                raise FileNotFoundError(f"GeoJSON file not found: {geojson}")
            # A non-existent string must be valid inline GeoJSON; otherwise a
            # mistyped path would be sent as garbage bytes and fail server-side
            # with an opaque error. Validate up front and fail clearly.
            try:
                json.loads(geojson)
            except json.JSONDecodeError as exc:
                raise ValueError(
                    f"geojson string is neither an existing file path nor valid JSON: {exc}"
                ) from exc
            return geojson.encode("utf-8")
        raise TypeError(
            f"Unsupported geojson type: {type(geojson).__name__}. "
            "Expected dict, list, bytes, JSON string, or path."
        )

    async def render(
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
        Render a basemap PNG from imagery and GeoJSON features.

        :param image: GeoTIFF image as bytes or a path to a ``.tif`` file.
        :param geojson: GeoJSON FeatureCollection / list of features as a dict,
            list, JSON string, bytes, or a path to a ``.geojson`` file.
        :param tile_size: Output tile size in pixels (longer side). Default: 1024.
        :param coordinate_space: Coordinate space of the GeoJSON geometries:
            ``"geographic"`` for georeferenced features (e.g. run output) or
            ``"pixel"`` for raw ``/score`` pixel-space output. Default: "geographic".
        :param theme: Named cartographic theme preset (e.g. ``"default"``,
            ``"dark"``, ``"standard_oil"``, ``"streets"``). Default: "default".
        :param color_map: Optional mapping of category name to hex color that
            overrides the built-in palette (e.g. ``{"Water": "#1a6fb0"}``).
        :param timeout: Read timeout in seconds. Default: 300.
        :return: Rendered PNG image as bytes.

        :raises ValueError: If arguments are invalid.
        :raises httpx.HTTPStatusError: If the endpoint returns an error.
        """
        if tile_size <= 0:
            raise ValueError("tile_size must be a positive integer")
        if coordinate_space not in VALID_COORDINATE_SPACES:
            raise ValueError(
                f"coordinate_space must be one of {VALID_COORDINATE_SPACES}, "
                f"got '{coordinate_space}'"
            )
        self._validate_theme(theme)

        image_bytes, image_filename = self._read_image_bytes(image)
        geojson_bytes = self._read_geojson_bytes(geojson)

        files = {
            "image": (image_filename, image_bytes, "image/tiff"),
            "geojson": ("features.geojson", geojson_bytes, "application/geo+json"),
        }
        data: Dict[str, str] = {
            "tile_size": str(tile_size),
            "coordinate_space": coordinate_space,
            "theme": theme,
        }
        if color_map is not None:
            data["color_map"] = json.dumps(color_map)

        headers = build_auth_headers(self.endpoint, self.credential)

        http_timeout = httpx.Timeout(connect=30.0, read=timeout, write=timeout, pool=30.0)

        logger.info(
            "Rendering map: endpoint=%s tile_size=%d coordinate_space=%s theme=%s",
            self.endpoint,
            tile_size,
            coordinate_space,
            theme,
        )

        async with httpx.AsyncClient(timeout=http_timeout) as client:
            response = await client.post(self.endpoint, files=files, data=data, headers=headers)

            if response.status_code != 200:
                logger.error(f"/map:render returned status {response.status_code}")
                logger.error(f"Response body: {response.text[:500]}")

            response.raise_for_status()

            return response.content
