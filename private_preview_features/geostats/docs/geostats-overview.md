---
title: GeoStats in Microsoft Planetary Computer Pro overview (Private Preview)
description: Learn how GeoStats computes raster-derived statistics for polygons and publishes analysis-ready results.
author: beharris
ms.author: beharris
ms.service: planetary-computer-pro
ms.topic: overview
ms.date: 10/21/2026
#customer intent: As a geospatial analyst, I want to understand GeoStats so that I can derive table-ready statistics from raster data without building my own distributed processing system.
---

# What is GeoStats in Microsoft Planetary Computer Pro? (Private Preview)

GeoStats computes raster-derived statistics for geometries at scale. You select raster observations from a SpatioTemporal Asset Catalog (STAC) collection, define one or more band calculations and statistics, and submit analysis geometries. GeoStats publishes an analysis-ready table and can optionally include image chips with the result.

In the private preview, GeoStats uses raster collections, geometry inputs, authorization, storage, and result discovery provided through Microsoft Planetary Computer Pro GeoCatalog. This data access pattern can evolve after the preview.

GeoStats supports workflows such as:

- Calculate standard raster indices over areas and time, such as vegetation, water, burn, and moisture indices.
- Summarize environmental conditions within administrative or operational boundaries.
- Produce table-ready features for forecasting, risk modeling, and reporting.

> [!IMPORTANT]
> GeoStats is available only to approved private-preview participants. The API, limits, and behavior can change before general availability. Contact the Microsoft Planetary Computer Pro team with your Azure Subscription ID and GeoCatalog ID if you are interested in participating.

## How GeoStats works

Defining a GeoStats analysis starts with the raster observations, geometries, calculations, and statistics you want to combine. The API separates the reusable analysis settings from the inputs and output settings that can change for each run.

| Input | What you define | Where you supply it |
| --- | --- | --- |
| Raster collection | The STAC collection containing the raster items and assets to analyze. Formulas and computations are scoped to this collection. | Collection ID in the API request URL |
| Raster selection | The bounded time range used to select STAC items from the raster collection. | Saved computation |
| Input geometry | The polygons to analyze, supplied as an inline GeoJSON FeatureCollection or as a vector asset referenced from a STAC item. You can identify a property to carry into the result as a stable geometry ID. | Run request |
| Calculation | A derived raster value defined either by referencing a saved formula or by providing an inline expression and band mapping. A computation can include multiple calculations. | Saved computation; reusable formulas are saved separately on the raster collection |
| Statistics | The reducers to apply to each calculation, such as `mean`, `count`, or `percentile_90`. | Saved computation |
| Observation handling | Whether matching items are processed independently with `item`, resolved into a `mosaic`, or pooled with `all`, plus any temporal grouping. | Saved computation |
| Data-quality options | An optional quality mask and, for temporal analysis, a minimum valid-coverage threshold. | Saved computation |
| Geometry processing | An optional buffer that grows each input polygon before GeoStats selects contributing pixels. | Run request |
| Output | The result format, STAC collection registration, and optional storage location. | Run request |

A saved computation can be run repeatedly with different geometries or output destinations. To change the raster time range, calculations, statistics, observation strategy, or other reusable analysis settings, update the computation or save another one. Saving a formula or computation doesn't execute the analysis.

For the complete REST workflow to discover or save a formula, save a computation, estimate and submit a run, monitor the asynchronous operation, and find its output, see [Use GeoStats to calculate zonal statistics](./use-geostats.md).

| Term | Meaning |
| --- | --- |
| Formula | A reusable, collection-scoped expression and band mapping. |
| Calculation | A derived raster band used by a computation, defined inline or by referencing a saved formula. |
| Statistic | A reducer such as `mean`, `count`, or `percentile_90` applied to a calculation. |
| Computation | A saved definition containing the raster selection, observation strategy, mask, calculations, and statistics. |
| Run | One execution of a computation with geometry input and output settings. |

## Calculations and statistics

GeoStats evaluates band arithmetic before reducing pixels to statistics. For example, you can calculate Normalized Difference Vegetation Index (NDVI) with the expression `(nir - red) / (nir + red)`. A band mapping binds each expression name to a physical STAC asset and, for a multiband asset, an optional band name or 1-based index:

```json
{
	"expression": "(nir - red) / (nir + red)",
	"bandMapping": {
		"nir": { "assetKey": "B05" },
		"red": { "assetKey": "B04" }
	}
}
```

You can define calculations in either of these ways:

- **Saved formula** - A collection-scoped expression and band mapping that computations reference by `formulaId`.
- **Inline calculation** - An expression and band mapping stored directly in one computation.

Saved and inline calculations use the same expression and band-mapping concepts, but have different request shapes and lifecycles. A formula reference can't be combined with inline fields or band-mapping overrides. List the formulas currently available to a collection with `GET /stac/collections/{collectionId}/formulas`; availability can vary by collection and preview configuration.

### Built-in formulas

When a collection declares compatible bands using STAC Electro-Optical (EO) common names, GeoStats automatically adds the corresponding built-in formulas. A formula is added only when all of its required bands can be resolved without ambiguity.

| Formula ID | Index | Required EO common-name bands |
| --- | --- | --- |
| `bsi` | Bare Soil Index | `swir16`, `red`, `nir`, `blue` |
| `ebbi` | Enhanced Built-Up and Bareness Index | `swir16`, `nir`, `lwir11` |
| `evi2` | Two-band Enhanced Vegetation Index | `nir`, `red` |
| `ibi` | Index-based Built-up Index | `swir16`, `nir`, `red`, `green` |
| `nbr` | Normalized Burn Ratio | `nir`, `swir22` |
| `ndbi` | Normalized Difference Built-up Index | `swir16`, `nir` |
| `ndmi` | Normalized Difference Moisture Index | `nir`, `swir16` |
| `ndre` | Normalized Difference Red Edge Index | `nir`, `rededge` |
| `ndsi` | Normalized Difference Snow Index | `green`, `swir16` |
| `ndvi` | Normalized Difference Vegetation Index | `nir`, `red` |
| `ndwi` | Normalized Difference Water Index | `green`, `nir` |

In the October 2026 validation snapshot, 11 of 138 Open Planetary Computer collections receive at least one built-in formula when copied into a GeoCatalog. This compatibility matrix was validated against collection metadata and, except where noted, by running each listed formula over a real STAC item.

| Open Planetary Computer collection | Built-in formulas | Notes |
| --- | --- | --- |
| `sentinel-2-l2a` | `bsi`, `evi2`, `ibi`, `nbr`, `ndbi`, `ndmi`, `ndsi`, `ndvi`, `ndwi` | `ndre` isn't added because multiple assets declare `rededge`; `ebbi` requires `lwir11`. |
| `landsat-c2-l2` | `bsi`, `ebbi`, `evi2`, `ibi`, `nbr`, `ndbi`, `ndmi`, `ndsi`, `ndvi`, `ndwi` | Uses `nir08` as the NIR band. |
| `naip` | `evi2`, `ndvi`, `ndwi` | The collection doesn't declare SWIR bands. |
| `hls2-s30` | `bsi`, `evi2`, `ibi`, `nbr`, `ndbi`, `ndmi`, `ndsi`, `ndvi`, `ndwi` | `ebbi` requires `lwir11`. |
| `hls2-l30` | `bsi`, `ebbi`, `evi2`, `ibi`, `nbr`, `ndbi`, `ndmi`, `ndsi`, `ndvi`, `ndwi` | All required bands resolve unambiguously. |
| `modis-09A1-061` | `bsi`, `evi2`, `ibi`, `nbr`, `ndbi`, `ndmi`, `ndsi`, `ndvi`, `ndwi` | Uses `nir08` as the NIR band; `ebbi` requires `lwir11`. |
| `modis-43A4-061` | `bsi`, `evi2`, `ibi`, `nbr`, `ndbi`, `ndmi`, `ndsi`, `ndvi`, `ndwi` | Uses `nir08` as the NIR band; `ebbi` requires `lwir11`. |
| `landsat-c2-l1` | `evi2`, `ndvi`, `ndwi` | Uses `nir08` as the NIR band; the collection doesn't declare SWIR bands. |
| `aster-l1t` | `evi2`, `ibi`, `ndbi`, `ndmi`, `ndsi`, `ndvi`, `ndwi` | Uses `nir08` as the NIR band; multiple assets declare `swir22`. |
| `planet-nicfi-analytic` | `evi2`, `ndvi`, `ndwi` | Formula availability was verified, but running them requires access to the licensed imagery. |
| `modis-09Q1-061` | `evi2`, `ndvi` | Uses `nir08` as the NIR band; the collection doesn't declare SWIR or green bands. |

