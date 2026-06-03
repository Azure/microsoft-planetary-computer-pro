# GeoAI SDK Documentation

Python SDK for running geospatial AI models at scale on Azure AI Foundry and Planetary Computer.

---

## Quick Links

📖 **[README](../README.md)** - Overview and quick start  
📓 **[Example Notebooks](../examples/)** - Interactive tutorials  
🔧 **[API Reference](#api-reference)** - Complete parameter documentation  

---

## Getting Started

1. **Install:** Clone the repository and run `pip install -e .`
2. **Learn:** Try the [EOOS notebook](../examples/EO_OS_Object_Detection/eoos_object_detection.ipynb) or [MARS notebook](../examples/MARS_Map_Autoregressive/mars_map_generation.ipynb)
3. **Reference:** Use API docs below for parameter details

---

## API Reference

### Core Classes

- **[Input](api/input.md)** - Configure data sources (STAC catalogs, collections)
- **[Output](api/output.md)** - Configure result destinations (GeoCatalog, blob storage)
- **[Constraint](api/constraints.md)** - Filter by space, time, and properties
- **[Models](api/models.md)** - Available models (EOOS, MARS)

### Features

- **[Validation](api/validation.md)** - Pre-flight checks for input, model, and output

---

## Examples

All examples are available as Jupyter notebooks in [examples/](../examples/):

- **[EOOS Object Detection](../examples/EO_OS_Object_Detection/eoos_object_detection.ipynb)** - Detect objects in satellite imagery
- **[MARS Map Generation](../examples/MARS_Map_Autoregressive/mars_map_generation.ipynb)** - Extract buildings, roads, railways

---

## Installation

### Local Installation

```bash
# Clone the repository
cd geoai-sdk
pip install -e .
```

### Development

```bash
# For contributors: install with dev tools
cd geoai-sdk
pip install -e ".[dev]"

# Format code before commits
python -m black geoai/ --line-length 100
python -m isort geoai/ --profile black --line-length 100
python -m flake8 geoai/ --count --select=E9,F63,F7,F82
```

---

## Architecture

The SDK is built with three layers:

### 1. Public API Layer
User-facing classes for configuration:

- [`Input`](api/input.md) - Data source configuration
- [`Output`](api/output.md) - Result destination
- [`Constraint`](api/constraints.md) - Spatial/temporal filtering
- [`Models`](api/models.md) - EOOS, MARS

### 2. Executors Layer
Handles workflow execution:

- **LocalExecutor** - Sequential processing with progress bars

### 3. Core Components Layer
Reusable business logic:

- **Spatial** - ChipMaker, DetectionMerger
- **STAC** - STACSearcher, ItemSelector
- **Imagery** - ImageFetcher, ImagePreprocessor
- **Models** - ModelClient, PayloadBuilder, ResponseParser
- **Results** - DetectionFormatter, GeoCatalogWriter

---

## Supported Models

| Model | Type | Input | Output |
|-------|------|-------|--------|
| [EOOS](api/models.md) | Object Detection | NAIP | GeoJSON Features |
| [MARS](api/models.md) | Map Generation | NAIP | GeoJSON Features |


---

## Support

- **Team:** Azure Orbital Spatio Team

---

## License

This project is licensed under the MIT License - see the LICENSE file for details.
