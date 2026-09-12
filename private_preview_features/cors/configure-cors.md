---
title: Configure CORS for a GeoCatalog resource (Preview)
description: Learn how to request a Cross-Origin Resource Sharing (CORS) configuration for your Microsoft Planetary Computer Pro GeoCatalog and verify that browser applications can access your data.
author: aloverro
ms.author: adamloverro
ms.service: planetary-computer-pro
ms.topic: how-to
ms.date: 09/11/2026
#customer intent: As a developer, I want to configure CORS on my GeoCatalog and verify it works so that my browser-based application can access GeoCatalog data directly.
---

# Configure CORS for a GeoCatalog resource (Preview)

This article shows you how to request a Cross-Origin Resource Sharing (CORS) configuration for your GeoCatalog and verify that a browser-based application can access your data across origins. For background on how CORS works with GeoCatalog, see [What is CORS for Microsoft Planetary Computer Pro?](./cors-overview.md).

> [!IMPORTANT]
> CORS for GeoCatalog is currently in preview. During preview, you request a configuration by opening a support ticket. Self-service configuration through the Azure portal and Resource Manager APIs is planned for a later release.

## Prerequisites

- An Azure subscription with an existing [GeoCatalog resource](https://learn.microsoft.com/azure/planetary-computer/deploy-geocatalog-resource).
- **GeoCatalog Administrator** access on the resource. See [Manage access to Microsoft Planetary Computer Pro](https://learn.microsoft.com/azure/planetary-computer/manage-access).
- The fully qualified **HTTPS** origin your application is served from (for example, `https://app.contoso.com`).

> [!IMPORTANT]
> CORS is not a security boundary. It controls which browser origins can read responses—it doesn't authenticate or authorize requests. Every request to GeoCatalog still requires a valid Microsoft Entra ID access token. See [Configure application authentication](https://learn.microsoft.com/azure/planetary-computer/application-authentication).

## Step 1: Gather your configuration values

Before you open a support ticket, decide on the values below. Providing complete, correct values lets the support engineer apply your configuration in a single step.

| Setting | What to provide | Notes |
| --- | --- | --- |
| **GeoCatalog resource** | The full resource ID or the GeoCatalog endpoint URL | For example, `https://<name>.<hash>.<region>.geocatalog.spatio.azure.com` |
| **Allowed origins** | One or more fully qualified HTTPS origins | Exact match only. No wildcards. Up to 50. |
| **Max age** | Preflight cache duration in seconds | For example, `3000` (50 minutes) |

Allowed origins and max age are the only values you provide. The allowed HTTP methods and headers are set by the platform and can't be configured per GeoCatalog.

> [!TIP]
> Include every origin your application uses, including any separate development origin (such as `https://localhost:8443`). Requests from origins that aren't on the list are blocked by the browser.

### Origin requirements

- Origins must be fully qualified and use **HTTPS**: `https://app.contoso.com`.
- Wildcard origins (`*`) and subdomain wildcards (`https://*.contoso.com`) aren't supported in preview.
- An origin is the scheme, host, and port only—don't include a path. `https://app.contoso.com` is valid; `https://app.contoso.com/maps` is not.

> [!TIP]
> For local development, generate a locally trusted HTTPS certificate with a tool such as [mkcert](https://github.com/FiloSottile/mkcert), then serve your app over HTTPS. The origin you register is `https://localhost:<port>`, not `http://localhost:<port>`.

## Step 2: Request the configuration

Open an Azure support ticket for your GeoCatalog resource and include the values from [Step 1](#step-1-gather-your-configuration-values). For help creating a request, see [Create an Azure support request](/azure/azure-portal/supportability/how-to-create-azure-support-request).

Azure Support confirms when the configuration is in place.

## Step 3: Verify CORS from a browser

Because CORS is enforced by the browser, the most reliable way to confirm your configuration is to make a real cross-origin request from your application's origin. Command-line tools like `curl` can show response headers but don't reproduce browser preflight and same-origin enforcement.

> [!NOTE]
> Browsers don't expose the `Access-Control-Allow-*` headers to JavaScript—they're consumed by the browser internally. So you can't confirm CORS by reading those headers in code: either the request succeeds and you get a response (CORS allowed it), or the browser blocks it and the `fetch()` call fails with a `TypeError`. To inspect the exact CORS headers the server returned, use your browser's developer tools **Network** tab and look at the preflight (`OPTIONS`) response.

### Verify the data plane API

From your application (served from an allowed HTTPS origin), call the STAC API and confirm the request succeeds:

```javascript
try {
  const response = await fetch(
    `${catalogUrl}/stac/collections?api-version=2026-04-15`,
    {
      method: 'GET',
      mode: 'cors',
      headers: { 'Authorization': `Bearer ${accessToken}` },
    }
  );
  // If CORS is configured for this origin, the request resolves and the body is readable.
  console.log(response.status); // 200
  console.log(await response.json());
} catch (error) {
  // A blocked cross-origin request rejects with a TypeError.
  console.error('Request failed (possible CORS block):', error);
}
```

If the origin isn't allowed, the browser blocks the response and `fetch()` throws a `TypeError`. Check the browser's developer console for a CORS error message.

### Verify managed storage range reads

To confirm assets stream directly from managed storage, first obtain an authorized asset URL (for example, by getting a SAS token as described in [SAS tokens: Download raw assets](https://learn.microsoft.com/en-us/azure/planetary-computer/build-web-application#sas-tokens-download-raw-assets) and applying it to the STAC asset href), then request a byte range from that URL.

```javascript
const response = await fetch(assetUrl, {
  method: 'GET',
  mode: 'cors',
  headers: { 'Range': 'bytes=0-16383' },
});

const bytes = await response.arrayBuffer();
console.log(response.status);   // 206 Partial Content
console.log(bytes.byteLength);  // 16384 bytes returned
```

A `206 Partial Content` response with the requested bytes confirms that cross-origin range reads from managed storage work.

> [!NOTE]
> The browser enforces CORS regardless of how you authenticate. Even when an asset URL includes a SAS token, the managed storage account must have CORS configured for the browser to read the response.

## Update or remove a configuration

To add, change, or remove allowed origins, open a new support ticket describing the update. CORS configurations persist across GeoCatalog updates and deployments. To remove cross-origin access entirely, request that your CORS configuration be cleared. After the change takes effect, cross-origin requests from previously allowed origins are blocked again.

## Troubleshooting

| Symptom | Likely cause | Resolution |
| --- | --- | --- |
| `fetch()` throws a CORS `TypeError` | The request origin isn't on the allowed list, or the configuration hasn't propagated yet | Confirm the exact origin (scheme, host, port) is registered. |
| Request returns `401` or `403` | Missing or invalid access token | CORS doesn't bypass authentication—include a valid Bearer token. See [Configure application authentication](https://learn.microsoft.com/azure/planetary-computer/application-authentication) |
| `localhost` origin rejected | Non-HTTPS origins can't be registered | Serve your local app over HTTPS so the browser sends an `https://` origin |

## Next steps

- [Build a web application with Microsoft Planetary Computer Pro](https://learn.microsoft.com/azure/planetary-computer/build-web-application)

## Related content

- [What is CORS for Microsoft Planetary Computer Pro?](./cors-overview.md)
- [Connect and build applications with your data](https://learn.microsoft.com/azure/planetary-computer/build-applications-with-planetary-computer-pro)
- [Configure application authentication](https://learn.microsoft.com/azure/planetary-computer/application-authentication)
- [MDN: Cross-Origin Resource Sharing (CORS)](https://developer.mozilla.org/docs/Web/HTTP/CORS)
