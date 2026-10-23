---
title: Vector data in Microsoft Planetary Computer Pro
description: Learn how to ingest, optimize, visualize, access, and filter vector data in Microsoft Planetary Computer Pro.
author: beharris
ms.author: beharris
ms.service: planetary-computer-pro
ms.topic: concept-article
ms.date: 10/23/2026

ms.custom:
# customer intent: As a GeoCatalog User I want to understand how vector data is supported in Microsoft Planetary Computer Pro so that I can ingest, manage, and visualize vector data formats.
---
# Vector data in Microsoft Planetary Computer Pro

Microsoft Planetary Computer Pro now supports ingestion, cloud optimization, visualization, and feature-level access for vector data. By using this preview feature, you can work with vector datasets alongside your raster and data cube assets, providing a comprehensive platform for geospatial analysis and visualization.

Vector files in Shapefile, GeoJSON, and GeoParquet formats can be converted to cloud-native formats: GeoParquet for analysis and PMTiles for visualization. OGC API - Tiles serves vector tiles backed by the generated PMTiles archives, while OGC API - Features provides another access model for retrieving and filtering individual features.

> [!IMPORTANT]
> Vector data support is currently in preview. Features and capabilities are subject to change. Provide your feedback to help improve this functionality.

## Ingestion of vector data

Ingest vector data files into Planetary Computer Pro by using the same workflows as other data types. As with raster and data cube formats, you must first store assets in Azure Blob Storage and create associated Spatiotemporal Asset Catalog (STAC) Items before ingestion.

Supported vector formats include:

- **Shapefile** - The traditional vector format commonly used in GIS applications
- **GeoJSON** - A lightweight, JSON-based format for encoding geographic data structures
- **GeoParquet** - A cloud-native columnar format optimized for large-scale vector data

> [!NOTE]
> For optimal PMTiles performance, only ingest assets for PMTiles conversion that are within the following size limits:
>
> - Shapefiles less than 2,272 MB
> - GeoParquet files less than 1,248 MB
> - GeoJSON files less than 1,248 MB
>
> These size limits apply only to PMTiles conversion. You can ingest vector assets that exceed these limits if you remove the `visual` role from the STAC item, which skips PMTiles generation during ingestion.

## Cloud optimization of vector data

When you ingest a STAC Item that contains vector assets, the data is automatically cloud optimized through conversion to cloud-native formats. This conversion enables efficient data access and visualization in cloud environments.

### Cloud optimization to GeoParquet

The ingestion process converts vector assets in Shapefile and GeoJSON formats to GeoParquet. GeoParquet is a cloud-native, columnar storage format based on Apache Parquet that provides:

- **Efficient storage** - Columnar compression significantly reduces file sizes.
- **Fast queries** - The column-oriented structure enables quick attribute filtering and spatial queries.
- **Cloud-optimized access** - Metadata and row group statistics allow selective reading of data without downloading entire files.

The process stores GeoParquet files generated during ingestion in blob storage alongside the original assets and enriches STAC items to reference these optimized files.

### Cloud optimization to PMTiles

For visualization purposes, the process also converts vector data to PMTiles format. PMTiles is a single-file archive format for tiled map data that enables:

- **Cloud-optimized tiling** - Tile data is organized for efficient HTTP range requests.
- **Serverless delivery** - No tile server required; you can serve tiles directly from object storage.
- **Scalable rendering** - Efficient rendering of vector data at any zoom level.

The process stores the PMTiles archives in blob storage and references them in the STAC items. OGC API - Tiles serves Mapbox Vector Tiles (MVT) from these archives for scalable visualization.

### STAC item properties that trigger cloud optimization

Within the collection's STAC items, the following conditions must be true for a vector asset to be cloud optimized:

* The asset format is one of the following types:
    - `application/vnd.shp`
    - `application/geo+json`
    - `application/x-parquet`
* The asset has a `roles` field that includes `data`, `visual`, or both within its list of roles.

