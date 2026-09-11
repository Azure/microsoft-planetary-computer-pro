# Input

Configure where the SDK retrieves geospatial data.

---

## Constructor

```python
Input(collection, geocatalog_uri=None, credential=None)
```

---

## Required Parameters

**`collection`** : `str`  
STAC collection name containing the imagery.

**Common collections:**
- `naip` - High-resolution aerial imagery (0.6m, USA only)
- `sentinel-2-l2a` - Sentinel-2 satellite (10m, global)
- `landsat-c2-l2` - Landsat Collection 2 (30m, global)

---

## Optional Parameters

**`geocatalog_uri`** : `str | None`  
STAC API endpoint URL. Default: Planetary Computer

**Default:** `https://planetarycomputer.microsoft.com/api/stac/v1`

**Custom GeoCatalog example:** `https://your-geocatalog.com/stac`

**`credential`** : `Any | None`  
Azure credential for authentication. Required for private GeoCatalogs.

**Example:** `DefaultAzureCredential()`

---

## Examples

### Planetary Computer (Default)

```python
import geoai

# Uses Planetary Computer by default
input_source = geoai.Input(collection="naip")
```

### Private GeoCatalog

```python
from azure.identity import DefaultAzureCredential
import geoai

input_source = geoai.Input(
    collection="custom-imagery",
    geocatalog_uri="https://my-geocatalog.com/stac",
    credential=DefaultAzureCredential()
)
```

---

## See Also

- **[Complete Example](../../examples/EO_OS_Object_Detection/eoos_object_detection.ipynb)** - Full workflow with Input configuration
- **[Output](output.md)** - Configure result destinations
- **[Constraint](constraints.md)** - Filter imagery
