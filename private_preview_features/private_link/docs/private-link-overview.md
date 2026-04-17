---
title: Private Link for Microsoft Planetary Computer Pro
description: Learn about Private Link capabilities for Microsoft Planetary Computer Pro GeoCatalogs, including private endpoints for APIs and storage, and trusted services bypass for secure data ingestion.
author: aloverro
ms.author: adamloverro
ms.service: planetary-computer-pro
ms.topic: overview
ms.date: 03/21/2026
#customer intent: As a security-focused Azure user, I want to understand what Private Link options are available for GeoCatalog so that I can restrict network access and meet my organization's compliance requirements.
---

# What is Private Link for Microsoft Planetary Computer Pro?

Azure Private Link enables you to access Microsoft Planetary Computer Pro GeoCatalog resources over a private endpoint in your virtual network. With Private Link, traffic between your virtual network and GeoCatalog travels over the Microsoft backbone network, eliminating exposure to the public internet. This provides network isolation that helps meet regulatory and compliance requirements.

Microsoft Planetary Computer Pro supports three Private Link scenarios that work together to secure the full lifecycle of geospatial data management: API access, managed storage access, and secure ingestion from customer-owned storage.

## Private Link scenarios

The following table summarizes the Private Link capabilities available for GeoCatalogs:

> [!NOTE]
> Private Link for GeoCatalog is currently in private preview.

| Scenario | What it does | When to use |
|----------|-------------|-------------|
| **Data plane API private endpoint** | Restricts GeoCatalog API access to your virtual network | When you need all API traffic (STAC, ingestion, data / tiling) to stay on a private network |
| **Managed storage private endpoint** | Provides private access to the GeoCatalog-managed blob storage account | When you need to access stored geospatial assets without going over the public internet |
| **Trusted services bypass for customer storage** | Allows GeoCatalog to ingest data from your locked-down storage account | When your source storage has a firewall but needs to allow GeoCatalog ingestion |

### Data plane API private endpoint

A private endpoint for the GeoCatalog data plane APIs creates a network interface with a private IP address in your virtual network. All API requests (collection management, item ingestion, search queries, data and tiling visualization) route through this private connection instead of the public internet.

When combined with disabling public network access on the GeoCatalog, this configuration ensures that only resources within your virtual network (or peered networks) can communicate with the GeoCatalog APIs.

### Managed storage private endpoint

Each GeoCatalog has a managed storage account where ingested geospatial data is stored and served from. A private endpoint to this managed storage account lets you read blob data privately from within your virtual network.

Because the managed storage account is in a Microsoft-managed subscription, creating a private endpoint requires you to connect by resource ID rather than through the Azure portal's resource picker. The connection starts in a **Pending** state and must be approved by the GeoCatalog service team.

### Trusted services bypass for customer storage

When your organization requires that source storage accounts have firewall rules that block public access, you can still allow GeoCatalog to ingest data from those accounts. Azure Storage recognizes GeoCatalog as a trusted Microsoft service. By enabling the **Allow Azure services on the trusted services list** exception on your storage firewall, GeoCatalog can read blob assets during ingestion while all other public traffic remains blocked.

## How Private Link works with GeoCatalog

A private endpoint is a network interface that connects your virtual network to a specific Azure service. Think of it as a secure pipe between your network and GeoCatalog.

When you create a private endpoint:

1. A **network interface** with a private IP address is created in your subnet.
2. A **private link connection** is established between the network interface and the target resource (GeoCatalog or its managed storage account).
3. A **private DNS zone** resolves the service's fully qualified domain name (FQDN) to the private IP address, so that existing applications and scripts continue to work without code changes.

### DNS zones

Each Private Link scenario uses a specific DNS zone:

| Scenario | Private DNS zone |
|----------|-----------------|
| Data plane API | `geocatalog.spatio.azure.com` |
| Managed storage | `privatelink.blob.core.windows.net` |

The DNS zone must be linked to your virtual network so that DNS queries from within the network resolve to the private endpoint's IP address instead of the public IP.

## Prerequisites

To use Private Link with GeoCatalog, you need:

- An Azure subscription with an existing [GeoCatalog resource](./deploy-geocatalog-resource.md)
- A virtual network with at least one subnet for private endpoints
- **GeoCatalog Admin** role (or equivalent) on the GeoCatalog resource
- Azure CLI with the `Microsoft.Orbital` provider registered
    - To register or re-register the resource provider:
    ```bash
    az provider register -n Microsoft.Orbital
    ```
- Subscriptions where you wish to use the Private Link feature must be allowlisted; contact MPC Pro Support to be added to the allowlist.
    - GeoCatalog resources on allowlisted subscriptions will be able to use API version `2025-07-01-preview`; this is required to access/ modify `managedStorageResourceIds` and `publicNetworkAccess` resource properties.

## Limitations

> [!NOTE]
> Private Link for GeoCatalog is currently in private preview. The following limitations apply during the preview period and may change prior to general availability.

- **Managed storage endpoint approval**: Private endpoints to managed storage require approval from the GeoCatalog service team. Follow the instructions in the managed storage guide to contact support for approval. The endpoint stays in **Pending** state until approved.
- **Portal support**: Some Private Link operations (such as deploying a GeoCatalog with public network access disabled) are not yet available in the Azure portal and require Azure CLI.

## Next steps

- [Configure a private endpoint for GeoCatalog data plane APIs](./configure-private-endpoint-data-plane.md)
- [Configure a private endpoint for GeoCatalog managed storage](./configure-private-endpoint-managed-storage.md)
- [Configure customer storage for private ingestion with GeoCatalog](./configure-trusted-services-customer-storage.md)

## Related content

- [Azure Private Link overview](/azure/private-link/private-link-overview)
- [Azure Storage network security](/azure/storage/common/storage-network-security)
- [Deploy a GeoCatalog resource](./deploy-geocatalog-resource.md)
- [Manage access to Microsoft Planetary Computer Pro](./manage-access.md)
