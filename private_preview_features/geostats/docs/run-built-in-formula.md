---
title: Quickstart - Run a built-in GeoStats formula (Private Preview)
description: Discover formulas compatible with a raster collection and run one without writing an expression or mapping bands manually.
author: beharris
ms.author: beharris
ms.service: planetary-computer-pro
ms.topic: quickstart
ms.date: 10/30/2026
#customer intent: As a GeoStats user, I want to use a formula compatible with my raster collection so that I don't have to write expressions or map source bands manually.
---

# Quickstart: Run a built-in GeoStats formula (Private Preview)

In this quickstart, you discover the built-in formulas available for a raster collection and run Normalized Difference Vegetation Index (NDVI) by referencing its formula ID. You don't write an expression, choose source assets, or map bands manually.

This preset-first workflow is recommended for collections copied from the Open Planetary Computer. A built-in formula stores the expression and the band mapping that GeoStats resolved for that specific collection. This mapping is especially useful for products whose required bands are stored in separate assets or at different native resolutions.

> [!IMPORTANT]
> GeoStats is available only to approved private-preview participants. The feature must be enabled for your GeoCatalog by the Microsoft Planetary Computer Pro team.

## Prerequisites

Before you begin, you need:

- An existing GeoCatalog with GeoStats enabled.
- The **GeoCatalog Administrator** role on the GeoCatalog.
- A raster collection in the GeoCatalog. This example uses a copy of the Open Planetary Computer `sentinel-2-l2a` collection.
- [Azure CLI](/cli/azure/install-azure-cli) installed and signed in to the tenant that contains the GeoCatalog.

The examples use API version `2026-10-01-preview`.

## Set request values

Set these environment variables. Replace the endpoint, collection ID, and date range with values from your GeoCatalog.

```bash
export GEOCATALOG_ENDPOINT="https://<catalog>.<hash>.<region>.geocatalog.spatio.azure.com"
export RASTER_COLLECTION_ID="<raster-collection-id>"
export COMPUTATION_ID="built-in-ndvi-quickstart"
export GEOSTATS_API_VERSION="2026-10-01-preview"

export ACCESS_TOKEN=$(az account get-access-token \
  --scope https://geocatalog.spatio.azure.com/.default \
  --query accessToken \
  --output tsv)
```

Use the GeoCatalog data-plane endpoint, not the Azure Resource Manager resource ID. Don't include a trailing slash in `GEOCATALOG_ENDPOINT`.

## Find formulas available to the collection

List the formulas that GeoStats has resolved for your raster collection:

```bash
curl --request GET \
  "${GEOCATALOG_ENDPOINT}/stac/collections/${RASTER_COLLECTION_ID}/formulas?api-version=${GEOSTATS_API_VERSION}" \
  --header "Authorization: Bearer ${ACCESS_TOKEN}"
```

The response contains a `value` array. Each entry includes an `id`, a description, an expression, and the band mapping resolved for this collection. For example, a compatible collection can include a formula whose ID is `ndvi`:

```json
{
  "value": [
    {
      "id": "ndvi",
      "name": "ndvi",
      "description": "Normalized Difference Vegetation Index",
      "expression": "(nir - red) / (nir + red)",
      "bandMapping": {
        "nir": { "assetKey": "<resolved-nir-asset>" },
        "red": { "assetKey": "<resolved-red-asset>" }
      }
    }
  ]
}
```

Treat the list response as the source of truth. Formula availability is collection-specific and can change when collection metadata changes.

> [!NOTE]
> Open Planetary Computer origin alone doesn't guarantee that a formula is available. During ingestion, the GeoCatalog must preserve the collection and item band metadata and the assets required by the formula. GeoStats seeds a built-in formula only when every required EO common-name band resolves without ambiguity. If metadata or an asset needed by a selected formula is missing at run time, GeoStats returns an error instead of guessing.

