---
title: GeoStats in Microsoft Planetary Computer Pro overview (Private Preview)
description: Learn how GeoStats computes raster-derived statistics for points and polygons and publishes analytics-ready results in a GeoCatalog.
author: beharris
ms.author: beharris
ms.service: planetary-computer-pro
ms.topic: overview
ms.date: 10/09/2026
#customer intent: As a geospatial analyst, I want to understand GeoStats so that I can derive table-ready statistics from raster data without building my own distributed processing system.
---

# What is GeoStats in Microsoft Planetary Computer Pro? (Private Preview)

GeoStats is a GeoCatalog capability that computes raster-derived statistics for points and polygons. You select raster observations from a SpatioTemporal Asset Catalog (STAC) collection, define one or more band calculations and statistics, and submit analysis geometries. GeoStats runs the computation at scale and publishes an analytics-ready table back to your GeoCatalog.

GeoStats supports workflows such as:

- Calculate vegetation indices for agricultural fields over time.
- Summarize environmental conditions within administrative or operational boundaries.
- Sample raster values at assets, facilities, or other point locations.
- Produce table-ready features for forecasting, risk modeling, and reporting.

> [!IMPORTANT]
> GeoStats is available only to approved private-preview participants. The API, limits, and behavior can change before general availability. The feature must be enabled for each GeoCatalog by the Microsoft Planetary Computer Pro team.

## How GeoStats works

A GeoStats workflow separates a reusable computation from each execution:

1. **Define calculations.** Save a reusable formula, or include a band expression directly in a computation.
1. **Save a computation.** Select a raster time range, observation strategy, optional quality mask, calculations, and statistics.
1. **Provide geometries.** Supply a small GeoJSON FeatureCollection inline or reference a vector asset on a STAC item in the GeoCatalog.
1. **Run the computation.** Choose zonal statistics for polygons or sampling for points and specify where GeoStats publishes the result.
1. **Monitor the operation.** Poll the operation URL returned by the service until the run reaches a terminal state.
1. **Discover the result.** Use the existing STAC API to find the output item and access its table asset.

Definitions are scoped to the raster collection in the request URL. You can run the same saved computation repeatedly with different geometry inputs or output destinations.

## Calculations and statistics

GeoStats evaluates band arithmetic before reducing pixels to statistics. For example, you can calculate Normalized Difference Vegetation Index (NDVI) with the expression `(nir - red) / (nir + red)` and bind `nir` and `red` to assets in the source collection.

You can define calculations in either of these ways:

- **Saved formula** - A named calculation that computations in the same raster collection can reuse.
- **Inline calculation** - An expression and band mapping stored directly in one computation.

A computation can apply multiple calculations and statistics in one pass over the raster data. Supported statistics are `mean`, `min`, `max`, `count`, `sum`, `stddev`, `median`, and integer percentiles from `percentile_1` through `percentile_99`.

## Observation strategies

The observation strategy determines how matching STAC items contribute to the result.

| Mode | Behavior | Common use |
| --- | --- | --- |
| `item` | Processes every matching STAC item independently. This mode is the default. | Preserve per-acquisition values and provenance. |
| `mosaic` | Resolves overlapping observations into one image by using an explicit priority. | Create one clear composite for a time range or period. |
| `all` | Retains all observations when calculating statistics. | Summarize every valid observation in a time range or period. |

For `mosaic` and `all`, you can group observations into ISO 8601 periods such as `P1W` for weekly or `P1M` for monthly results. You can also set a minimum valid-pixel fraction. Periods that don't meet the threshold remain represented in the output with a status instead of silently disappearing.

## Quality masks

An optional mask excludes invalid raster pixels before statistics are calculated. GeoStats supports:

- Enumerated masks, where each pixel value identifies a class.
- Bit-packed masks, where fields such as cloud, cloud shadow, cirrus, or snow occupy individual bits.

The request supplies the mask legend unless the source STAC metadata provides it. Keeping the legend with the request makes the masking behavior explicit and reproducible.

## Geometry inputs

GeoStats accepts two geometry input tiers:

| Input | When to use | Private-preview limit |
| --- | --- | --- |
| Inline GeoJSON FeatureCollection | Tests and small, ad hoc analyses | 1 to 100 features |
| STAC asset reference | Large or recurring analyses | Reference a GeoParquet or supported vector asset already stored on a STAC item |

The complete JSON request must be smaller than 10,000,000 bytes. Arrow attachments aren't supported in the private-preview API.

