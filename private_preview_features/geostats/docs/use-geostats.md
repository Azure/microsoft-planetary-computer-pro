---
title: Use GeoStats to calculate zonal statistics (Private Preview)
description: Learn how to save a GeoStats formula and computation, estimate and run zonal statistics, monitor the operation, and discover the published result.
author: beharris
ms.author: beharris
ms.service: planetary-computer-pro
ms.topic: how-to
ms.date: 10/09/2026
#customer intent: As a geospatial analyst, I want to run GeoStats against raster data and field boundaries so that I can use the resulting statistics in analysis and reporting.
---

# Use GeoStats to calculate zonal statistics (Private Preview)

This article shows how to use the GeoStats REST API to calculate mean Normalized Difference Vegetation Index (NDVI) for polygons. You save a reusable formula and computation, estimate the work, submit an asynchronous run, and find the GeoParquet result in your GeoCatalog.

> [!IMPORTANT]
> GeoStats is available only to approved private-preview participants. The feature must be enabled for your GeoCatalog by the Microsoft Planetary Computer Pro team.

## Prerequisites

Before you begin, you need:

- An existing GeoCatalog with GeoStats enabled.
- The **GeoCatalog Administrator** role on the GeoCatalog. The GeoCatalog Reader role can't save or run computations.
- A raster STAC collection in the GeoCatalog. Each item must expose the raster and mask assets used in the requests.
- An output collection for the result STAC item, plus a unique computation ID and output location for this run.
- [Azure CLI](/cli/azure/install-azure-cli) installed and signed in to the tenant that contains the GeoCatalog.

The examples use API version `2026-10-01-preview`.

## Set request values

Set the following environment variables. Replace every placeholder with a value from your GeoCatalog.

```bash
export GEOCATALOG_ENDPOINT="https://<catalog>.<hash>.<region>.geocatalog.spatio.azure.com"
export RASTER_COLLECTION_ID="<raster-collection-id>"
export OUTPUT_COLLECTION_ID="<output-collection-id>"
export COMPUTATION_ID="ndvi-by-zone"
export GEOSTATS_API_VERSION="2026-10-01-preview"
export STAC_API_VERSION="2025-04-30-preview"

export ACCESS_TOKEN=$(az account get-access-token \
  --scope https://geocatalog.spatio.azure.com/.default \
  --query accessToken \
  --output tsv)
```

Use the GeoCatalog data-plane endpoint, not the Azure Resource Manager resource ID. Don't include a trailing slash in `GEOCATALOG_ENDPOINT`.

## Save an NDVI formula

A formula is a reusable calculation stored in, and available only to, the raster collection identified in the URL. This example is for a collection whose items store red and near-infrared data in separate single-band Cloud Optimized GeoTIFF (COG) assets, such as a Sentinel-2 collection. Change the asset keys to match the source STAC items.

Create a file named `formula.json` with the following content:

```json
{
  "id": "ndvi",
  "name": "ndvi",
  "description": "Normalized Difference Vegetation Index",
  "expression": "(nir - red) / (nir + red)",
  "bandMapping": {
    "nir": { "assetKey": "<nir-asset-key>" },
    "red": { "assetKey": "<red-asset-key>" }
  }
}
```

Save the formula:

```bash
curl --request PUT \
  "${GEOCATALOG_ENDPOINT}/stac/collections/${RASTER_COLLECTION_ID}/formulas/ndvi?api-version=${GEOSTATS_API_VERSION}" \
  --header "Authorization: Bearer ${ACCESS_TOKEN}" \
  --header "Content-Type: application/json" \
  --data @formula.json
```

The service returns `201 Created` for a new formula or `200 OK` when it replaces an existing formula. If the body includes `id`, it must match the formula ID in the URL.

For a multiband asset, map both expression names to the same asset and select each band by its metadata name or 1-based index. For example:

```json
"bandMapping": {
  "nir": { "assetKey": "image", "bandName": "nir" },
  "red": { "assetKey": "image", "bandIndex": 4 }
}
```

