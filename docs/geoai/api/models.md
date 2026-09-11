# Models

Available geospatial AI models in the SDK.

---

## Supported Models

| Model | Task | Collections | Resolution | Output |
|-------|------|-------------|------------|--------|
| **EOOS** | Object Detection | NAIP | 0.6m | GeoJSON (points/polygons) |
| **MARS** | Building/Road/Railway/Water Detection + Map Render | NAIP | 0.6m | GeoJSON (polygons/lines) + PNG |

---

## Model Discovery

List all available models:

```python
import geoai

# List all models
models = geoai.models.list()
for model in models:
    print(f"{model['name']}: {model['model_name']}")

# Get model details
eoos_info = geoai.models.get("eoos")
print(eoos_info['supported_collections'])  # ['naip']
```

---

## Common Interface

All models follow the same interface:

```python
# 1. Initialize model
model = geoai.models.EOOS(
    endpoint="https://your-endpoint.inference.ml.azure.com/score",
    credential="your-api-key-or-credential"
)

# 2. Run inference
result = await model.run(
    input=input_source,
    constraint=constraint,
    params={"chip_size": 1024, "threshold": 0.5},
    output=output
)

# 3. Access results
print(f"Detected {result.detection_count} objects")
print(f"Processed {result.total_chips} chips")
```

---

## EOOS (Object Detection)

Detects objects in high-resolution satellite imagery.

**Model ID:** `microsoft/eo-os-object-detection`

**Parameters:**
- `chip_size` (int): Chip size in pixels (default: 1024, max: 2048)
- `stride` (int): Stride in pixels for overlap (default: 800)
- `threshold` (float): Detection confidence threshold (0-1, default: 0.5)

**Example:**

```python
model = geoai.models.EOOS(
    endpoint="https://eoos.eastus.inference.ml.azure.com/score",
    credential="your-api-key"
)

result = await model.run(
    input=input_source,
    constraint=constraint,
    params={"chip_size": 1024, "stride": 800, "threshold": 0.5},
    output=output
)
```

---

## MARS (Building/Road/Railway/Water Detection)

Extracts building footprints, road networks, railway lines, and water bodies from aerial imagery.

**Model ID:** `microsoft/mars-map-autoregressive`

**Detected Features:**
- **Building** - Polygon geometries (footprints)
- **Road** - LineString geometries (road networks)
- **Railway** - LineString geometries (railway tracks)
- **Water** - Polygon geometries (water segmentation)

**Parameters:**
- `chip_size` (int): Chip size in pixels (default: 1024, max: 2048)
- `stride` (int): Stride in pixels for overlap (default: 800)
- `categories` (list): Optional filter for specific features (default: all 4 — Building, Road, Railway, Water)

**Example:**

```python
model = geoai.models.MARS(
    endpoint="https://mars.eastus.inference.ml.azure.com/score",
    credential="your-api-key"
)

# Detect all categories
result = await model.run(
    input=input_source,
    constraint=constraint,
    params={"chip_size": 1024, "stride": 800},
    output=output
)

# Filter to buildings and water only
result = await model.run(
    input=input_source,
    constraint=constraint,
    params={
        "chip_size": 1024,
        "stride": 800,
        "categories": ["Building", "Water"]
    },
    output=output
)

print(f"Detected {result.detection_count} features")
```

### Map rendering (`/map:render`)

MARS also exposes a rendering endpoint that rasterizes imagery + extracted GeoJSON
features into a styled cartographic basemap PNG. The render URL is derived automatically
from the model's scoring endpoint, so the same `MARS` instance is reused.

**`render_map` parameters:**
- `image` (bytes | path): GeoTIFF image.
- `geojson` (dict | list | JSON str | bytes | path): Features to render.
- `tile_size` (int): Output tile size in pixels, longer side (default: 1024).
- `coordinate_space` (str): `"geographic"` for georeferenced features (e.g. run
  output) or `"pixel"` for raw `/score` output (default: `"geographic"`).
- `theme` (str): Cartographic theme — `default`, `dark`, `standard_oil`, or
  `streets` (default: `"default"`). See `model.render_themes`.
- `color_map` (dict): Optional category → hex color overrides.

Returns PNG image bytes.

```python
from pathlib import Path

png_bytes = await model.render_map(
    image="chip.tif",
    geojson=result.merged_results,  # georeferenced FeatureCollection from run()
    coordinate_space="geographic",
    theme="streets",
    color_map={"Water": "#1a6fb0", "Building": "#8a9cbf"},
)

Path("basemap.png").write_bytes(png_bytes)
```

---

## Concurrency Configuration

Both models support configuring concurrency based on your endpoint deployment:

```python
# Default: 1 concurrent request
model = geoai.models.EOOS(endpoint="...", credential="...")

# Scale with your deployment
model = geoai.models.EOOS(
    endpoint="...",
    credential="...",
    num_instances=3,           # Endpoint instances
    concurrent_per_instance=10  # Max requests per instance
)
# → 30 total concurrent requests
```

---

## See Also

- **[EOOS Notebook](../../examples/EO_OS_Object_Detection/eoos_object_detection.ipynb)** - Complete object detection example
- **[MARS Notebook](../../examples/MARS_Map_Autoregressive/mars_map_generation.ipynb)** - Complete map generation example
- **[Input](input.md)** - Configure data sources
- **[Output](output.md)** - Configure result destinations