For recurring analysis, specify `geometryIdColumn` for a stable business key. GeoStats carries that value into the output so you can reliably join results to the source geometries. If you omit it, GeoStats uses the geometry's position in the submitted source; positional identity isn't reliable across reordered or reingested datasets.

## Spatial modes

GeoStats distinguishes polygon aggregation from point sampling because they have different semantics:

- **Zonal mode** aggregates pixels within polygons. You can choose area weighting so boundary pixels contribute in proportion to their overlap with each polygon.
- **Sample mode** extracts raster values at points by using nearest-neighbor or bilinear interpolation.

You can optionally buffer input geometries before analysis. Buffer distances are expressed in meters and applied after the geometry is transformed to the raster coordinate reference system.

## Results and provenance

GeoStats can write results as GeoParquet, Delta, or GeoJSON. A successful run registers the result as a STAC item in the selected output collection. The item points to the result asset and records run provenance, so you use normal GeoCatalog discovery and authorization to access it.

Result rows include the source geometry identity, observation or period timing, calculation statistics, coverage, status, and source-item provenance as applicable to the selected strategy. Empty periods and unusable observations are represented by status values rather than omitted rows, which helps downstream workflows distinguish missing imagery from masked pixels. Run-level failures are reported on the asynchronous operation.

For example, an item-mode computation that requests `mean` for a calculation named `ndvi` can produce rows like these. Values are illustrative.

| geometry_id | item_id | timestamp | ndvi_mean | ndvi_count | status |
| --- | --- | --- | ---: | ---: | --- |
| zone-001 | scene-2026-08-05 | 2026-08-05T10:42:11Z | 0.61 | 1834.7 | `ok` |
| zone-001 | scene-2026-08-10 | 2026-08-10T10:40:54Z | null | 0.0 | `noValidPixels` |

Calculation and statistic names form wide result columns such as `ndvi_mean`. In item mode, every intersecting acquisition produces a row even when masking removes all pixels. The null statistic and `noValidPixels` status preserve that acquisition in the time series and explain why it has no value. Counts are coverage-weighted pixel areas and can be fractional.

Temporal `mosaic` and `all` computations use `period_start`, `period_end`, and `is_partial` instead of an item timestamp. They can also report `belowValidFraction` when clear coverage is below the requested threshold and `noItems` when no scene intersects a feature in a period.

## Image chips

An `item` or `mosaic` computation can optionally add an `image_chips` binary column to the result. Each value is a cropped Cloud Optimized GeoTIFF (COG) containing the requested band expressions for that row's geometry bounding box. Chips preserve pixels outside the exact geometry boundary, and the analytical mask used for statistics doesn't blank chip pixels.

Each decoded or encoded chip is limited to 1,048,576 bytes. If a chip exceeds the limit, its value is null while the row's statistics and status remain unchanged. Image chips aren't supported with the `all` observation strategy and aren't resized automatically.

## Asynchronous operations

GeoStats runs and estimates are always asynchronous. A submission returns `202 Accepted` with an `operation-location` header that points to the standard GeoCatalog operation resource. Status values are `Pending`, `Running`, `Succeeded`, `Canceling`, `Canceled`, and `Failed`.

Each submission creates a new operation. Don't automatically retry a submission after an ambiguous network failure because the first request might already have started a run. Check the operation and computation run list before resubmitting.

The estimate endpoint plans the same geometry partitions and STAC searches as a run without reading raster values or publishing results. It reports feature, item, pixel, and partition counts and identifies partitions predicted to exceed worker capacity. An estimate isn't a price or duration quote.

## Access and security

GeoStats uses the same Microsoft Entra ID authentication, GeoCatalog authorization, and tenant isolation as other GeoCatalog data-plane APIs. Request a token for the `https://geocatalog.spatio.azure.com/.default` scope. A user or application must also have access to the source collection, geometry asset, and output collection used by the computation.

## Private-preview limitations

The following limitations apply to the private preview:

- GeoStats must be enabled by the Microsoft Planetary Computer Pro team for each GeoCatalog.
- Raster data and referenced geometry assets must be available in the GeoCatalog where the computation runs.
- Inline GeoJSON is limited to 100 features, and the complete JSON request must be smaller than 10,000,000 bytes.
- Runs and estimates are asynchronous; no synchronous execution path is available.
- The API version is `2026-10-01-preview`.
- Feature behavior, supported formats, and service limits can change during the preview.

## Next step

> [!div class="nextstepaction"]
> [Use GeoStats to calculate zonal statistics](./use-geostats.md)