> [!TIP]
> If the STAC collection declares the Electro-Optical (EO) extension and its bands include common names such as `red` and `nir`, GeoStats might already have preconfigured this formula from the collection metadata. Check the collection's saved formulas before creating a duplicate:
>
> ```bash
> curl --request GET \
>   "${GEOCATALOG_ENDPOINT}/stac/collections/${RASTER_COLLECTION_ID}/formulas?api-version=${GEOSTATS_API_VERSION}" \
>   --header "Authorization: Bearer ${ACCESS_TOKEN}"
> ```

## Save a computation

A computation stores the reusable raster selection and analysis parameters. The run request supplies the geometries and output destination separately.

Create a file named `computation.json`. This example:

- Selects one month of raster observations.
- Excludes cloud, cirrus, adjacent cloud, cloud shadow, and snow by using a bit-packed quality mask.
- References the saved `ndvi` formula.
- Calculates the mean for every matching STAC item independently.

```json
{
  "dataSource": {
    "source": "self",
    "datetime": "<start-date-time>/<end-date-time>"
  },
  "mask": {
    "asset": "<mask-asset-key>",
    "bits": [
      { "name": "cirrus", "offset": 0 },
      { "name": "cloud", "offset": 1 },
      { "name": "adjacentCloud", "offset": 2 },
      { "name": "cloudShadow", "offset": 3 },
      { "name": "snow", "offset": 4 }
    ],
    "exclude": [
      "cirrus",
      "cloud",
      "adjacentCloud",
      "cloudShadow",
      "snow"
    ]
  },
  "calculations": [
    { "formulaId": "ndvi" }
  ],
  "statistics": ["mean"],
  "observationStrategy": {
    "mode": "item"
  }
}
```

> [!CAUTION]
> Mask encodings vary by raster product. Find the mask asset key in a source item's `assets` object, then use the product specification or the asset's STAC classification metadata to identify class values or bit offsets. A legend supplied in this request takes precedence over STAC metadata. Incorrect definitions can produce plausible but incorrect statistics, so first run a small, known area and time range and compare the result with the source mask before scaling up.

Save the computation:

```bash
curl --request PUT \
  "${GEOCATALOG_ENDPOINT}/stac/collections/${RASTER_COLLECTION_ID}/computations/zonal-statistics/${COMPUTATION_ID}?api-version=${GEOSTATS_API_VERSION}" \
  --header "Authorization: Bearer ${ACCESS_TOKEN}" \
  --header "Content-Type: application/json" \
  --data @computation.json
```

The service validates and stores the definition synchronously. It returns `201 Created` for a new computation or `200 OK` when it replaces an existing computation. Saving a computation doesn't execute it.

## Estimate the run

An estimate plans geometry partitions and matching raster items without reading raster values or publishing output. Use it to identify a request that is predicted to exceed worker capacity before you submit the run.

Create a file named `estimate.json`:

```json
{
  "dataSource": {
    "source": "self",
    "datetime": "<start-date-time>/<end-date-time>"
  },
  "input": {
    "features": {
      "geoJson": {
        "type": "FeatureCollection",
        "features": [
          {
            "type": "Feature",
            "geometry": {
              "type": "Polygon",
              "coordinates": [
                [
                  [-120.50, 47.50],
                  [-120.49, 47.50],
                  [-120.49, 47.51],
                  [-120.50, 47.51],
                  [-120.50, 47.50]
                ]
              ]
            },
            "properties": {
              "zone_id": "example-zone"
            }
          }
        ]
      },
      "geometryIdColumn": "zone_id"
    },
    "mode": "zonal"
  },
  "observationStrategy": {
    "mode": "item"
  }
}
```

Submit the estimate:

```bash
curl --include --request POST \
  "${GEOCATALOG_ENDPOINT}/stac/collections/${RASTER_COLLECTION_ID}/computations/zonal-statistics:estimate?api-version=${GEOSTATS_API_VERSION}" \
  --header "Authorization: Bearer ${ACCESS_TOKEN}" \
  --header "Content-Type: application/json" \
  --data @estimate.json
```