Other Open Planetary Computer collections don't currently receive built-ins because their metadata doesn't declare all bands required by a formula or declares a required band ambiguously across multiple assets. Collection metadata and built-in definitions can change, so use the formulas endpoint as the source of truth for the formulas available in a specific GeoCatalog collection.

A computation can apply multiple calculations and statistics in one pass over the raster data. Supported statistics are `mean`, `min`, `max`, `count`, `sum`, `stddev`, `median`, and integer percentiles from `percentile_1` through `percentile_99`.

## Observation strategies

The observation strategy determines how matching STAC items contribute to the result.

| Mode | How observations contribute | Result rows | Interpretation of `<calculation>_count` |
| --- | --- | --- | --- |
| `item` | Each matching STAC item is processed independently. This mode is the default. | One row for each intersecting feature-item pair. | Valid coverage-weighted pixel area for that feature-item pair. |
| `mosaic` | Items are ordered by an explicit priority, and the first valid pixel at each location contributes. | One row per feature, or per feature and period. | Valid coverage-weighted pixel area in the resolved mosaic. |
| `all` | Every valid pixel observation from every matching item contributes. | One row per feature, or per feature and period. | Valid observation weight across all contributing items. |

Adding calculations or statistics adds columns, not rows. In `item` mode, a feature that intersects two STAC items produces two rows. A feature that intersects no item produces no placeholder row. In `mosaic` and `all` modes, each feature produces one row for the complete time range or one row per requested period, including periods with no usable imagery.

### Compare item, mosaic, and all

Consider one polygon that fully covers two pixels on a common grid. An earlier item contains values 0.2 and 0.4. A later item contains 0.6 at the first pixel and nodata at the second. The following simplified outputs request `mean` and `count`; no quality mask or reprojection changes the values.

In `item` mode, each intersecting item produces an independent row:

| geometry_id | item_id | value_mean | value_count | status |
| --- | --- | ---: | ---: | --- |
| zone-001 | item-earlier | 0.3 | 2.0 | `ok` |
| zone-001 | item-later | 0.6 | 1.0 | `ok` |

In `mosaic` mode with `priority: latest`, the later value wins at the first pixel and the earlier value supplies the second pixel because the later item is nodata there. The resolved values 0.6 and 0.4 produce one row:

| geometry_id | item_count | value_mean | value_count | status |
| --- | ---: | ---: | ---: | --- |
| zone-001 | 2 | 0.5 | 2.0 | `ok` |

In `all` mode, all three valid observations contribute. The values 0.2, 0.4, and 0.6 produce one row:

| geometry_id | item_count | value_mean | value_count | status |
| --- | ---: | ---: | ---: | --- |
| zone-001 | 2 | 0.4 | 3.0 | `ok` |

This example uses whole pixels, so each contributes a weight of 1. Polygon-boundary pixels contribute fractional weights. Real `mosaic` and `all` runs can also reproject observations to a common grid, which can change the exact values and weights.

For `mosaic` and `all`, you can group observations into periods. `temporal.period` accepts a positive integer number of days (`PnD`), weeks (`PnW`), calendar months (`PnM`), or calendar years (`PnY`). The minimum is `P1D`. Sub-day, zero, fractional, and compound durations such as `PT1H` and `P1DT12H` aren't supported. No explicit application-level maximum period or period count is currently enforced, but processing resources and date/time representability still impose practical limits.

In `mosaic` mode, you must choose `earliest`, `latest`, or `preferLeastCloudy`. GeoStats orders matching STAC items by that priority and uses the first valid pixel at each location. `preferLeastCloudy` ranks whole STAC items by `eo:cloud_cover`; it doesn't automatically apply a per-pixel quality mask.