The `visual` role triggers PMTiles conversion. For assets that exceed the PMTiles conversion limits, remove the `visual` role before ingestion. You can retain the `data` role to ingest the asset without generating PMTiles.

### STAC item enrichment

For each optimized vector asset within the STAC item, add the following fields:

- `msft:vector_converted: true` – Indicates that vector optimization was applied.
- Additional asset entries for the generated GeoParquet and PMTiles files with appropriate format types and roles.

These optimized assets enable efficient analysis and visualization of your vector data in cloud environments.

### Benefits of cloud optimized vector data

Vector data cloud optimization provides several key benefits:

- **Improved performance** - Cloud-native formats enable faster data access and queries.
- **Reduced bandwidth** - Selective reading capabilities minimize data transfer.
- **Scalable visualization** - PMTiles format enables efficient rendering at any scale.
- **Interoperability** - Standard formats work with common geospatial tools and libraries.

### Disabling vector data cloud optimization

If you don't want cloud optimization for your vector assets, disable it by removing `data` and `visual` from the asset's `roles` list in the STAC item JSON before ingestion.

## OGC API - Tiles

OGC API - Tiles provides a standards-based `/visual` endpoint for discovering and retrieving vector tiles. It replaces the earlier Vector Tile API proof-of-concept under `/data/vector`; the old routes aren't available and don't redirect to the new API.

The API serves Mapbox Vector Tiles (MVT) from the PMTiles archives generated during ingestion. Mapping libraries and GIS applications can use these tiles to:

- Build custom web maps by using libraries like Mapbox GL JS, Leaflet, or OpenLayers
- Integrate vector data into desktop GIS applications
- Create specialized visualization applications for your vector datasets

OGC API - Tiles is available under API version `2026-10-01-preview`. Start at the landing page and follow its links to discover collections, tile matrix sets, styles, tilesets, and tiles:

```http
GET https://<geocatalog-host>/visual?api-version=2026-10-01-preview
Authorization: Bearer <access-token>
```

For example, a collection vector tile uses this path:

```http
GET https://<geocatalog-host>/visual/collections/<collection-id>/tiles/WebMercatorQuad/<tile-matrix>/<tile-row>/<tile-column>?api-version=2026-10-01-preview
Accept: application/vnd.mapbox-vector-tile
Authorization: Bearer <access-token>
```

The tile coordinates are ordered as zoom, row, and column (`z/y/x`). This differs from the `z/x/y` order used by many XYZ URL templates. The API also supports dataset, item, and registered-search tile origins and Mapbox Style Specification v8 styles.

> [!IMPORTANT]
> OGC API - Tiles is a private preview and must be enabled on the GeoCatalog. The `api-version` query parameter is required on every request. An authorized request returns `404` when the feature isn't enabled.

For the complete operation list and schemas, see the [OGC API - Tiles API reference](../spec/ogc-tiles-api.md).

### Access vector tiles from QGIS

QGIS users can access vector tiles stored in Planetary Computer Pro in several ways:

- **Access PMTiles from blob storage** - Load PMTiles assets directly from Azure Blob Storage by using the `/vsicurl/` prefix with a SAS token.
- **Use OGC API - Tiles** - Create a generic vector tile connection to stream authenticated MVT tiles from a `/visual/collections/<collection-id>/tiles/WebMercatorQuad/{z}/{y}/{x}` URL. Include `api-version=2026-10-01-preview` and configure the bearer token as an HTTP header.
- **Download and load locally** - Download PMTiles assets to local storage for offline use.

QGIS doesn't currently support loading vector data directly through a STAC connection. For detailed instructions on configuring QGIS to access your GeoCatalog, see [Configure QGIS to access a GeoCatalog resource](./configure-qgis.md).

### Access vector tiles from ArcGIS Pro

ArcGIS Pro doesn't currently support PMTiles through STAC connections. OGC API - Tiles serves MVT from PMTiles archives, but ArcGIS Pro's Tile XYZ service doesn't currently support authentication, which limits this approach for secured GeoCatalog resources.

