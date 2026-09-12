---
title: Cross-Origin Resource Sharing (CORS) for Microsoft Planetary Computer Pro (Preview)
description: Learn how Cross-Origin Resource Sharing (CORS) lets browser-based applications access GeoCatalog APIs and managed storage assets directly, and how to request a CORS configuration during preview.
author: aloverro
ms.author: adamloverro
ms.service: planetary-computer-pro
ms.topic: overview
ms.date: 09/11/2026
#customer intent: As a developer building a browser-based geospatial application, I want to understand how CORS works with GeoCatalog so that my web app can access STAC APIs, tiles, and cloud-native assets directly from the browser.
---

# What is CORS for Microsoft Planetary Computer Pro? (Preview)

Cross-Origin Resource Sharing (CORS) lets a browser-based application hosted on one origin (for example, `https://app.contoso.com`) call your GeoCatalog resource on a different origin (for example, `https://<name>.<hash>.<region>.geocatalog.spatio.azure.com`). By default, web browsers block these cross-origin requests. Configuring CORS on your GeoCatalog tells the browser that requests from the origins you trust are allowed.

With CORS configured, your web application can talk to GeoCatalog directly from the browser with no proxy server required—to:

- Search and discover data with the **STAC API**.
- Load map tiles from the **Tiler API**.
- Stream cloud-native assets (Cloud Optimized GeoTIFF, GeoParquet, and Cloud Optimized Point Cloud) directly from **managed storage** using HTTP range requests.

> [!IMPORTANT]
> CORS for GeoCatalog is currently in preview. During preview, you request a CORS configuration by opening a support ticket. Self-service configuration through the Azure portal and Resource Manager APIs is planned for a later release. Features and behavior are subject to change.

## Why CORS matters for cloud-native geospatial data

Cloud-native geospatial formats—[Cloud Optimized Point Cloud (COPC)](https://copc.io/#server-implementation-notes), Cloud Optimized GeoTIFF (COG), and GeoParquet—are designed to be read incrementally over HTTP directly by the browser using range requests. Popular JavaScript mapping libraries, including CesiumJS, deck.gl, MapLibre GL JS, OpenLayers, and Leaflet, use `fetch()` or `XMLHttpRequest` to load this data. All of them need the server to return CORS response headers before the browser hands the data to your application.

## What CORS applies to

A GeoCatalog CORS configuration covers two surfaces that a browser application typically calls:

| Surface | Endpoints | Example browser use |
| --- | --- | --- |
| **Data plane API** | STAC API (`/stac/*`) and Tiler API (`/data/*`) | Search collections, load map tiles |
| **Managed storage** | Blob storage that hosts your ingested assets | Stream COPC, COG, and GeoParquet files with range requests |

A single CORS configuration applies your allowed origins across both surfaces.

## What you configure

For your GeoCatalog, you provide two values:

| Setting | Description | Example |
| --- | --- | --- |
| **Allowed origins** | The exact origins your browser application is served from. Must be fully qualified **HTTPS** origins, with no wildcards. | `https://app.contoso.com` |
| **Max age** | How long (in seconds) the browser caches the preflight result before checking again. | `3000` |

You can configure up to 50 allowed origins per GeoCatalog.

> [!NOTE]
> The allowed HTTP methods and request/response headers are set by the platform and can't be configured per GeoCatalog. The defaults permit the `GET` requests—including HTTP range requests—that browser applications use to read STAC data, tiles, and cloud-native assets. You provide only the allowed origins and the preflight max age.

## CORS is not a security boundary

CORS controls **browser behavior**, not server-side access control. It tells the browser which origins are allowed to read a response. CORS does **not** authenticate or authorize the request. Every request to GeoCatalog still requires a valid Microsoft Entra ID access token; allowing an origin through CORS doesn't grant that origin access to your data. A request from an allowed origin without a valid token still returns `401` or `403`. See [Configure application authentication](https://learn.microsoft.com/azure/planetary-computer/application-authentication).

Because the browser isn't a trusted environment for managing credentials, review the [Backends for Frontends pattern](/azure/architecture/patterns/backends-for-frontends) before choosing between calling GeoCatalog directly with CORS and routing requests through a server-side proxy. CORS is a platform capability you can choose; it isn't a replacement for a secure application architecture.

## Preview limitations

The following limitations apply during preview and may change before general availability:

- **Request through support** — CORS is configured by opening a support ticket. Portal and Resource Manager (ARM) configuration aren't yet available.
- **Exact origin matching only** — You must supply fully qualified HTTPS origins (for example, `https://app.contoso.com`). Wildcard origins (`*`) are prohibited, and subdomain wildcards (`https://*.contoso.com`) aren't supported in preview.
- **HTTPS origins only** — Non-HTTPS origins, including `http://localhost`, can't be registered. To develop locally, serve your app over HTTPS.
- **Propagation delay** — A CORS configuration typically takes effect within five minutes after it's applied.

## Prerequisites

- An Azure subscription with an existing [GeoCatalog resource](https://learn.microsoft.com/azure/planetary-computer/deploy-geocatalog-resource).
- **GeoCatalog Administrator** access on the resource. See [Manage access to Microsoft Planetary Computer Pro](https://learn.microsoft.com/azure/planetary-computer/manage-access).
- A browser-based application served from a fixed HTTPS origin.

## Next steps

- [Configure CORS for a GeoCatalog resource](./configure-cors.md)

## Related content

- [Connect and build applications with your data](https://learn.microsoft.com/azure/planetary-computer/build-applications-with-planetary-computer-pro)
- [Build a web application with Microsoft Planetary Computer Pro](https://learn.microsoft.com/azure/planetary-computer/build-web-application)
- [MDN: Cross-Origin Resource Sharing (CORS)](https://developer.mozilla.org/docs/Web/HTTP/CORS)
- [Azure Storage CORS support](/rest/api/storageservices/cross-origin-resource-sharing--cors--support-for-the-azure-storage-services)
