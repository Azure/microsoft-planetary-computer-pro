# Validation

Pre-flight checks for input, model endpoints, and output destinations.

---

## Overview

The SDK provides comprehensive validation to catch configuration errors **before** running expensive inference jobs.

Validation checks:
- **Input** - Imagery availability, band compatibility, resolution
- **Model Endpoint** - Connectivity and authentication
- **Output** - GeoCatalog and blob storage access

---

## When Validation Runs

Validation happens **automatically** in:
- `model.run()` - Always validates before execution
- `model.estimate()` - Validates before estimating job scope

**Optional:** Explicit validation with `model.validate_input()`

---

## Validation Method

```python
validation = await model.validate_input(
    input=input_source,
    constraint=constraint,
    params=params,
    output=output  # Optional: validates output if provided
)

if validation.is_valid:
    print("✅ Ready to run!")
else:
    for error in validation.errors:
        print(f" {error}")
```

---

## What Gets Validated

### Input Validation

**Imagery Availability:**
- Queries STAC catalog to verify data exists for AOI
- Reports number of imagery items found
- Detects resolution from STAC metadata

**Band Compatibility:**
- Checks collection has required bands (e.g., RGB for EOOS/MARS)
- Validates against model specifications

**Resolution Compatibility:**
- Verifies resolution matches model requirements
- Warns if suboptimal but acceptable

**Collection Support:**
- Checks if model supports the specified collection
- Validates filter compatibility

### Model Endpoint Validation

**Connectivity:**
- Tests that endpoint URL is reachable
- Detects network/DNS issues

**Authentication:**
- Validates API key or Azure credential works
- Catches 401/403 errors **before** running
- **Prevents the "wrong token but validation passed" issue!**

### Output Validation

**GeoCatalog Access:**
- Tests endpoint is reachable
- Validates credential has write permissions

**Blob Storage Access:**
- Tests storage account accessibility
- Validates credential can list containers
- Checks if blob container exists or can be created

---

## Validation Results

### ValidationResult Object

```python
class ValidationResult:
    is_valid: bool              # Overall validation status
    errors: List[str]           # List of errors (empty if valid)
    warnings: List[str]         # Non-fatal warnings
    detected_resolution: float  # Detected imagery resolution (m/pixel)
    bands_found: List[str]      # Available bands in imagery
    stac_items_count: int       # Number of STAC items found
```

### Example Response

```python
ValidationResult(
    is_valid=True,
    errors=[],
    warnings=["Resolution 0.3m differs from optimal 0.6m"],
    detected_resolution=0.3,
    bands_found=['red', 'green', 'blue'],
    stac_items_count=2
)
```

---

## Common Validation Errors

### Input Errors

**No imagery found:**
```
❌ No STAC items found for collection 'naip' in specified AOI/datetime
```
**Fix:** Adjust datetime range or check AOI coordinates

**Missing bands:**
```
❌ Collection 'sentinel-2-l2a' missing required bands: ['red']. Found: ['B02', 'B03', 'B04']
```
**Fix:** Use correct band names or choose different collection

**Unsupported collection:**
```
❌ Model 'EOOS' does not support collection 'landsat-c2-l2'. Supported: ['naip']
```
**Fix:** Use a supported collection

### Model Endpoint Errors

**Authentication failure:**
```
❌ Model endpoint authentication failed: Authentication failed (401 Unauthorized). Check your credential/API key.
```
**Fix:** Verify API key or Azure credential has proper role assignments

**Cannot reach endpoint:**
```
❌ Model endpoint authentication failed: Cannot connect to endpoint: [connection error details]
```
**Fix:** Check endpoint URL, network connectivity, firewall rules

### Output Errors

**GeoCatalog access denied:**
```
❌ GeoCatalog authentication failed: Credential failed to obtain access token
```
**Fix:** Run `az login` or check credential has access to GeoCatalog

**Blob storage access denied:**
```
❌ Blob storage access denied: [error]. Ensure your identity has 'Storage Blob Data Contributor' role.
```
**Fix:** Assign required RBAC roles to your identity

---

## Examples

### Basic Validation

```python
import geoai
from azure.identity import DefaultAzureCredential

# Configure
input_source = geoai.Input(collection="naip")
constraint = geoai.Constraint(
    bbox=[-122.5, 37.5, -122.0, 38.0],
    datetime="2020-01-01/2024-12-31"
)

model = geoai.models.EOOS(
    endpoint="https://eoos.eastus.inference.ml.azure.com/score",
    credential="your-api-key"
)

# Validate before running
validation = await model.validate_input(
    input=input_source,
    constraint=constraint,
    params={"chip_size": 1024, "threshold": 0.5}
)

if validation.is_valid:
    print(f"✅ Found {validation.stac_items_count} imagery items")
    print(f"📏 Resolution: {validation.detected_resolution}m/pixel")
else:
    print("❌ Validation failed:")
    for error in validation.errors:
        print(f"   {error}")
```

### Validate with Output

```python
# Also validate output destination
output = geoai.Output(
    geocatalog_uri="https://geocatalog.contoso.com",
    collection_name="detections",
    credential=DefaultAzureCredential(),
    storage_url="https://myaccount.blob.core.windows.net",
    blob_container="results"
)

validation = await model.validate_input(
    input=input_source,
    constraint=constraint,
    params=params,
    output=output  # Validates GeoCatalog + blob storage access
)

if validation.is_valid:
    print("✅ Input, model endpoint, and output all validated!")
```

### Handle Warnings

```python
if validation.is_valid:
    if validation.warnings:
        print("⚠️  Warnings:")
        for warning in validation.warnings:
            print(f"   {warning}")
        
        # Decide whether to proceed
        proceed = input("Continue anyway? (y/n): ")
        if proceed.lower() != 'y':
            exit(0)
    
    # Run model
    result = await model.run(...)
```

---

## Best Practices

1. **Always validate on new configurations** - First time using a new AOI, collection, or endpoint
2. **Validate output** - Pass `output` parameter to catch destination issues early
3. **Check warnings** - Non-fatal but may indicate suboptimal configuration
4. **Use validation to debug** - If `run()` fails, explicit validation provides clearer error messages

---

## See Also

- **[Complete Example](../../examples/EO_OS_Object_Detection/eoos_object_detection.ipynb)** - Notebooks show validation in action
- **[Input](input.md)** - Input configuration parameters
- **[Output](output.md)** - Output configuration parameters
- **[Models](models.md)** - Model-specific requirements