As an alternative, support for loading GeoParquet assets through STAC connections is coming soon. Cloud-optimized assets use the `.parquet` extension that ArcGIS Pro expects, which will enable direct access to vector data with attribute and spatial query capabilities. For guidance on setting up a GeoCatalog connection, see [Configure ArcGIS Pro to access a GeoCatalog](./create-connection-arc-gis-pro.md).

## Vector Features API

The Vector Features API exposes individual vector features and their properties through the GeoCatalog implementation of [OGC API - Features](https://ogcapi.ogc.org/features/). Unlike OGC API - Tiles, which returns MVT for client-side map rendering, the Vector Features API returns vector features as GeoJSON for query, analysis, and display.

Use the Vector Features API to:

- Discover the feature collections available in a GeoCatalog.
- Retrieve features from a collection as GeoJSON.
- Limit results to a geographic area by using a bounding box (`bbox`). Bounding-box coordinates use OGC CRS84 order: longitude, latitude.
- Filter on feature properties by using Common Query Language (CQL2) JSON expressions and `filter-lang=cql2-json`.
- Select the properties to return, limit the page size, and follow response links to retrieve additional pages.
- Use the same standards-based endpoint from custom applications, QGIS, and ArcGIS Pro.

For the complete operation and schema reference, see the [Vector Features API OpenAPI definition](../spec/vector-features-api.json).

### Access, query, and filter features through the API

Start with the OGC API landing page for your GeoCatalog. From the landing page, follow the advertised links to discover collections and their items. Feature requests use this general path:

```http
GET https://<geocatalog-host>/features/collections/<collection-id>/items?api-version=2026-08-01-preview
Accept: application/geo+json
Authorization: Bearer <access-token>
```

Add `bbox` for spatial filtering or add `filter` and `filter-lang=cql2-json` for property filtering. The service applies these filters before it returns the GeoJSON response, which reduces the amount of data transferred to the client.

> [!IMPORTANT]
> Keep the trailing slash in the landing-page URL (`/features/`). A redirect from a URL without the trailing slash can cause some clients to omit the authorization header. Never include an access token in a shared URL, project file, screenshot, or log.

### Access, query, and filter features from QGIS

QGIS includes a native OGC API Features provider. Create an API Header authentication configuration for the Microsoft Entra bearer token, and then create a WFS / OGC API Features connection to the GeoCatalog landing page. Enable **Only request features overlapping the view extent** so QGIS sends a `bbox` with feature requests and the service performs spatial filtering.

During the current preview, authenticated collection discovery, map display, and extent-based filtering are supported. Native QGIS attribute subset requests might not propagate authentication reliably. To apply a CQL2 property filter, you can send an authenticated request from the QGIS Python Console and load the returned GeoJSON as a temporary layer.

### Access, query, and filter features from ArcGIS Pro

ArcGIS Pro can discover and display collections through a native OGC API Features connection when the endpoint uses an authentication method supported by ArcGIS Pro. The native client sends bounding boxes for extent-based requests, allowing the service to limit the features returned for the visible map area.

For authenticated CQL2 property filtering during the current preview, use an integrated ArcGIS Pro notebook to request filtered GeoJSON and convert the response to a feature class with ArcPy. A native ArcGIS Pro definition query can filter the displayed layer locally, but it isn't currently guaranteed to send a CQL2 filter to the service.

## Related content

- [OGC API - Tiles API reference](../spec/ogc-tiles-api.md)
- [Vector Features API OpenAPI definition](../spec/vector-features-api.json)
- [Supported data types in Microsoft Planetary Computer Pro](./supported-data-types.md)
- [Configure QGIS to access a GeoCatalog resource](./configure-qgis.md)
- [Configure ArcGIS Pro to access a GeoCatalog](./create-connection-arc-gis-pro.md)
- [Build applications with Microsoft Planetary Computer Pro](./build-applications-with-planetary-computer-pro.md)
