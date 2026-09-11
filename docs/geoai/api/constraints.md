# Constraints

Constraint classes define spatial, temporal, and model-specific filtering for model execution.

---

## Overview

The SDK supports two modes:

- **Single AOI** - Process one location (bbox or geometry)
- **Multi-AOI** - Process multiple locations concurrently (GeoDataFrame or GeoParquet)

---

## Parameters

### Single AOI Parameters (choose one)

**`bbox`** : `List[float] | None`  
Bounding box in WGS84 coordinates: `[west, south, east, north]` (longitude, latitude).

**`geometry`** : `Dict | None`  
GeoJSON geometry (alternative to bbox). Supports Polygon, MultiPolygon, etc.

### Multi-AOI Parameters

**`aois`** : `GeoDataFrame | str | None`  
Multiple areas of interest for concurrent processing.

Accepts:
- **GeoDataFrame** - Direct GeoDataFrame with geometries
- **str** - Path to GeoParquet file (`.geoparquet`)

**Requirements:**
- Must have `geometry` column
- Recommended: Include `id` column for tracking results
- CRS: Any (automatically converted to EPSG:4326)

### Temporal Filtering

**`datetime`** : `str | None`  
ISO 8601 datetime or range:
- Single: `"2024-01-15T00:00:00Z"`
- Range: `"2024-01-01/2024-12-31"`
- Open-ended: `"2024-01-01/.."` or `"../2024-12-31"`

### Additional Filters

**`filter`** : `Dict | None`  
CQL2-JSON filter for STAC search. Common filters:
- Cloud cover: `{"eo:cloud_cover": {"lte": 20}}`
- GSD: `{"gsd": {"lte": 1.0}}`
- Platform: `{"platform": {"eq": "sentinel-2a"}}`

**`stac_search`** : `Search | None`  
Pre-built pystac_client Search object. Advanced users only.

---

## Examples

### Single AOI - Bounding Box

```python
import geoai

constraint = geoai.Constraint(
    bbox=[-122.5, 37.5, -122.0, 38.0],
    datetime="2024-01-01/2024-12-31"
)
```

### Single AOI - Geometry

```python
constraint = geoai.Constraint(
    geometry={
        "type": "Polygon",
        "coordinates": [[
            [-122.5, 37.5],
            [-122.0, 37.5],
            [-122.0, 38.0],
            [-122.5, 38.0],
            [-122.5, 37.5]
        ]]
    },
    datetime="2024-01-01/2024-12-31"
)
```

### Single AOI - With Filters

```python
constraint = geoai.Constraint(
    bbox=[-122.5, 37.5, -122.0, 38.0],
    datetime="2024-01-01/2024-12-31",
    filter={"eo:cloud_cover": {"lte": 20}}
)
```

### Complex Geometry from File

```python
import json

with open("aoi.geojson") as f:
    geojson = json.load(f)

constraint = geoai.Constraint(
    geometry=geojson["features"][0]["geometry"],
    datetime="2024-01-01/2024-12-31"
)
```

### Multi-AOI - GeoDataFrame

```python
import geopandas as gpd
from shapely.geometry import box

# Create GeoDataFrame with multiple AOIs
gdf = gpd.GeoDataFrame({
    'id': ['site_1', 'site_2', 'site_3'],
    'name': ['Downtown', 'Airport', 'Harbor'],
    'geometry': [
        box(-122.5, 37.5, -122.4, 37.6),
        box(-122.3, 37.7, -122.2, 37.8),
        box(-122.1, 37.9, -122.0, 38.0)
    ]
}, crs="EPSG:4326")

constraint = geoai.Constraint(
    aois=gdf,
    datetime="2024-01-01/2024-12-31"
)

# Process all AOIs concurrently
result = await model.run(input, constraint, params, output)
print(f"Processed {result.total_aois} locations")
print(f"Successful: {result.successful_aois}")
```

### Multi-AOI - GeoParquet File

```python
# Save to GeoParquet (efficient format)
gdf.to_parquet("sites.geoparquet")

# Load and process
constraint = geoai.Constraint(
    aois="sites.geoparquet",
    datetime="2024-01-01/2024-12-31",
    filter={"gsd": {"lte": 0.6}}  # High-res only
)

result = await model.run(input, constraint, params, output)

# Per-AOI results available
for aoi_result in result._raw_result.get('results', []):
    aoi_id = aoi_result['aoi_id']
    detections = aoi_result['result']['detection_count']
    print(f"{aoi_id}: {detections} detections")
```

