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
- Permission to read the input collections and create GeoStats resources and output items.
- A raster STAC collection in the GeoCatalog. Each item must expose the raster and mask assets used in the requests.
- A STAC item with a GeoParquet or supported vector asset that contains your polygon geometries.
- A unique output collection, computation ID, and output location for this run.
- [Azure CLI](/cli/azure/install-azure-cli) installed and signed in to the tenant that contains the GeoCatalog.

The examples use API version `2026-10-01-preview` and the Microsoft Entra ID scope `https://geocatalog.spatio.azure.com/.default`.

## Set request values

Set the following environment variables. Replace every placeholder with a value from your GeoCatalog.

```bash
export GEOCATALOG_ENDPOINT="https://<catalog>.<hash>.<region>.geocatalog.spatio.azure.com"
export RASTER_COLLECTION_ID="<raster-collection-id>"
export FEATURE_COLLECTION_ID="<feature-collection-id>"
export FEATURE_ITEM_ID="<feature-item-id>"
export FEATURE_ASSET_KEY="<feature-asset-key>"
export GEOMETRY_ID_COLUMN="<stable-id-column>"
export OUTPUT_COLLECTION_ID="<output-collection-id>"
export COMPUTATION_ID="ndvi-by-zone"
export GEOSTATS_API_VERSION="2026-10-01-preview"

export ACCESS_TOKEN=$(az account get-access-token \
  --scope https://geocatalog.spatio.azure.com/.default \
  --query accessToken \
  --output tsv)
```

Use the GeoCatalog data-plane endpoint, not the Azure Resource Manager resource ID. Don't include a trailing slash in `GEOCATALOG_ENDPOINT`.

## Save an NDVI formula

A formula is a reusable calculation scoped to the raster collection in the URL. This example binds the expression names `nir` and `red` to single-band assets. Change the asset keys to match the source STAC items.

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
> Mask encodings vary by raster product. Use offsets and classes from the source product specification or its STAC classification metadata. Incorrect mask definitions can produce plausible but incorrect statistics.

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
      "stacAsset": {
        "collectionId": "<feature-collection-id>",
        "itemId": "<feature-item-id>",
        "assetKey": "<feature-asset-key>"
      },
      "geometryIdColumn": "<stable-id-column>"
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

The service returns `202 Accepted`. Copy the `operation-location` response header and poll it as described in [Monitor the operation](#monitor-the-operation). A successful estimate reports counts as strings in `additionalInformation`, including `FeatureCount`, `ItemCount`, `EstimatedPixels`, `EstimatedReadPixels`, `PartitionCount`, and `PartitionsOverCapacity`.

If `PartitionsOverCapacity` is greater than zero, reduce the time range, geometry size or spread, or number of scenes combined per period. You can also use `item` mode instead of `mosaic` or `all`. The estimate is a capacity prediction, not a price or duration quote.

## Run the computation

Create a file named `run.json`:

```json
{
  "input": {
    "features": {
      "stacAsset": {
        "collectionId": "<feature-collection-id>",
        "itemId": "<feature-item-id>",
        "assetKey": "<feature-asset-key>"
      },
      "geometryIdColumn": "<stable-id-column>"
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

For `Pending` or `Running`, wait for the number of seconds in the original `retry-after` response header before polling again. The `additionalInformation` object includes partition progress counters while a run executes.

## Find the published result

After the operation succeeds, list items in the output collection with the STAC API:

```bash
curl --request GET \
  "${GEOCATALOG_ENDPOINT}/stac/collections/${OUTPUT_COLLECTION_ID}/items?api-version=2025-04-30-preview" \
  --header "Authorization: Bearer ${ACCESS_TOKEN}"
```

Identify the item created by your run and inspect its assets. The result asset points to the GeoParquet table at the output location. Use the item's provenance properties to associate the result with the GeoStats run and source data.

Join result rows back to your input features by using the geometry identifier carried from `geometryIdColumn`. Don't rely on physical row order for a referenced STAC asset.

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

## Use inline GeoJSON for a small analysis

For 1 to 100 features, replace `input.features` in the estimate or run request with an inline RFC 7946 FeatureCollection:

```json
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
}
```

GeoJSON coordinates use WGS 84 longitude and latitude. The complete JSON request must be smaller than 10,000,000 bytes. For larger or recurring inputs, ingest the geometries once and reference their STAC asset.

## Troubleshoot common responses

| Response | Meaning | Action |
| --- | --- | --- |
| `400 ValidationError` | A field combination, identifier, mask, expression, or referenced resource is invalid. | Read the error details, correct the request, and submit it again. |
| `401` or `403` | The token is missing, expired, has the wrong audience, or the principal lacks access. | Request a fresh token for the GeoCatalog scope and verify data-plane permissions. |
| `404` | The collection, formula, or computation doesn't exist, or GeoStats isn't enabled for the GeoCatalog. | Verify identifiers and confirm private-preview enablement. |
| `409 CollectionConfigChanged` | Another collection configuration update won an optimistic-concurrency race. | Read the current formula or collection state and retry the intended update. |
| `413 RequestTooLarge` | The JSON request exceeds the private-preview body limit. | Store the geometries as a GeoParquet asset and reference its STAC item. |
| Operation `Failed` | Validation passed, but planning, raster access, computation, or publication failed asynchronously. | Inspect `error`, `statusHistory`, and partition counters on the operation. |

## Related content

- [GeoStats overview](./geostats-overview.md)
- [GeoStats REST API specification](../spec/openapi.json)