For example, suppose an earlier STAC item has a valid pixel value of 0.2 and `eo:cloud_cover` of 30, while a later item has a valid value of 0.6 and cloud cover of 10:

| Priority | Pixel selected at that location |
| --- | --- |
| `earliest` | 0.2 from the earlier item |
| `latest` | 0.6 from the later item |
| `preferLeastCloudy` | 0.6 from the item with lower collection-level cloud cover |

If the first pixel in the selected order is invalid, GeoStats considers the next item.

Periods start at the beginning of the requested `datetime` range. For example, `P1W` over `2026-06-03/2026-06-20` produces:

| period_start | period_end | is_partial |
| --- | --- | --- |
| 2026-06-03T00:00:00Z | 2026-06-10T00:00:00Z | false |
| 2026-06-10T00:00:00Z | 2026-06-17T00:00:00Z | false |
| 2026-06-17T00:00:00Z | 2026-06-20T00:00:00Z | true |

The service includes the final partial period; callers can't drop or reject it. Omitting `temporal.period` reduces the complete bounded time range as one period. Supplying `temporal` requires `mosaic` or `all` mode.

In `all` mode, GeoStats places matching STAC items on a common temporal grid, pools every valid pixel observation, and then applies the requested statistics. It doesn't average item-level statistics equally. Reprojection can make an `all` result differ slightly from a value reconstructed from item-mode sums and counts.

## Quality masks

Quality masking is optional and opt-in. Omitting `mask` doesn't automatically apply dataset-specific cloud, shadow, snow, or other quality masks. Raster nodata and intrinsic raster masks still apply, and non-finite source or calculation values are excluded. GeoStats supports:

- Enumerated masks, where each pixel value identifies a class.
- Bit-packed masks, where fields such as cloud, cloud shadow, cirrus, or snow occupy individual bits.

The request supplies the mask legend unless the source STAC metadata provides it. Classification metadata can resolve an explicitly requested mask's encoding; metadata alone doesn't enable masking.

> [!CAUTION]
> Mask encodings vary by raster product. An incorrect class or bit mapping can produce plausible but incorrect statistics. Validate a small, known area and time range against the source product before scaling up.

## Geometry inputs

GeoStats accepts two geometry input tiers:

| Input | When to use | Private-preview limit |
| --- | --- | --- |
| Inline GeoJSON FeatureCollection | Tests and small, ad hoc analyses | 1 to 100 features |
| STAC asset reference | Large or recurring analyses | Reference a GeoParquet or supported vector asset already stored on a STAC item |

One input feature is one vector record containing one geometry and optional properties. Limits count features, so a multipart geometry in one record counts as one feature.

The complete JSON request must be smaller than 10,000,000 bytes. Arrow attachments aren't supported in the private-preview API.

For recurring analysis, specify `geometryIdColumn` for a stable business key. GeoStats carries that value into the output so you can reliably join results to the source geometries. If you omit it, GeoStats uses the geometry's position in the submitted source; positional identity isn't reliable across reordered or reingested datasets.

## Polygon analysis

GeoStats calculates zonal statistics for polygons. Boundary pixels contribute in proportion to the fraction of each pixel inside the polygon. This area weighting is always applied and isn't customer-selectable. For example, four valid pixels that are each one-quarter covered contribute a combined `<calculation>_count` of 1.0.

You can optionally buffer input geometries before analysis. A positive buffer grows each polygon before GeoStats selects pixels and calculates statistics, so it can change the resulting count and values. Buffer distances are expressed in meters and applied after the geometry is transformed to the raster coordinate reference system. Omit the buffer to analyze the polygon as drawn.

For example, a polygon containing 10 complete valid pixels has a weighted count of 10. If buffering adds four pixels that are each half covered, the count becomes 12 and those four values contribute at half weight to statistics.

## Results and provenance

GeoStats writes GeoParquet by default and can also write GeoJSON or Delta. Use Delta with a stable `output.location` when the result must be exposed as a table through a OneLake shortcut. A successful run registers the result as a STAC item for every format.

