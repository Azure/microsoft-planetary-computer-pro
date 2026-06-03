# Output

Configure where model results are published.

---

## Constructor

```python
Output(
    geocatalog_uri,
    collection_name,
    credential,
    storage_url,
    blob_container,
    storage_account_key=None,
    run_id=None,
    save_local=False,
    output_dir="./output"
)
```

---

## Required Parameters

**`geocatalog_uri`** : `str`  
GeoCatalog/STAC endpoint URL where results will be published.

**`collection_name`** : `str`  
Name of the collection to create or use for results.

**`credential`** : `Any`  
Azure credential for GeoCatalog and blob storage authentication.

**`storage_url`** : `str`  
Azure Blob Storage account URL (e.g., `https://account.blob.core.windows.net`).

**`blob_container`** : `str`  
Blob container name for storing chip imagery and STAC item assets.

---

## Optional Parameters

**`storage_account_key`** : `str | None`  
Storage account key for SAS generation. Only needed if Azure AD delegation is unavailable.

**Recommended:** Use Azure RBAC roles instead:
- Storage Blob Data Contributor (for uploads)
- Storage Blob Delegator (for SAS generation)

**`run_id`** : `str | None`  
Run identifier for organizing results. Auto-generated UUID if not provided.

**`save_local`** : `bool`  
Save results to local files for debugging. Default: `False`.

**`output_dir`** : `str`  
Local directory for saved files (only used if `save_local=True`). Default: `./output`.

---

## Publishing Behavior

**GeoCatalog publishing happens automatically** when you provide an Output object to `model.run()`.

Results include:
- STAC items with detection/segmentation metadata
- Chip imagery and overlays in blob storage
- GeoJSON features with geometries and properties

---

## Examples

### Standard Configuration

```python
from azure.identity import DefaultAzureCredential
import geoai

output = geoai.Output(
    geocatalog_uri="https://geocatalog.contoso.com",
    collection_name="building-detections",
    credential=DefaultAzureCredential(),
    storage_url="https://myaccount.blob.core.windows.net",
    blob_container="results"
)
```

### With Local Debugging

```python
output = geoai.Output(
    geocatalog_uri="https://geocatalog.contoso.com",
    collection_name="road-detections",
    credential=DefaultAzureCredential(),
    storage_url="https://myaccount.blob.core.windows.net",
    blob_container="results",
    save_local=True,
    output_dir="./debug_output"
)
```

### With Storage Account Key (Fallback)

```python
import os

output = geoai.Output(
    geocatalog_uri="https://geocatalog.contoso.com",
    collection_name="detections",
    credential=DefaultAzureCredential(),
    storage_url="https://myaccount.blob.core.windows.net",
    blob_container="results",
    storage_account_key=os.getenv("STORAGE_ACCOUNT_KEY")  # Fallback auth
)
```

---

## Blob Storage Layout

Results are organized in blob storage:

```
{blob_container}/
└── {model_name}/
    └── {run_id}/
        ├── chips/
        │   ├── chip_0_0.tif
        │   ├── chip_0_1.tif
        │   └── ...
        └── results/
            ├── merged_imagery.tif
            ├── final_overlay.tif
            ├── final_overlay.jpg
            └── detections.geojson
```

---

## Validation

Output destinations are validated when you call `model.validate_input()` or `model.run()`.

Validation checks:
- GeoCatalog endpoint is reachable
- Credential has write permissions  
- Blob storage account is accessible
- Blob container exists or can be created

See [Validation](validation.md) for details.

---

## Common Issues

### Error: "Failed to generate SAS token"

**Cause**: Missing RBAC roles or storage account key.

**Solution**: Either:
1. Assign Azure RBAC roles (recommended):
   - Storage Blob Data Contributor
   - Storage Blob Delegator
2. Or provide `storage_account_key` parameter

---

## See Also

- [Complete Example](../../examples/EO_OS_Object_Detection/eoos_object_detection.ipynb) - Full workflow with Output configuration
- [Input](input.md) - Configure data sources
- [Validation](validation.md) - Pre-flight checks