The service returns `202 Accepted`. Copy the `operation-location` response header and poll it as described in [Monitor the operation](#monitor-the-operation). A successful estimate reports counts as strings in `additionalInformation`, including `FeatureCount`, `ItemCount`, `FeatureItemPairs`, `EstimatedPixels`, `EstimatedReadPixels`, `PartitionCount`, and `PartitionsOverCapacity`. `FeatureItemPairs` is an upper bound based on the feature and item search counts; it isn't the expected number of rows in the published result table.

If `PartitionsOverCapacity` is greater than zero, reduce the time range, geometry size or spread, or number of scenes combined per period. You can also use `item` mode instead of `mosaic` or `all`. The estimate is a capacity prediction, not a price or duration quote.

## Run the computation

Create a file named `run.json`:

```json
{
  "input": {
    "features": {
      "geoJson": {
        "type": "FeatureCollection",
        "features": [
          {
            "type": "Feature",
            "geometry": {
              "type": "Polygon",
              "coordinates": [
                [
                  [-120.50, 47.50],
                  [-120.49, 47.50],
                  [-120.49, 47.51],
                  [-120.50, 47.51],
                  [-120.50, 47.50]
                ]
              ]
            },
            "properties": {
              "zone_id": "example-zone"
            }
          }
        ]
      },
      "geometryIdColumn": "zone_id"
    },
    "mode": "zonal"
  },
  "output": {
    "stacCollectionId": "<output-collection-id>",
    "location": "<unique-output-location>",
    "writeMode": "overwrite",
    "format": "geoparquet"
  }
}
```

The `location` is relative to the GeoCatalog's configured output sink. Use a unique location unless you intentionally want the selected write mode to modify an existing dataset.

Submit the run and save the response headers:

```bash
curl --dump-header run-response-headers.txt --request POST \
  "${GEOCATALOG_ENDPOINT}/stac/collections/${RASTER_COLLECTION_ID}/computations/zonal-statistics/${COMPUTATION_ID}:run?api-version=${GEOSTATS_API_VERSION}" \
  --header "Authorization: Bearer ${ACCESS_TOKEN}" \
  --header "Content-Type: application/json" \
  --data @run.json
```

The service always returns `202 Accepted` for an accepted run. Open `run-response-headers.txt` and copy the URL from the `operation-location` header.

> [!CAUTION]
> Each successful submission starts a new run. Don't automatically retry after an ambiguous network failure. First list the computation's runs or check the operation ID from the response to determine whether the original request was accepted.

## Monitor the operation

Set the operation URL returned in the response header and poll it. The operation URL is an absolute URL under `/operations/{operationId}`.

```bash
export OPERATION_URL="<operation-location-value>"

curl --request GET \
  "${OPERATION_URL}" \
  --header "Authorization: Bearer ${ACCESS_TOKEN}"
```

Wait for a terminal `status` value:

- `Succeeded` - The output was written and registered as a STAC item.
- `Failed` - Inspect `error` and `statusHistory` for the failure code and message.
- `Canceled` - The operation was canceled before completion. Partial output can remain addressable.

For `Pending` or `Running`, wait for the number of seconds in the original `retry-after` response header before polling again. If that header isn't present, use a bounded polling interval appropriate for your client. The `additionalInformation` object includes partition progress counters while a run executes.

## Find the published result

After the operation succeeds, list items in the output collection with the STAC API:

```bash
curl --request GET \
  "${GEOCATALOG_ENDPOINT}/stac/collections/${OUTPUT_COLLECTION_ID}/items?api-version=${STAC_API_VERSION}" \
  --header "Authorization: Bearer ${ACCESS_TOKEN}"
```

This discovery request uses the GeoCatalog STAC API version, not the GeoStats API version used by the formula, computation, estimate, and run routes.

Identify the item created by your run and inspect its assets. The result asset points to the GeoParquet table at the output location. Use the item's provenance properties to associate the result with the GeoStats run and source data.

Join result rows back to your input features by using the geometry identifier carried from `geometryIdColumn`. An item-mode result from this example contains columns like these:

| Column | Meaning |
| --- | --- |
| `geometry_id` | Value of `zone_id` from the input feature. |
| `item_id` | Source raster STAC item used for the row. |
| `timestamp` | Acquisition time of the source raster item. |
| `ndvi_mean` | Mean NDVI for valid pixels in the polygon. Calculation and statistic names form `<calculation>_<statistic>` columns. |
| `status` | `ok` when the value was computed, or a reason such as `noValidPixels` when it wasn't. |

For example:

| geometry_id | item_id | timestamp | ndvi_mean | status |
| --- | --- | --- | ---: | --- |
| example-zone | scene-2026-08-05 | 2026-08-05T10:42:11Z | 0.61 | `ok` |

### Query the result with OGC API Features

If OGC API Features is enabled for your GeoCatalog, query the output collection as GeoJSON without downloading or parsing GeoParquet:

```bash
curl --request GET \
  "${GEOCATALOG_ENDPOINT}/data/features/collections/${OUTPUT_COLLECTION_ID}/items?limit=100&api-version=${STAC_API_VERSION}" \
  --header "Authorization: Bearer ${ACCESS_TOKEN}" \
  --header "Accept: application/geo+json"
```

The endpoint can also apply spatial and attribute filters so that clients retrieve only the result features they need.

### Download or access the GeoParquet asset

To work with the file directly, use the result asset `href` from the STAC item. You can download the GeoParquet file with a collection-level SAS token from the output collection:

```bash
curl --request GET \
  "${GEOCATALOG_ENDPOINT}/sas/token/${OUTPUT_COLLECTION_ID}?api-version=${STAC_API_VERSION}" \
  --header "Authorization: Bearer ${ACCESS_TOKEN}"
```

SAS token generation uses the GeoCatalog STAC API version, not the GeoStats API version.

Append the returned `token` to the result asset `href`, then use the signed URL with `curl`, an Azure Storage client, or a GeoParquet-compatible tool. SAS tokens are temporary; request a new token when the current one expires.

## Use an inline calculation instead

You can store the expression directly in the computation when it isn't intended for reuse. Replace the `calculations` array in `computation.json` with:

```json
"calculations": [
  {
    "name": "ndvi_custom",
    "expression": "(nir - red) / (nir + red)",
    "bandMapping": {
      "nir": { "assetKey": "<nir-asset-key>" },
      "red": { "assetKey": "<red-asset-key>" }
    }
  }
]
```

An entry must be either a `formulaId` reference or an inline calculation. Don't combine `formulaId` with inline fields or band-mapping overrides.

## Reference reusable or large geometry inputs

The example above uses inline GeoJSON, which is appropriate for 1 to 100 features. If you have more geometries or need to reuse them across runs, ingest a GeoParquet or supported vector asset into the GeoCatalog and replace `input.features` in both the estimate and run requests with a STAC asset reference:

```json
"features": {
  "stacAsset": {
    "collectionId": "<feature-collection-id>",
    "itemId": "<feature-item-id>",
    "assetKey": "<feature-asset-key>"
  },
  "geometryIdColumn": "<stable-id-column>"
}
```

For referenced assets, always supply a stable business key in `geometryIdColumn`. Don't rely on physical row order because ingestion can reorder the source features. Inline GeoJSON coordinates use WGS 84 longitude and latitude, and the complete request must be smaller than 10,000,000 bytes.

## Troubleshoot common responses

| Response | Meaning | Action |
| --- | --- | --- |
| `400 ValidationError` | A field combination, identifier, mask, expression, or referenced resource is invalid. | Read the error details, correct the request, and submit it again. |
| `401` or `403` | The token is missing or expired, or the principal lacks access. | Sign in again, request a fresh token as shown in this article, and verify the **GeoCatalog Administrator** role assignment. |
| `404` | The collection, formula, or computation doesn't exist, or GeoStats isn't enabled for the GeoCatalog. | Verify identifiers and confirm private-preview enablement. |
| `409 CollectionConfigChanged` | Another collection configuration update won an optimistic-concurrency race. | Read the current formula or collection state and retry the intended update. |
| `413 RequestTooLarge` | The JSON request exceeds the private-preview body limit. | Store the geometries as a GeoParquet asset and reference its STAC item. |
| Operation `Failed` | Validation passed, but planning, raster access, computation, or publication failed asynchronously. | Inspect `error`, `statusHistory`, and partition counters on the operation. |

## Related content

- [GeoStats overview](./geostats-overview.md)
- [GeoStats REST API specification](../spec/openapi.json)
