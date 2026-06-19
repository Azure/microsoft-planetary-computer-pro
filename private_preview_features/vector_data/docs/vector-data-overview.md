---
title: Vector data in Microsoft Planetary Computer Pro overview (Preview)
description: Learn about vector data support in Microsoft Planetary Computer Pro. This article explains how to ingest and cloud-optimize Shapefile, GeoJSON, and GeoParquet files for cloud-native analysis and visualization.
author: beharris
ms.author: beharris
ms.service: planetary-computer-pro
ms.topic: concept-article
ms.date: 01/12/2026

ms.custom:
# customer intent: As a GeoCatalog User I want to understand how vector data is supported in Microsoft Planetary Computer Pro so that I can ingest, manage, and visualize vector data formats.
---
# Vector data in Microsoft Planetary Computer Pro (Preview)

Microsoft Planetary Computer Pro now supports ingestion, cloud optimization, and visualization of vector data files in Shapefile, GeoJSON, and GeoParquet formats. By using this preview feature, you can work with vector datasets alongside your raster and data cube assets, providing a comprehensive platform for geospatial analysis and visualization.

Vector data is optimized for cloud environments through conversion to cloud-native formats: GeoParquet for analysis and PMTiles for visualization. This optimization ensures efficient access and rendering of vector datasets at any scale.

> [!IMPORTANT]
> Vector data support is currently in preview. Features and capabilities are subject to change. Provide your feedback to help improve this functionality.

## Ingestion of vector data

Ingest vector data files into Planetary Computer Pro by using the same workflows as other data types. As with raster and data cube formats, you must first store assets in Azure Blob Storage and create associated Spatiotemporal Asset Catalog (STAC) Items before ingestion.

Supported vector formats include:

- **Shapefile** - The traditional vector format commonly used in GIS applications
- **GeoJSON** - A lightweight, JSON-based format for encoding geographic data structures
- **GeoParquet** - A cloud-native columnar format optimized for large-scale vector data

>[!NOTE]
>Vector data ingestion is currently subject to file size limitations to ensure optimal performance. Please only ingest:
>- Shapefiles less than 2272 MB
>- GeoParquet files less than 1248 MB
>- GeoJSON files less than 1248 MB

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

The process stores the PMTiles archives in blob storage and references them in the STAC items, enabling visualization through the Vector Tiling API.

### STAC item properties that trigger cloud optimization

Within the collection's STAC items, the following conditions must be true for a vector asset to be cloud optimized:

* The asset format is one of the following types:
    - `application/vnd.shp`
    - `application/geo+json`
    - `application/x-parquet`
* The asset has a `roles` field that includes either `data` or `visual` within its list of roles.

If these conditions are met, both GeoParquet and PMTiles assets are generated in blob storage alongside the original asset.

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

## Vector Tiling API

While the Microsoft Planetary Computer Pro Explorer doesn't yet support interactive visualization of vector tiles, the Vector Tiling API enables you to access and render your vector data outside of the web interface.

The Vector Tiling API provides access to vector tiles in standard formats, such as MVT (Mapbox Vector Tiles), that mapping libraries and GIS applications can consume. This access allows you to:

- Build custom web maps by using libraries like Mapbox GL JS, Leaflet, or OpenLayers
- Integrate vector data into desktop GIS applications
- Create specialized visualization applications for your vector datasets

The API automatically serves tiles from the PMTiles archives generated during ingestion, providing efficient, cloud-optimized access to your vector data at any zoom level.

## Integration with desktop GIS applications

Microsoft Planetary Computer Pro's vector data support integrates seamlessly with industry-standard desktop GIS applications, enabling professional workflows and advanced analysis capabilities.

### QGIS integration

QGIS users can access vector data stored in Planetary Computer Pro using several methods. While direct loading through STAC connections isn't currently supported for vector data, you can work with your cloud-optimized vector assets through alternative approaches:

- **Access PMTiles from blob storage** - Load PMTiles assets directly from Azure Blob Storage by using the `/vsicurl/` prefix with a SAS token
- **Use the Vector Tiling API** - Connect to the Vector Tiling API to stream tiles and apply custom styles
- **Download and load locally** - Download PMTiles assets to local storage for offline analysis

By using these methods, you can perform analysis and styling by using QGIS's full suite of vector tools and combine Planetary Computer Pro vector data with local datasets.

> [!NOTE]
> QGIS currently supports cloud-optimized raster formats (COG and COPC) through STAC connections, but vector format support through this method requires additional development. Future updates might expand STAC connection capabilities for vector data.

For detailed instructions on configuring QGIS to access your GeoCatalog, see [Configure QGIS to access a GeoCatalog resource](./configure-qgis.md).

### ArcGIS Pro integration

ArcGIS Pro integration with Planetary Computer Pro vector data is evolving. Current capabilities and limitations include:

- **GeoParquet access via STAC** - Support for loading GeoParquet assets through STAC connections is coming soon. Cloud-optimized assets now use the `.parquet` extension that ArcGIS Pro expects, enabling direct access to vector data with full attribute and spatial query capabilities.
- **PMTiles visualization** - ArcGIS Pro does not currently support PMTiles format through STAC connections
- **Vector Tiling API limitations** - The Vector Tiling API serves Mapbox Vector Tiles (MVT) from PMTiles archives, but ArcGIS Pro's Tile XYZ service doesn't currently support authentication, limiting this approach for secured GeoCatalog resources.

When GeoParquet access is fully enabled, you can:

- Connect to your GeoCatalog directly from the ArcGIS Pro catalog pane
- Access vector layers with full attribute and spatial query capabilities  
- Leverage ArcGIS Pro's advanced cartography and analysis tools
- Incorporate Planetary Computer Pro vector data into ArcGIS workflows and models

For step-by-step guidance on setting up the connection, see [Configure ArcGIS Pro to access a GeoCatalog](./create-connection-arc-gis-pro.md).

## Related content

- [Supported data types in Microsoft Planetary Computer Pro](./supported-data-types.md)
- [Configure QGIS to access a GeoCatalog resource](./configure-qgis.md)
- [Configure ArcGIS Pro to access a GeoCatalog](./create-connection-arc-gis-pro.md)
- [Build applications with Microsoft Planetary Computer Pro](./build-applications-with-planetary-computer-pro.md)
