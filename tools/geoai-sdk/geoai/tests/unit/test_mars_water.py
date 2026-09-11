"""
Unit tests for the MARS Water category and spec metadata (map_render, geometry types).
"""

import numpy as np
import pytest

from geoai.core.models.payload_builder import PayloadBuilder
from geoai.core.models.spec_loader import ModelSpecLoader


@pytest.fixture
def mars_spec():
    return ModelSpecLoader.load("microsoft/mars-map-autoregressive")


class TestMarsSpecWater:
    def test_water_in_default_categories(self, mars_spec):
        defaults = mars_spec["parameters"]["categories"]["default"]
        assert "Water" in defaults
        assert defaults == ["Building", "Road", "Railway", "Water"]

    def test_water_in_request_format(self, mars_spec):
        assert "Water" in mars_spec["foundry_api"]["request_format"]["categories"]

    def test_category_geometry_types(self, mars_spec):
        geom = mars_spec["category_geometry_types"]
        assert geom["Water"] == "Polygon"
        assert geom["Building"] == "Polygon"
        assert geom["Road"] == "LineString"
        assert geom["Railway"] == "LineString"

    def test_map_render_section(self, mars_spec):
        render = mars_spec["map_render"]
        assert render["endpoint_path"] == "/map:render"
        assert render["payload_format"] == "multipart"
        assert render["output_format"] == "png"
        assert set(render["themes"]) == {"default", "dark", "standard_oil", "streets"}
        params = render["parameters"]
        assert params["coordinate_space"]["enum"] == ["geographic", "pixel"]


class TestMarsPayloadCategories:
    """PayloadBuilder should pass Water through to the endpoint payload."""

    @staticmethod
    def _rgb_array():
        # (C, H, W) uint8 RGB image
        return np.zeros((3, 8, 8), dtype=np.uint8)

    def test_omitting_categories_lets_server_default(self, mars_spec):
        # When no categories are passed, the SDK omits the field and the
        # endpoint applies its own defaults (which now include Water).
        builder = PayloadBuilder(mars_spec["foundry_api"])
        payload = builder.build(images=[self._rgb_array()], params={})
        assert "categories" not in payload
        assert "image" in payload

    def test_explicit_water_category(self, mars_spec):
        builder = PayloadBuilder(mars_spec["foundry_api"])
        payload = builder.build(images=[self._rgb_array()], params={"categories": ["Water"]})
        assert payload["categories"] == ["Water"]
        assert "image" in payload


class TestMarsModelRenderThemes:
    def test_render_themes(self, mars_spec):
        from geoai.public.models.mars import MARS

        model = MARS(endpoint="https://mars.inference.ml.azure.com/score", credential="k")
        assert set(model.render_themes) == {"default", "dark", "standard_oil", "streets"}
