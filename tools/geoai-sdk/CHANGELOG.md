# Changelog

All notable changes to the GeoAI SDK will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- **MARS: Water segmentation category** — the `Water` class (Polygon geometry) is now a
  default MARS category alongside Building, Road, and Railway. Filter via
  `params={"categories": ["Water", ...]}`.
- **MARS: `/map:render` support** — new `MARS.render_map()` method and `MapRenderer` client
  to rasterize imagery + GeoJSON features into a styled cartographic basemap PNG. Supports
  `tile_size`, `coordinate_space` (`geographic`/`pixel`), `theme`
  (`default`/`dark`/`standard_oil`/`streets`), and `color_map` overrides. The render URL is
  derived automatically from the model's scoring endpoint.
- Model spec schema: optional `category_geometry_types` and `map_render` sections.
- Shared `geoai.shared.auth` helper (`build_auth_headers`, `get_auth_scope`) reused by the
  model client and map renderer.
- Initial SDK package structure with modern Python packaging (pyproject.toml)
- Unified API for running geospatial AI models (Input, Constraint, Output, Model classes)
- EO-OS object detection model implementation
- Local executor for sequential workflow processing with progress tracking
- GeoCatalog STAC integration for reading and writing catalogs
- Automatic AOI chipping with configurable chip size, stride, and overlap
- STAC catalog search with spatial, temporal, and metadata filtering
- COG image fetching and preprocessing pipeline with normalization
- Detection result merging using Non-Maximum Suppression (NMS)
- SAS URL generation for Azure Blob Storage authentication with user delegation keys
- Progress indicators using tqdm for chip processing and inference operations
- Comprehensive example scripts for EO-OS object detection workflows
- Full documentation suite (README, quickstart guide, architecture documentation)
- Test framework structure with pytest configuration and fixtures

### Known Issues
