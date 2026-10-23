---
title: OGC API - Tiles API reference
description: Find the OpenAPI definition and key endpoints for OGC API - Tiles in Microsoft Planetary Computer Pro.
author: beharris
ms.author: beharris
ms.service: planetary-computer-pro
ms.topic: reference
ms.date: 10/23/2026
---

# OGC API - Tiles API reference

Microsoft Planetary Computer Pro implements OGC API - Tiles for standards-based discovery and delivery of vector and map tiles. Vector tile operations serve Mapbox Vector Tiles (MVT) backed by the PMTiles archives generated during ingestion.

The API is available at `/visual` under API version `2026-10-01-preview`. It replaces the earlier proof-of-concept routes under `/data/vector` and `/data/tiles`. The old routes aren't available and don't redirect to `/visual`.

> [!IMPORTANT]
> OGC API - Tiles is a private preview and must be enabled on the GeoCatalog. The `api-version` query parameter is required on every request. An authorized `/visual` request returns `404` when the feature isn't enabled.

## Get the API definition for your GeoCatalog

Each enabled GeoCatalog publishes its own version-filtered API definition. Use these resources as the authoritative reference for the operations and schemas available to your catalog:

| Resource | URL |
| --- | --- |
| OGC landing page | `https://<geocatalog-host>/visual?api-version=2026-10-01-preview` |
| OpenAPI document | `https://<geocatalog-host>/visual/api?api-version=2026-10-01-preview` |
| Human-readable API reference | `https://<geocatalog-host>/visual/api.html?api-version=2026-10-01-preview` |
| Conformance declaration | `https://<geocatalog-host>/visual/conformance?api-version=2026-10-01-preview` |

Start at the landing page and follow the advertised links instead of constructing resource URLs when possible. The OpenAPI document contains only the routes available in `2026-10-01-preview` and is kept in sync with the deployed service.

All requests require a Microsoft Entra bearer token:

```http
GET https://<geocatalog-host>/visual?api-version=2026-10-01-preview
Authorization: Bearer <access-token>
```

## Key vector tile resources

The API can serve vector tiles from the full GeoCatalog dataset, a collection, an item, or a registered search. Common collection resources include:

| Resource | Path |
| --- | --- |
| Collection | `/visual/collections/{collectionId}` |
| Vector tileset list | `/visual/collections/{collectionId}/tiles` |
| Vector tileset metadata | `/visual/collections/{collectionId}/tiles/{tileMatrixSetId}` |
| Vector tile | `/visual/collections/{collectionId}/tiles/{tileMatrixSetId}/{tileMatrix}/{tileRow}/{tileCol}` |
| Collection styles | `/visual/collections/{collectionId}/styles` |
| Styled vector tile | `/visual/collections/{collectionId}/styles/{styleId}/tiles/{tileMatrixSetId}/{tileMatrix}/{tileRow}/{tileCol}` |

Append `?api-version=2026-10-01-preview` to every path.

Vector tiles use the media type `application/vnd.mapbox-vector-tile` and `WebMercatorQuad`. Tile coordinates are ordered as tile matrix, row, and column (`z/y/x`), not the `z/x/y` order common in XYZ templates.

For example:

```http
GET https://<geocatalog-host>/visual/collections/<collection-id>/tiles/WebMercatorQuad/4/6/7?api-version=2026-10-01-preview
Accept: application/vnd.mapbox-vector-tile
Authorization: Bearer <access-token>
```

## Styles

OGC API - Tiles uses Mapbox Style Specification v8 documents for vector portrayal. The service stores and validates the stylesheet, while the client renders the MVT with it. A vector tile can also be requested without a style.

Styles are resources under `/visual/styles` or a collection's `/styles` path. A style selected for a tile is named in the path as `styles/{styleId}`; the API doesn't use a `style` query parameter.

## Related content

- [Vector data in Microsoft Planetary Computer Pro](../docs/vector-data-overview.md)
- [OGC API - Tiles](https://ogcapi.ogc.org/tiles/)
