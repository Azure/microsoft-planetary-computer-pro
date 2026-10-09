"""OpenFreeMap Positron for Folium maps and legacy storm HTML exports."""

import argparse
import json
from pathlib import Path
import re

from branca.element import Element, Template
from folium.elements import JSCSSMixin


STYLE_URL = "https://tiles.openfreemap.org/styles/positron"
MAPLIBRE_JS = "https://cdn.jsdelivr.net/npm/maplibre-gl@5.24.0/dist/maplibre-gl.js"
MAPLIBRE_CSS = "https://cdn.jsdelivr.net/npm/maplibre-gl@5.24.0/dist/maplibre-gl.css"
LEAFLET_BRIDGE_JS = (
    "https://cdn.jsdelivr.net/npm/@maplibre/maplibre-gl-leaflet@0.1.4/leaflet-maplibre-gl.js"
)
ATTRIBUTION = (
    '<a href="https://openfreemap.org/">OpenFreeMap</a> | &copy; '
    '<a href="https://openmaptiles.org/">OpenMapTiles</a> | Data: &copy; '
    '<a href="https://www.openstreetmap.org/copyright">OpenStreetMap contributors</a> | '
    '<a href="https://github.com/hyperknot/openfreemap/blob/main/LICENSE.md" '
    'title="Positron: OpenMapTiles (CC BY 4.0), derived from CARTO by Stamen and '
    'Paul Norman (CC BY 3.0)">Style credits</a>'
)
THEME_HTML = """
<script>
(() => {
  const param = new URLSearchParams(window.location.search).get("clawpilotTheme");
  const theme =
    param || (window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light");
  document.documentElement.setAttribute("data-theme", theme);
})();
</script>
<style>
:root {
  color-scheme: light;
  --cp-bg: #f7f4ef;
  --cp-bg-elevated: #fcfbf8;
  --cp-surface: #ffffff;
  --cp-surface-soft: #f5f5f5;
  --cp-border: #dedede;
  --cp-border-strong: #919191;
  --cp-text: #242424;
  --cp-text-muted: #5c5c5c;
  --cp-text-soft: #6f6f6f;
  --cp-accent: #b11f4b;
  --cp-accent-hover: #9a1a41;
  --cp-accent-soft: rgba(177, 31, 75, 0.08);
  --cp-accent-fg: #ffffff;
  --cp-success: #16a34a;
  --cp-danger: #dc2626;
  --cp-warning: #f59e0b;
  --cp-link: #0078d4;
  --cp-shadow: 0 18px 48px rgba(0, 0, 0, 0.12);
  --cp-overlay: rgba(255, 255, 255, 0.8);
  --cp-panel: rgba(255, 255, 255, 0.86);
  --cp-panel-strong: rgba(255, 255, 255, 0.96);
  --cp-sheen: rgba(255, 255, 255, 0.55);
  --cp-highlight: rgba(177, 31, 75, 0.12);
}
html[data-theme="dark"] {
  color-scheme: dark;
  --cp-bg: #3d3b3a;
  --cp-bg-elevated: #343231;
  --cp-surface: #292929;
  --cp-surface-soft: #2e2e2e;
  --cp-border: #474747;
  --cp-border-strong: #5f5f5f;
  --cp-text: #dedede;
  --cp-text-muted: #919191;
  --cp-text-soft: #b0b0b0;
  --cp-accent: #fd8ea1;
  --cp-accent-hover: #fb7b91;
  --cp-accent-soft: rgba(253, 142, 161, 0.14);
  --cp-accent-fg: #1a1a1a;
  --cp-success: #4ade80;
  --cp-danger: #f87171;
  --cp-warning: #fbbf24;
  --cp-link: #4da6ff;
  --cp-shadow: 0 18px 48px rgba(0, 0, 0, 0.32);
  --cp-overlay: rgba(41, 41, 41, 0.88);
  --cp-panel: rgba(41, 41, 41, 0.72);
  --cp-panel-strong: rgba(41, 41, 41, 0.96);
  --cp-sheen: rgba(255, 255, 255, 0.04);
  --cp-highlight: rgba(253, 142, 161, 0.12);
}
.openfreemap-error {
  background: var(--cp-surface);
  color: var(--cp-danger);
  border: 1px solid var(--cp-border);
  border-radius: 0.625rem;
  padding: 12px;
  max-width: 320px;
  font: 13px/1.5 "Segoe UI", Aptos, Calibri, -apple-system, BlinkMacSystemFont, sans-serif;
}
</style>
"""