If you omit `output.stacCollectionId`, GeoStats registers the result item in the original raster collection. If you name another existing collection, it registers the item there instead. GeoStats doesn't create that collection. The underlying file remains in GeoCatalog-managed storage; `stacCollectionId` controls STAC registration, while `output.location` controls the relative storage path and is required for Delta.

The primary access path is to discover the result STAC item and use its table asset. If enabled, OGC API Features can query an output collection as GeoJSON. Delta supports OneLake integration, and a collection-level SAS token can provide temporary direct access to file-based assets.

Result rows include the source geometry identity, observation or period timing, calculation statistics, coverage, status, and source-item provenance as applicable to the selected strategy. Row cardinality depends on the observation strategy:

| Strategy | Result rows |
| --- | --- |
| `item` | Each input feature gets one row for every intersecting STAC item, so one feature can produce many rows. A feature with no intersecting item produces no row, and a successful run can publish an empty table. |
| `mosaic` or `all`, without a period | One row for each input feature. |
| `mosaic` or `all`, with a period | One row for each input feature in each period, including periods with no usable imagery. |

Calculations and statistics become columns, so adding them doesn't add rows. Run-level failures are reported on the asynchronous operation.

Output columns vary by strategy, requested statistics, and optional features:

| Category | Examples | When present |
| --- | --- | --- |
| Feature identity | `feature_index`, `geometry_id` | Every row includes positional identity; a stable geometry ID is carried when configured. |
| Item provenance | `item_id`, `timestamp`, `band_assets` | `item` rows. |
| Temporal provenance | `period_start`, `period_end`, `is_partial`, `item_count` | `mosaic` and `all` rows. |
| Coverage | `spatial_valid_fraction`, `valid_observation_count`, `observation_fraction` | Temporal rows when applicable. |
| Requested statistics | `ndvi_mean`, `ndvi_count`, or another `<calculation>_<statistic>` column | One column for each requested calculation-statistic combination. |
| Result state | `status` | Every row. |
| Optional output | `image_chips` | When requested for `item` or `mosaic`. |

For example, an item-mode computation that requests only `mean` for a calculation named `ndvi` can produce this minimal result. Values are illustrative.

| geometry_id | item_id | timestamp | ndvi_mean | status |
| --- | --- | --- | ---: | --- |
| zone-001 | item-2026-08-05 | 2026-08-05T10:42:11Z | 0.61 | `ok` |
| zone-001 | item-2026-08-10 | 2026-08-10T10:40:54Z | null | `noValidPixels` |

Calculation and statistic names form wide result columns such as `ndvi_mean`. In item mode, every intersecting STAC item produces a row even when no usable pixels remain. The null statistic and `noValidPixels` status preserve that item in the time series and explain why it has no value.

Temporal `mosaic` and `all` computations use `period_start`, `period_end`, and `is_partial` instead of an item timestamp. They can also report `belowValidFraction` when clear coverage is below the requested threshold and `noItems` when no STAC item intersects a feature in a period.

Use the row status and coverage columns to decide how to handle each result. `temporal.minValidFraction` defaults to `0.0`, which applies no minimum coverage threshold. `belowValidFraction` therefore occurs only when the caller supplies a higher threshold.

| Status | Triggering configuration and condition | Suggested action |
| --- | --- | --- |
| `ok` | Usable values remained and any explicit valid-fraction threshold was met. | Use the value. |
| `belowValidFraction` | The caller set `temporal.minValidFraction` above `0.0`, and `spatial_valid_fraction` was lower. | Relax the threshold, lengthen the period, or apply a downstream threshold. |
| `noValidPixels` | At least one STAC item intersected the feature, but nodata, intrinsic masks, non-finite values, or an explicit quality mask removed every value. This can occur without `mask`. | Check source data, calculations, and any requested quality mask. |
| `noItems` | No STAC item in the period intersected the feature. | Verify collection coverage, revisit interval, and time range. |

`minValidFraction` is evaluated per feature and period against `spatial_valid_fraction`, not against a STAC item's `eo:cloud_cover`. The `item_count` includes intersecting STAC items even when all their pixels are unusable, which distinguishes `noValidPixels` from `noItems`.