### Multi-AOI with Properties

```python
# AOIs can include custom properties
gdf = gpd.GeoDataFrame({
    'id': ['zone_1', 'zone_2'],
    'zone_type': ['residential', 'commercial'],
    'priority': [1, 2],
    'geometry': [
        box(-122.5, 37.5, -122.4, 37.6),
        box(-122.3, 37.7, -122.2, 37.8)
    ]
}, crs="EPSG:4326")

constraint = geoai.Constraint(aois=gdf, datetime="2024-01-01/2024-12-31")
# Properties preserved in results
```

---

## Multi-AOI Benefits

Processing multiple AOIs in a single run provides:

- **Efficiency** - SDK optimizes STAC search across all locations  
- **Concurrency** - Chips processed in parallel across all AOIs  
- **Robustness** - Failed AOIs don't stop the entire job  
- **Single Output** - All results published to one GeoCatalog collection  
- **Per-AOI Results** - Individual statistics and outputs for each location  

**Use cases:**
- Multiple buildings or sites
- City-wide analysis by neighborhood
- Regional infrastructure surveys
- Portfolio analysis across properties

---

## Mode Detection

The SDK automatically detects the constraint mode:

```python
# Single AOI mode
constraint = geoai.Constraint(bbox=[...], datetime="...")
print(constraint.mode)  # "single"

# Multi-AOI mode
constraint = geoai.Constraint(aois=gdf, datetime="...")
print(constraint.mode)  # "multi"

# Iterate AOIs (works for both modes)
for aoi in constraint.iter_aois():
    print(aoi['id'], aoi['geometry'])
```

---

## Validation

Constraints are validated automatically during initialization:

```python
constraint = geoai.Constraint(
    bbox=[-122.5, 37.5, -122.0, 38.0],
    datetime="2024-01-01/2024-12-31"
)
# Raises ValueError if invalid
```

### Common Validation Errors

**"Must provide either bbox, geometry, or aois"**  
```python
# Wrong
constraint = geoai.Constraint(datetime="2024-01-01/2024-12-31")

# Correct - single AOI
constraint = geoai.Constraint(
    bbox=[-118.5, 34.0, -118.0, 34.5],
    datetime="2024-01-01/2024-12-31"
)

# Correct - multi AOI
constraint = geoai.Constraint(
    aois=gdf,
    datetime="2024-01-01/2024-12-31"
)
```

**"Cannot provide both bbox and aois"**  
```python
# Wrong - mixing single and multi AOI modes
constraint = geoai.Constraint(
    bbox=[-118.5, 34.0, -118.0, 34.5],
    aois=gdf,
    datetime="2024-01-01/2024-12-31"
)

# Correct - choose one mode
constraint = geoai.Constraint(
    aois=gdf,
    datetime="2024-01-01/2024-12-31"
)
```

**"minx must be < maxx"**  
```python
# Wrong - west > east
bbox=[-118.0, 34.0, -118.5, 34.5]

# Correct
bbox=[-118.5, 34.0, -118.0, 34.5]
```

**"longitude must be in range [-180, 180]"**  
```python
# Wrong
bbox=[190, 34.0, 195, 34.5]

# Correct
bbox=[-170, 34.0, -165, 34.5]
```

---

## CQL2 Filter Examples

### Cloud Cover

```python
filter={"eo:cloud_cover": {"lte": 20}}
```

### Resolution

```python
filter={"gsd": {"lte": 1.0}}
```

### Combined Filters

```python
filter={
    "op": "and",
    "args": [
        {"op": "<=", "args": [{"property": "eo:cloud_cover"}, 10]},
        {"op": "<=", "args": [{"property": "gsd"}, 0.6]},
        {"op": "=", "args": [{"property": "platform"}, "naip"]}
    ]
}
```

---

## See Also

- [Complete Examples](../../examples/) - Multi-AOI workflows in notebooks
- [Input](input.md) - Data source configuration
- [Output](output.md) - Result destinations
- [Models](models.md) - Model-specific requirements
- [STAC Guide](../guides/stac.md) - Working with STAC catalogs
