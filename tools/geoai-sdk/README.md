# GeoAI SDK

> Run Azure AI Foundry geospatial models at scale on satellite imagery

## What is GeoAI SDK?

**GeoAI SDK** makes it simple to run geospatial AI models on satellite imagery. Point to your data source, define your area of interest, and let the SDK handle everything else - from data discovery and validation to concurrent processing and result publishing.

Built for [Planetary Computer](https://planetarycomputer.microsoft.com/) and [Azure AI Foundry](https://ai.azure.com/), with automatic optimization for model endpoints and concurrent request handling.

## ⚡ Quick Start

```python
import geoai
from azure.identity import DefaultAzureCredential

# 1. Configure your workflow
input_source = geoai.Input(collection="naip")  # Planetary Computer

constraint = geoai.Constraint(
    bbox=[-122.5, 37.5, -122.0, 38.0],  # San Francisco
    datetime="2024-01-01/2024-12-31"
)

output = geoai.Output(
    geocatalog_uri="https://your-geocatalog.com/",
    collection_name="sf-detections",
    credential=DefaultAzureCredential(),
    storage_url="https://youraccount.blob.core.windows.net",
    blob_container="results"
)

# 2. Run object detection
model = geoai.models.EOOS(
    endpoint="https://your-model.inference.ml.azure.com/score",
    credential="your-api-key",
    num_instances=3,           # Optimize for your deployment
    concurrent_per_instance=10  # Max concurrent requests per instance
)

result = await model.run(
    input=input_source,
    constraint=constraint,
    params={"chip_size": 1024, "stride": 800, "threshold": 0.5},
    output=output
)

print(f"✅ Detected {result.detection_count} objects")
print(f"📊 Processed {result.total_chips} chips")
print(f"🔗 View: {result.geocatalog_url}")
```

**That's it!** The SDK handles STAC search, chipping, preprocessing, inference, merging, and publishing.

---

## ✨ Why GeoAI SDK?

### **No Infrastructure Management**
- ✅ Single machine processing with optimized concurrency
- ✅ Automatic parallelization across model instances
- ✅ Smart resource utilization based on your endpoint configuration

### **Intelligent Workflow**
- 🔍 **Discover** - Find available models and check compatibility
- 📊 **Estimate** - Preview job scope before running (chip count, data availability)
- ✅ **Validate** - Automatic input validation and error checking
- 🚀 **Execute** - Fully automated 7-step workflow

### **Key Capabilities**
- 🌍 **Multi-AOI Support** - Process hundreds of locations in one call
- ⚡ **Concurrent Processing** - 5-30× speedup with configurable parallelism
- 🔄 **Result Merging** - Automatic NMS for overlapping detections
- 📤 **GeoCatalog Integration** - Direct STAC item publishing with extent management

---

## � Prerequisites

Before using the SDK, you'll need to set up the following Azure resources:

### 1. Deploy AI Model in Azure AI Foundry

Deploy an EOOS or MARS model endpoint to run inference:

- Browse models in [Azure AI Foundry Model Catalog](https://ai.azure.com/explore/models):
  - [EOOS Object Detection](https://ai.azure.com/explore/models/eo-os-object-detection/version/1/registry/azureml-spectre-p)
  - [MARS Map Generation](https://ai.azure.com/explore/models/mars-map-autoregressive/version/1/registry/azureml-spectre-p)
- Obtain your endpoint URL (e.g., `https://your-model.eastus.inference.ml.azure.com/score`)
- Get your API key or configure Azure AD authentication

### 2. Azure Storage Account

Required for storing imagery and STAC item assets:

- Create an [Azure Storage Account](https://learn.microsoft.com/en-us/azure/storage/common/storage-account-create)
- Create a blob container (e.g., `sdk-results`)
- Note your storage URL (e.g., `https://youraccount.blob.core.windows.net`)

### 3. GeoCatalog

Required for publishing results as STAC items:

- Set up a GeoCatalog instance or use an existing one
- Note your GeoCatalog URI (collections are auto-created)

### 4. Azure RBAC Roles

Assign the following roles for Azure AD authentication (recommended):

| Resource | Required Role | Purpose |
|----------|--------------|---------|
| Storage Account | `Storage Blob Data Contributor` | Upload chips and assets |
| Storage Account | `Storage Blob Delegator` | Generate SAS tokens with Azure AD |
| GeoCatalog | Write access to collection | Publish STAC items |
| Model Endpoint (Azure ML) | `AzureML Data Scientist` | Call inference endpoint |
| Model Endpoint (AI Foundry) | `Azure AI Developer` or `Cognitive Services User` | Call inference endpoint |

**Assign roles using Azure CLI:**
```bash
# Storage roles
az role assignment create --assignee user@contoso.com \
  --role "Storage Blob Data Contributor" \
  --scope /subscriptions/{sub-id}/resourceGroups/{rg}/providers/Microsoft.Storage/storageAccounts/{account}

# Model endpoint role (Azure ML example)
az role assignment create --assignee user@contoso.com \
  --role "AzureML Data Scientist" \
  --scope /subscriptions/{sub-id}/resourceGroups/{rg}/providers/Microsoft.MachineLearningServices/workspaces/{workspace}
```

### 5. Environment Variables (Optional)

For convenience, you can set environment variables instead of using Azure AD:

```bash
# Storage account key (alternative to Azure AD)
export STORAGE_ACCOUNT_KEY="your-key-here"

# Model API keys (alternative to Azure AD)
export EOOS_API_KEY="your-eoos-key"
export MARS_API_KEY="your-mars-key"

# SDK logging level
export GEOAI_LOG_LEVEL="INFO"  # or DEBUG for detailed logs
```

**For example notebooks:** Copy `.env.example` to `.env` (in the same directory as the notebooks) and edit with your values. The notebooks will automatically load it.

---

## 🛠️ Installation

**From wheel** (download from [GitHub Release](https://github.com/Azure/microsoft-planetary-computer-pro/releases)):

```bash
pip install geoai_sdk-0.1.0-py3-none-any.whl
```

**From cloned repo:**

```bash
pip install tools/geoai-sdk/
```

For running example notebooks, install with the `examples` extra:

```bash
# From wheel
pip install "geoai_sdk-0.1.0-py3-none-any.whl[examples]"

# From cloned repo
pip install "tools/geoai-sdk[examples]"
```

For development (includes pytest, linting tools):

```bash
pip install "tools/geoai-sdk[dev]"
```

**Requirements:**
- Python 3.9+
- Azure credentials (for GeoCatalog publishing)
- Model endpoint (Azure AI Foundry deployment)

---

## 🎯 How It Works

### Automated Workflow Steps

When you call `model.run()`, the SDK automatically:

1. **🔒 Validation** - Verifies input/output configuration, checks model compatibility
2. **🔲 Chip Creation** - Divides AOI into processing tiles with configurable size/stride
3. **🔍 STAC Search** - Finds matching imagery items with spatial/temporal filtering
4. **📥 Image Fetching** - Downloads and preprocesses imagery with multi-tile merging
5. **🤖 Model Inference** - Runs predictions with concurrent request batching
6. **🔄 Result Merging** - Combines detections with NMS and spatial deduplication
7. **📤 GeoCatalog Publishing** - Uploads results as STAC items with imagery assets

---

## 📚 Key Features

### 1. Model Discovery

```python
# List all models
models = geoai.models.list()

# Check collection support
collections = geoai.models.EOOS.get_supported_collections()  # ['naip']
```

### 2. Validation

Validate before running (optional - auto-runs in estimate/run):

```python
validation = await model.validate_input(
    input=input_source,
    constraint=constraint,
    params={"chip_size": 1024}
)

if not validation.is_valid:
    for error in validation.errors:
        print(f"❌ {error}")
```

### 3. Estimation

Preview job scope (includes validation):

```python
estimate = await model.estimate(input_source, constraint, params)

print(f"Chips: {estimate.estimated_chips}")
print(f"STAC items: {estimate.stac_items_found}")

# Per-AOI breakdown for multi-AOI
for aoi in estimate.aoi_estimates:
    print(f"{aoi['aoi_id']}: {aoi['estimated_chips']} chips")
```

### 4. Multi-AOI Processing

```python
import geopandas as gpd

gdf = gpd.read_parquet("buildings.parquet")

constraint = geoai.Constraint(
    aois=gdf,
    datetime="2024-01-01/2024-12-31"
)

result = await model.run(input_source, constraint, params, output)
print(f"Processed {result.total_aois} AOIs")
```

### 5. Advanced STAC Control

```python
import pystac_client

client = pystac_client.Client.open("https://planetarycomputer.microsoft.com/api/stac/v1")
search = client.search(
    collections=["naip"],
    bbox=[-122.5, 37.5, -122.0, 38.0],
    datetime="2024-01-01/2024-12-31",
    sortby=[{"field": "properties.datetime", "direction": "desc"}],
    limit=10
)

constraint = geoai.Constraint(bbox=[-122.5, 37.5, -122.0, 38.0], stac_search=search)
```

---

## 📖 Examples

### Object Detection (EOOS)

Detect objects in high-resolution satellite imagery:

```python
import geoai
from azure.identity import DefaultAzureCredential

# Configure input from Planetary Computer
input_source = geoai.Input(collection="naip")

# Define area and time
constraint = geoai.Constraint(
    bbox=[-118.42, 33.938, -118.40, 33.946],  # LAX
    datetime="2020-01-01/2023-12-31"
)

# Configure output
output = geoai.Output(
    geocatalog_uri="https://your-geocatalog.com/",
    collection_name="lax-detections",
    credential=DefaultAzureCredential(),
    storage_url="https://youraccount.blob.core.windows.net",
    blob_container="results"
)

# Run detection
model = geoai.models.EOOS(
    endpoint="https://eoos.inference.ml.azure.com/score",
    credential="your-api-key"
)

result = await model.run(
    input=input_source,
    constraint=constraint,
    params={"chip_size": 1024, "stride": 800, "threshold": 0.5},
    output=output
)

print(f"Detected {result.detection_count} objects")
```

### Building/Road Detection (MARS)

Extract buildings, roads, and railways:

```python
import geoai

# Same input/constraint setup...

# Run MARS
model = geoai.models.MARS(
    endpoint="https://mars.inference.ml.azure.com/score",
    credential="your-api-key"
)

result = await model.run(
    input=input_source,
    constraint=constraint,
    params={
        "chip_size": 1024,
        "stride": 800,
        "threshold": 0.5,
        # Optional: filter specific features
        # "categories": ["Building", "Road"]
    },
    output=output
)

# Results include category breakdown
print(f"🏢 Buildings: {result.detection_counts.get('Building', 0)}")
print(f"🛣️ Roads: {result.detection_counts.get('Road', 0)}")
print(f"🚂 Railways: {result.detection_counts.get('Railway', 0)}")
```

---

## 🎓 Learn More

- **[📓 Example Notebooks](examples/)** - Interactive Jupyter notebooks with full workflows
  - [EOOS Object Detection](examples/EO_OS_Object_Detection/eoos_object_detection.ipynb)
  - [MARS Map Generation](examples/MARS_Map_Autoregressive/mars_map_generation.ipynb)

- **[📖 Documentation](docs/)** - Detailed guides and API reference

---

## 🌟 Supported Models

| Model | Task | Collections | Resolution |
|-------|------|-------------|------------|
| **EOOS** | Object Detection | NAIP | 0.6m |
| **MARS** | Building/Road/Railway Detection | NAIP | 0.6m |

---

## 🤝 Support

- **Homepage**: [https://aka.ms/geoaisdk](https://aka.ms/geoaisdk)
- **Documentation**: [Full Docs](https://github.com/Azure/microsoft-planetary-computer-pro/tree/main/docs/geoai)
- **Repository**: [GitHub](https://github.com/Azure/microsoft-planetary-computer-pro/tree/main/tools/geoai-sdk)
- **Issues**: [GitHub Issues](https://github.com/Azure/microsoft-planetary-computer-pro/issues)

---