For polygons, `<calculation>_count` is the sum of valid pixel-overlap fractions, not the number of touched cells. Three fully covered valid pixels and one half-covered valid pixel produce a count of 3.5. For `item` and `mosaic`, count represents valid coverage-weighted pixel area. For `all`, it represents valid observation weight across all contributing STAC items.

### Tested strategy examples

An item-mode UAT used one polygon and two intersecting HLS L30 STAC items. It requested `mean`, `sum`, and `count` for the same source band:

| STAC item | value_mean | value_sum | value_count | status |
| --- | ---: | ---: | ---: | --- |
| HLS item 1 | 0.263235166 | 7316.869886 | 27795.943822 | `ok` |
| HLS item 2 | 0.416673688 | 2.055826 | 4.933899 | `ok` |

The matching `all` run placed both items on a common reprojected temporal grid and produced one period row:

| item_count | value_mean | value_sum | value_count | status |
| ---: | ---: | ---: | ---: | --- |
| 2 | 0.263265236 | 7319.206709 | 27801.645289 | `ok` |

The pixel-pooled mean predicted from the item rows was 0.263262397, while their equal-item average was 0.339954427. The observed result confirms that `all` pools pixel observations rather than averaging item means. The small difference from the pooled prediction comes from reprojection onto the temporal grid.

A separate mosaic UAT used `priority: latest`, a cloud-quality mask, reprojection, and 625 input polygons. It produced exactly one successful row per polygon, with no duplicate geometry IDs. At each grid location, only the first valid pixel in the selected STAC-item order contributed to that row; repeated observations weren't pooled as they are in `all` mode.

## Image chips

An `item` or `mosaic` computation can optionally add an `image_chips` binary column. GeoStats produces one Cloud Optimized GeoTIFF (COG) chip per result row, not one chip per pixel. Each chip covers the geometry's rectangular bounding box, so it includes pixels outside the exact polygon boundary. The analytical quality mask used for statistics doesn't blank pixels in the chip.

```text
+-----------------------+  geometry bounding box and chip extent
|      _________        |
|     / polygon \       |  statistics use the polygon
|     \_________/       |  chip retains every bounding-box pixel
+-----------------------+
```

Each decoded or encoded chip is limited to 1,048,576 bytes. If a chip exceeds the limit, its value is null while the row's statistics and status remain unchanged. Image chips aren't supported with the `all` observation strategy and aren't resized automatically.

## Asynchronous operations

GeoStats runs and estimates are always asynchronous. A submission returns `202 Accepted` with an `operation-location` header that points to the standard GeoCatalog operation resource. Status values are `Pending`, `Running`, `Succeeded`, `Canceling`, `Canceled`, and `Failed`.

Each submission creates a new operation. Don't automatically retry a submission after an ambiguous network failure because the first request might already have started a run. Check the operation and computation run list before resubmitting.

The estimate endpoint plans the same geometry partitions and STAC searches as a run without reading raster values or publishing results. Successful estimate operations expose feature, item, feature-item pair, pixel, read-pixel, partition, maximum-scene, and capacity counters in `additionalInformation`. `FeatureItemPairs` is an upper bound based on feature and item search counts, not a prediction of result-table rows. An estimate isn't a price or duration quote. For the request and response workflow, see [Estimate the run](./use-geostats.md#estimate-the-run).

## Access and security

GeoStats uses the same Microsoft Entra ID authentication, GeoCatalog authorization, and tenant isolation as other GeoCatalog data-plane APIs. Request a token for the `https://geocatalog.spatio.azure.com/.default` scope. A user or application must also have access to the source collection, geometry asset, and output collection used by the computation.

## Private-preview limitations

The following limitations apply to the private preview:

- Access is limited to approved participants whose Azure subscription ID has been allow-listed by the Microsoft Planetary Computer Pro team.
- Raster data and referenced geometry assets must be available in the GeoCatalog where the computation runs.
- Inline GeoJSON is limited to 100 features, and the complete JSON request must be smaller than 10,000,000 bytes.
- Runs and estimates are asynchronous; no synchronous execution path is available.
- The API version is `2026-10-01-preview`.
- Feature behavior, supported formats, and service limits can change during the preview.

## Next step

> [!div class="nextstepaction"]
> [Use GeoStats to calculate zonal statistics](./use-geostats.md)
