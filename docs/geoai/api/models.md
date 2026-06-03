# Models

Available geospatial AI models in the SDK.

---

## Supported Models

| Model | Task | Collections | Resolution | Output |
|-------|------|-------------|------------|--------|
| **EOOS** | Object Detection | NAIP | 0.6m | GeoJSON (points/polygons) |
| **MARS** | Building/Road/Railway Detection | NAIP | 0.6m | GeoJSON (polygons/lines) |

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

## MARS (Building/Road/Railway Detection)

Extracts building footprints, road networks, and railway lines from aerial imagery.

**Model ID:** `microsoft/mars-map-autoregressive`

**Detected Features:**
- **Building** - Polygon geometries (footprints)
- **Road** - LineString geometries (road networks)
- **Railway** - LineString geometries (railway tracks)

**Parameters:**
- `chip_size` (int): Chip size in pixels (default: 1024, max: 2048)
- `stride` (int): Stride in pixels for overlap (default: 800)
- `threshold` (float): Detection confidence threshold (0-1, default: 0.6)
- `categories` (list): Optional filter for specific features (default: all 3)

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
    params={"chip_size": 1024, "stride": 800, "threshold": 0.6},
    output=output
)

# Filter to buildings only
result = await model.run(
    input=input_source,
    constraint=constraint,
    params={
        "chip_size": 1024,
        "stride": 800,
        "threshold": 0.6,
        "categories": ["Building"]
    },
    output=output
)

# Check results by category
print(f"Buildings: {result.detection_counts.get('Building', 0)}")
print(f"Roads: {result.detection_counts.get('Road', 0)}")
print(f"Railways: {result.detection_counts.get('Railway', 0)}")
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
