"""
Unit tests for MapRenderer (MARS /map:render client) and shared auth helpers.
"""

import asyncio
import json
from pathlib import Path

import pytest

from geoai.core.models.map_renderer import MapRenderer
from geoai.core.models.spec_loader import ModelSpecLoader
from geoai.shared.auth import (
    AZURE_ML_SCOPE,
    COGNITIVE_SERVICES_SCOPE,
    build_auth_headers,
    get_auth_scope,
)


@pytest.fixture
def mars_spec():
    return ModelSpecLoader.load("microsoft/mars-map-autoregressive")


# ---------------------------------------------------------------------------
# Shared auth helpers
# ---------------------------------------------------------------------------


class TestAuthHelpers:
    def test_string_credential_is_bearer(self):
        headers = build_auth_headers("https://x.inference.ml.azure.com/score", "my-key")
        assert headers["Authorization"] == "Bearer my-key"

    def test_no_credential_returns_empty(self):
        assert build_auth_headers("https://x/score", None) == {}

    def test_azure_ml_scope(self):
        assert get_auth_scope("https://x.inference.ml.azure.com/score") == AZURE_ML_SCOPE

    def test_ai_foundry_scope(self):
        assert get_auth_scope("https://x.inference.ai.azure.com/score") == COGNITIVE_SERVICES_SCOPE

    def test_credential_object_uses_scope(self):
        class FakeToken:
            token = "abc123"

        class FakeCredential:
            def __init__(self):
                self.scope = None

            def get_token(self, scope):
                self.scope = scope
                return FakeToken()

        cred = FakeCredential()
        headers = build_auth_headers("https://x.inference.ml.azure.com/score", cred)
        assert headers["Authorization"] == "Bearer abc123"
        assert cred.scope == AZURE_ML_SCOPE


# ---------------------------------------------------------------------------
# Endpoint URL derivation
# ---------------------------------------------------------------------------


class TestResolveRenderEndpoint:
    @pytest.mark.parametrize(
        "endpoint",
        [
            "https://mars.eastus.inference.ml.azure.com/score",
            "https://mars.eastus.inference.ml.azure.com/score/",
            "https://mars.eastus.inference.ml.azure.com",
            "https://mars.eastus.inference.ml.azure.com/",
            "https://mars.eastus.inference.ml.azure.com/map:render",
        ],
    )
    def test_derives_render_url(self, endpoint, mars_spec):
        renderer = MapRenderer(endpoint=endpoint, credential="k", model_spec=mars_spec)
        assert renderer.endpoint == "https://mars.eastus.inference.ml.azure.com/map:render"

    def test_requires_map_render_section(self):
        spec = {"model_id": "test/x", "map_render": {}}
        with pytest.raises(ValueError, match="does not declare a 'map_render'"):
            MapRenderer(endpoint="https://x/score", credential="k", model_spec=spec)

    def test_requires_endpoint(self, mars_spec):
        with pytest.raises(ValueError, match="endpoint is required"):
            MapRenderer(endpoint="", credential="k", model_spec=mars_spec)

    def test_exposes_supported_themes(self, mars_spec):
        renderer = MapRenderer(endpoint="https://x/score", credential="k", model_spec=mars_spec)
        assert set(renderer.supported_themes) == {"default", "dark", "standard_oil", "streets"}


# ---------------------------------------------------------------------------
# Input normalization
# ---------------------------------------------------------------------------


