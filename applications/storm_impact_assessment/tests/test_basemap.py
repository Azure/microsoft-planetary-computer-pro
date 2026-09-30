import json
from pathlib import Path
import sys
import subprocess
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.basemap import (
    ATTRIBUTION,
    LEAFLET_BRIDGE_JS,
    MAPLIBRE_CSS,
    MAPLIBRE_JS,
    STYLE_URL,
    add_basemap,
    repair_export,
)


LEGACY_MAP = """
<!doctype html>
<html><head>
<script src="https://cdn.jsdelivr.net/npm/leaflet@1.9.3/dist/leaflet.js"></script>
</head><body>
<script>
var tile_layer_abc123 = L.tileLayer(
    "https://basemaps.cartocdn.com/light_all/{z}/{x}/{y}.png",
    {
        "minZoom": 0,
        "maxZoom": 18,
        "maxNativeZoom": 18,
        "attribution": "CARTO",
    }
);
tile_layer_abc123.addTo(map_def456);
var stormData = [{"lat": 29, "lon": -85}];
</script>
</body></html>
"""


class BasemapTests(unittest.TestCase):
    def test_repair_preserves_embedded_results(self):
        repaired = repair_export(LEGACY_MAP)
        self.assertIn('var stormData = [{"lat": 29, "lon": -85}];', repaired)
        self.assertNotIn("cartocdn.com", repaired)
        self.assertIn(STYLE_URL, repaired)
        self.assertIn("L.maplibreGL(", repaired)
        self.assertIn("map.setMaxZoom(18)", repaired)
        self.assertIn(json.dumps(ATTRIBUTION), repaired)
        self.assertIn("map.attributionControl.addAttribution(", repaired)
        self.assertNotIn("tile_layer_abc123.addTo(map_def456)", repaired)
        self.assertEqual(
            repaired.split("var stormData =")[1],
            LEGACY_MAP.split("var stormData =")[1],
        )
        self.assertLess(repaired.index("clawpilotTheme"), repaired.index("leaflet.js"))
        self.assertLess(repaired.index("leaflet.js"), repaired.index(MAPLIBRE_JS))
        self.assertLess(repaired.index(MAPLIBRE_JS), repaired.index(LEAFLET_BRIDGE_JS))

    def test_repair_refuses_unrecognized_or_ambiguous_exports(self):
        for html in ("<html></html>", LEGACY_MAP + LEGACY_MAP, repair_export(LEGACY_MAP)):
            with self.subTest(html=html[:30]), self.assertRaises(ValueError):
                repair_export(html)

    def test_repair_refuses_missing_map(self):
        with self.assertRaises(ValueError):
            repair_export(LEGACY_MAP.replace("tile_layer_abc123.addTo(map_def456);", ""))

    def test_repair_refuses_incomplete_html(self):
        with self.assertRaises(ValueError):
            repair_export(LEGACY_MAP.replace("</head>", ""))

    def test_folium_loads_assets_once_and_initializes_after_map(self):
        import folium

        map_object = folium.Map(location=[29, -85], zoom_start=6, tiles=None)
        add_basemap(map_object)
        folium.Marker([29, -85]).add_to(map_object)
        folium.LayerControl().add_to(map_object)
        for _ in range(2):
            html = map_object.get_root().render()
            for asset in (MAPLIBRE_JS, MAPLIBRE_CSS, LEAFLET_BRIDGE_JS):
                self.assertEqual(html.count(asset), 1, asset)
            self.assertEqual(html.count(STYLE_URL), 1)
            self.assertNotIn("cartocdn.com", html)
            self.assertNotIn("gibs.earthdata.nasa.gov", html)
            self.assertLess(html.index("clawpilotTheme"), html.index("leaflet.js"))
            self.assertLess(html.index("leaflet.js"), html.index(MAPLIBRE_JS))
            self.assertLess(html.index("L.map("), html.index("L.maplibreGL("))
            self.assertIn(json.dumps(ATTRIBUTION), html)
            self.assertIn("errorMessage.textContent = message", html)
            self.assertIn("webglcontextlost", html)
            self.assertIn("L.marker(", html)
            self.assertIn("L.control.layers(", html)

    def test_cli_preserves_existing_files(self):
        script = Path(__file__).resolve().parents[1] / "scripts" / "basemap.py"
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "source.html"
            output = Path(directory) / "output.html"
            source.write_text(LEGACY_MAP, encoding="utf-8")
            output.write_text("existing export", encoding="utf-8")
            result = subprocess.run(
                [sys.executable, str(script), str(source), str(output)],
                capture_output=True, text=True,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("Basemap repair failed", result.stderr)
            self.assertEqual(source.read_text(encoding="utf-8"), LEGACY_MAP)
            self.assertEqual(output.read_text(encoding="utf-8"), "existing export")
            same_path = subprocess.run(
                [sys.executable, str(script), str(source), str(source)],
                capture_output=True, text=True,
            )
            self.assertNotEqual(same_path.returncode, 0)
            self.assertIn("preserve the original", same_path.stderr)

    def test_notebook_uses_shared_basemap(self):
        notebook = json.loads(
            (Path(__file__).resolve().parents[1] / "hurricane_forecast_infra_impact.ipynb")
            .read_text(encoding="utf-8")
        )
        source = "\n".join("".join(cell["source"]) for cell in notebook["cells"])
        self.assertIn("from scripts.basemap import add_basemap", source)
        self.assertIn("add_basemap(m)", source)
        self.assertIn("OpenFreeMap Positron", source)
        self.assertNotIn("basemaps.cartocdn.com", source)


if __name__ == "__main__":
    unittest.main()