def _basemap_script(map_name: str, layer_name: str) -> str:
    return f"""
var {layer_name} = null;
(function() {{
    var map = {map_name};
    var errorMessage = null;
    map.setMaxZoom(18);
    // The Leaflet bridge does not forward the MapLibre attribution control.
    map.attributionControl.addAttribution({json.dumps(ATTRIBUTION)});
    function showError(message) {{
        console.error(message);
        if (!errorMessage) {{
            var notice = L.control({{position: 'topleft'}});
            notice.onAdd = function() {{
                errorMessage = L.DomUtil.create('div', 'openfreemap-error');
                errorMessage.setAttribute('role', 'alert');
                L.DomEvent.disableClickPropagation(errorMessage);
                L.DomEvent.disableScrollPropagation(errorMessage);
                return errorMessage;
            }};
            notice.addTo(map);
        }}
        errorMessage.textContent = message;
    }}
    if (typeof maplibregl === 'undefined' || typeof L.maplibreGL !== 'function') {{
        showError('OpenFreeMap could not load. Internet access is required for its map libraries and tiles.');
        return;
    }}
    try {{
        {layer_name} = L.maplibreGL({{
            style: {json.dumps(STYLE_URL)},
            attributionControl: false,
            interactive: false,
            maxZoom: 18
        }}).addTo(map);
        var gl = {layer_name}.getMaplibreMap();
        gl.on('error', function(event) {{
            showError('OpenFreeMap request failed: ' + event.error.message);
        }});
        gl.on('webglcontextlost', function() {{
            showError('The basemap lost its WebGL context. Reload the page in a WebGL-enabled browser.');
        }});
    }} catch (error) {{
        showError('OpenFreeMap needs WebGL and internet access: ' + error.message);
    }}
}})();
"""


class _PositronBasemap(JSCSSMixin):
    default_js = [
        ("maplibre_gl", MAPLIBRE_JS),
        ("maplibre_gl_leaflet", LEAFLET_BRIDGE_JS),
    ]
    default_css = [("maplibre_gl_css", MAPLIBRE_CSS)]
    _template = Template(
        "{% macro script(this, kwargs) %}{{ this.javascript | safe }}{% endmacro %}"
    )

    def __init__(self):
        super().__init__()
        self._name = "OpenFreeMapPositron"

    def render(self, **kwargs):
        self.javascript = _basemap_script(self._parent.get_name(), self.get_name())
        super().render(**kwargs)


def add_basemap(map_object):
    """Add Positron without changing the map's storm or infrastructure layers."""
    map_object.get_root().header.add_child(
        Element(THEME_HTML), name="basemap_theme", index=0
    )
    _PositronBasemap().add_to(map_object)


def repair_export(html: str) -> str:
    """Replace only the legacy basemap, leaving embedded results and UI intact."""
    pattern = re.compile(
        r'var (?P<layer>tile_layer_\w+) = L\.tileLayer\(\s*'
        r'"https://basemaps\.cartocdn\.com/light_all/\{z\}/\{x\}/\{y\}\.png",'
        r'\s*(?P<options>\{.*?\})\s*\);',
        re.DOTALL,
    )
    matches = list(pattern.finditer(html))
    if len(matches) != 1:
        raise ValueError(
            f"Expected exactly one legacy CARTO basemap; found {len(matches)}. "
            "The file may already be repaired or use a different export format."
        )
    match = matches[0]
    layer_name = match["layer"]
    add_pattern = re.compile(
        rf"\b{re.escape(layer_name)}\.addTo\((?P<map>map_\w+)\);"
    )
    additions = list(add_pattern.finditer(html))
    if len(additions) != 1:
        raise ValueError("Could not uniquely identify the legacy basemap's map.")
    if len(re.findall(r"<head\b[^>]*>", html, re.IGNORECASE)) != 1 or len(
        re.findall(r"</head\s*>", html, re.IGNORECASE)
    ) != 1:
        raise ValueError("Expected a complete HTML document with one head element.")

    declaration = _basemap_script(additions[0]["map"], layer_name)
    html = html[:match.start()] + declaration + html[match.end():]
    html = add_pattern.sub("", html, count=1)
    html = re.sub(
        r"<head\b[^>]*>", lambda m: m[0] + THEME_HTML, html, count=1, flags=re.IGNORECASE
    )
    assets = (
        f'<link rel="stylesheet" href="{MAPLIBRE_CSS}">\n'
        f'<script src="{MAPLIBRE_JS}"></script>\n'
        f'<script src="{LEAFLET_BRIDGE_JS}"></script>\n'
    )
    return re.sub(
        r"</head\s*>", lambda m: assets + m[0], html, count=1, flags=re.IGNORECASE
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path, help="Existing CARTO-based HTML export")
    parser.add_argument("output", type=Path, help="New HTML file (must not exist)")
    args = parser.parse_args()
    if args.input.resolve() == args.output.resolve():
        parser.error("Choose a different output path to preserve the original.")
    try:
        result = repair_export(args.input.read_bytes().decode("utf-8"))
        with args.output.open("xb") as output:
            output.write(result.encode("utf-8"))
    except (OSError, ValueError) as exc:
        parser.exit(1, f"Basemap repair failed: {exc}\n")
    print(f"Repaired map: {args.output.resolve()}")
    print("Open the HTML directly in a WebGL-enabled browser. Internet is required; no key is needed.")


if __name__ == "__main__":
    main()