class TestInputNormalization:
    def test_image_bytes(self):
        data, name = MapRenderer._read_image_bytes(b"tiffbytes")
        assert data == b"tiffbytes"
        assert name.endswith(".tif")

    def test_image_path(self, tmp_path):
        p = tmp_path / "chip.tif"
        p.write_bytes(b"tiff-content")
        data, name = MapRenderer._read_image_bytes(str(p))
        assert data == b"tiff-content"
        assert name == "chip.tif"

    def test_image_missing_path(self):
        with pytest.raises(FileNotFoundError):
            MapRenderer._read_image_bytes("does/not/exist.tif")

    def test_geojson_dict(self):
        obj = {"type": "FeatureCollection", "features": []}
        out = MapRenderer._read_geojson_bytes(obj)
        assert json.loads(out) == obj

    def test_geojson_list(self):
        features = [{"type": "Feature", "geometry": None, "properties": {}}]
        out = MapRenderer._read_geojson_bytes(features)
        assert json.loads(out) == features

    def test_geojson_json_string(self):
        s = '{"type": "FeatureCollection", "features": []}'
        out = MapRenderer._read_geojson_bytes(s)
        assert json.loads(out) == json.loads(s)

    def test_geojson_path(self, tmp_path):
        p = tmp_path / "features.geojson"
        p.write_text('{"type": "FeatureCollection", "features": []}')
        out = MapRenderer._read_geojson_bytes(str(p))
        assert json.loads(out)["type"] == "FeatureCollection"

    def test_geojson_nonexistent_pathlike_string_raises(self):
        # A path-like string that doesn't exist and isn't valid JSON should fail
        # fast with a clear ValueError rather than being sent as garbage bytes.
        with pytest.raises(ValueError, match="neither an existing file path nor valid"):
            MapRenderer._read_geojson_bytes("features.geojson")

    def test_geojson_missing_path_object_raises(self):
        with pytest.raises(FileNotFoundError):
            MapRenderer._read_geojson_bytes(Path("does/not/exist.geojson"))


# ---------------------------------------------------------------------------
# render() validation + request building (mocked transport)
# ---------------------------------------------------------------------------


class _FakeResponse:
    def __init__(self, status_code=200, content=b"PNGDATA", text=""):
        self.status_code = status_code
        self.content = content
        self.text = text

    def raise_for_status(self):
        if self.status_code != 200:
            import httpx

            raise httpx.HTTPStatusError("error", request=None, response=self)


class _FakeAsyncClient:
    """Captures the outgoing request and returns a canned response."""

    captured = {}

    def __init__(self, *args, **kwargs):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return False

    async def post(self, url, files=None, data=None, headers=None):
        _FakeAsyncClient.captured = {
            "url": url,
            "files": files,
            "data": data,
            "headers": headers,
        }
        return _FakeResponse()


class TestRender:
    def _renderer(self, spec):
        return MapRenderer(
            endpoint="https://mars.eastus.inference.ml.azure.com/score",
            credential="secret-key",
            model_spec=spec,
        )

    def test_invalid_tile_size(self, mars_spec):
        r = self._renderer(mars_spec)
        with pytest.raises(ValueError, match="tile_size"):
            asyncio.run(r.render(image=b"x", geojson={}, tile_size=0))

    def test_invalid_coordinate_space(self, mars_spec):
        r = self._renderer(mars_spec)
        with pytest.raises(ValueError, match="coordinate_space"):
            asyncio.run(r.render(image=b"x", geojson={}, coordinate_space="latlon"))

    def test_invalid_theme(self, mars_spec):
        r = self._renderer(mars_spec)
        with pytest.raises(ValueError, match="Unknown theme"):
            asyncio.run(r.render(image=b"x", geojson={}, theme="rainbow"))

    def test_render_builds_request(self, mars_spec, monkeypatch):
        import geoai.core.models.map_renderer as mod

        monkeypatch.setattr(mod.httpx, "AsyncClient", _FakeAsyncClient)
        r = self._renderer(mars_spec)

        png = asyncio.run(
            r.render(
                image=b"tiffbytes",
                geojson={"type": "FeatureCollection", "features": []},
                tile_size=512,
                coordinate_space="pixel",
                theme="streets",
                color_map={"Water": "#1a6fb0"},
            )
        )

        assert png == b"PNGDATA"

        cap = _FakeAsyncClient.captured
        assert cap["url"] == "https://mars.eastus.inference.ml.azure.com/map:render"
        assert cap["data"]["tile_size"] == "512"
        assert cap["data"]["coordinate_space"] == "pixel"
        assert cap["data"]["theme"] == "streets"
        assert json.loads(cap["data"]["color_map"]) == {"Water": "#1a6fb0"}
        assert "image" in cap["files"] and "geojson" in cap["files"]
        assert cap["headers"]["Authorization"] == "Bearer secret-key"

    def test_render_omits_color_map_when_none(self, mars_spec, monkeypatch):
        import geoai.core.models.map_renderer as mod

        monkeypatch.setattr(mod.httpx, "AsyncClient", _FakeAsyncClient)
        r = self._renderer(mars_spec)

        asyncio.run(r.render(image=b"x", geojson=[], color_map=None))
        assert "color_map" not in _FakeAsyncClient.captured["data"]