If `ndvi` isn't listed, don't copy the formula or asset keys from another collection. Confirm that the collection and its items preserve the source band metadata and required assets. See [Built-in formulas](./geostats-overview.md#built-in-formulas) for formula requirements and the validated Open Planetary Computer compatibility matrix.

You can inspect the exact saved formula before using it:

```bash
curl --request GET \
  "${GEOCATALOG_ENDPOINT}/stac/collections/${RASTER_COLLECTION_ID}/formulas/ndvi?api-version=${GEOSTATS_API_VERSION}" \
  --header "Authorization: Bearer ${ACCESS_TOKEN}"
```

## Save a computation that references the formula

Create a file named `computation.json`. The calculation contains only the formula ID. Don't add an expression, band mapping, or band-mapping override.

```json
{
  "dataSource": {
    "source": "self",
    "datetime": "<start-date-time>/<end-date-time>"
  },
  "calculations": [
    { "formulaId": "ndvi" }
  ],
  "statistics": ["mean", "count"],
  "observationStrategy": {
    "mode": "item"
  }
}
```

Replace the date-time placeholders, and then save the computation:

```bash
curl --request PUT \
  "${GEOCATALOG_ENDPOINT}/stac/collections/${RASTER_COLLECTION_ID}/computations/zonal-statistics/${COMPUTATION_ID}?api-version=${GEOSTATS_API_VERSION}" \
  --header "Authorization: Bearer ${ACCESS_TOKEN}" \
  --header "Content-Type: application/json" \
  --data @computation.json
```

The service returns `201 Created` for a new computation or `200 OK` when it replaces an existing computation. Saving the computation doesn't run it.

## Run the computation

Create a file named `run.json` with a small test polygon that overlaps your imagery. Coordinates use WGS 84 longitude and latitude.

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
    "format": "geoparquet"
  }
}
```

Submit the run and save its response headers:

```bash
curl --dump-header run-response-headers.txt --request POST \
  "${GEOCATALOG_ENDPOINT}/stac/collections/${RASTER_COLLECTION_ID}/computations/zonal-statistics/${COMPUTATION_ID}:run?api-version=${GEOSTATS_API_VERSION}" \
  --header "Authorization: Bearer ${ACCESS_TOKEN}" \
  --header "Content-Type: application/json" \
  --data @run.json
```

The service returns `202 Accepted`. Copy the URL from the `operation-location` response header and poll it:

```bash
export OPERATION_URL="<operation-location-value>"

curl --request GET \
  "${OPERATION_URL}" \
  --header "Authorization: Bearer ${ACCESS_TOKEN}"
```

When the operation reports `Succeeded`, GeoStats has written the GeoParquet result and registered it as a STAC item in the raster collection. Result columns include `ndvi_mean` and `ndvi_count`.

## Troubleshoot formula availability

| Result | Meaning | Action |
| --- | --- | --- |
| The formula list includes `ndvi` | GeoStats resolved the required `nir` and `red` bands for this collection. | Reference `{ "formulaId": "ndvi" }` in the computation. |
| The formula list is empty or doesn't include the formula you need | One or more required bands are absent, ambiguous, or not described by preserved EO metadata. | Check the collection and item metadata and required assets. Don't guess asset keys. |
| Saving or running returns a formula or band-resolution error | The saved formula no longer resolves against the current collection or one or more selected items don't expose its required assets and metadata. | Recheck the formula list and inspect the selected STAC items. Correct and reingest incomplete metadata when necessary. |
| The operation succeeds but returns no rows | No source items intersected both the date range and test geometry. | Verify the collection extent, item dates, and polygon coordinates. |

## Next step

For output collections, quality masks, observation strategies, estimates, large geometry inputs, and result discovery, continue to [Use GeoStats to calculate zonal statistics](./use-geostats.md).

## Related content

- [GeoStats overview](./geostats-overview.md)
- [GeoStats REST API specification](../spec/openapi.json)