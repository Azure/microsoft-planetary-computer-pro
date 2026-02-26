# Architecture

## Overview

The ArcGIS Publishing Automation pipeline bridges Microsoft Planetary Computer (MPC) Pro GeoCatalogs with ArcGIS Enterprise, enabling automated discovery and publication of cloud-optimized imagery.

## Data Flow

```
  ┌──────────────┐
  │  Trigger      │  Timer (Azure Functions), Scheduled Task (VM),
  │               │  or Manual (Notebook Server)
  └──────┬───────┘
         │
         ▼
  ┌──────────────┐     ┌─────────────────────────┐
  │  1. STAC      │────►│  MPC Pro GeoCatalog      │
  │     Query     │     │  (STAC Search API)       │
  │               │◄────│  Returns item metadata   │
  └──────┬───────┘     │  + raw blob URLs         │
         │              └─────────────────────────┘
         │
         ▼
  ┌──────────────┐     ┌─────────────────────────┐
  │  2. Dedup     │────►│  ArcGIS Image Collection │
  │     Check     │     │  (Query catalog/Name)    │
  │               │◄────│  Returns existing IDs    │
  └──────┬───────┘     └─────────────────────────┘
         │
         │ New items only
         ▼
  ┌──────────────┐
  │  3. URL       │  Maps blob URLs to data store paths:
  │     Mapping   │  https://acct.blob.../container/path/cog.tif
  │               │  → /cloudStores/store_name/path/cog.tif
  └──────┬───────┘
         │
         ▼
  ┌──────────────┐     ┌─────────────────────────┐
  │  4. Add       │────►│  ArcGIS Image Collection │
  │     Rasters   │     │  (add_rasters / create)  │
  └──────┬───────┘     └─────────────────────────┘
         │
         ▼
  ┌──────────────┐     ┌─────────────────────────┐
  │  5. Publish/  │────►│  ArcGIS Image Server     │──────┐
  │     Refresh   │     │  (Imagery Layer)         │      │
  └──────────────┘     └─────────────────────────┘      │
                                                          │ Direct blob
                                                          │ access via
                                                          │ registered Planetary
                                                          │ Computer Pro
                                                          │ data store
                                                          ▼
                                                   ┌──────────────┐
                                                   │ Azure        │
                                                   │ Storage      │
                                                   │ (COGs)       │
                                                   └──────────────┘
```

## Component Architecture

### Core Pipeline (`src/`)

| Module | Responsibility |
|---|---|
| `config.py` | YAML config loading, validation, env var interpolation |
| `stac_client.py` | MPC Pro SDK wrapper for authenticated STAC searches |
| `imagery_manager.py` | ArcGIS image collection CRUD, deduplication, URL mapping |
| `service_publisher.py` | Imagery layer publish/refresh on Image Server |
| `pipeline.py` | Orchestrates the full workflow |
| `run.py` | CLI entry point with args parsing |

### Deployment Wrappers

All three deployment methods use the **same core pipeline** — only the trigger mechanism differs:

```
┌─────────────────────────────────────────────────────────────┐
│                     Core Pipeline (src/)                     │
│  stac_client → imagery_manager → service_publisher          │
└────────────────────────────┬────────────────────────────────┘
                             │
         ┌───────────────────┼───────────────────┐
         │                   │                   │
  ┌──────┴──────┐    ┌──────┴──────┐    ┌──────┴──────┐
  │ Azure       │    │ Windows     │    │ ArcGIS      │
  │ Functions   │    │ Scheduled   │    │ Notebook    │
  │ (Timer)     │    │ Task        │    │ Server      │
  └─────────────┘    └─────────────┘    └─────────────┘
```

## Authentication Flows

### Azure Functions

```
Timer Trigger
    │
    ▼
Function App (Python)
    │
    ├─ DefaultAzureCredential (User-Assigned MI)
    │   └─ AZURE_CLIENT_ID / AZURE_TENANT_ID from app settings
    │       └─ Gets Bearer token for GeoCatalog scope
    │           └─ Queries STAC API
    │
    └─ ArcGIS Enterprise (username/password from app settings or Key Vault)
        └─ REST API calls to Image Server
```

The Function App's managed identity needs:
- **GeoCatalog Reader** on the MPC Pro GeoCatalog resource

### VM Scheduled Task

```
Windows Task Scheduler
    │
    ▼
Python script (run.py)
    │
    ├─ DefaultAzureCredential (System-Assigned MI)
    │   └─ VM's managed identity
    │       └─ Gets Bearer token → STAC API
    │
    └─ ArcGIS Enterprise (config.yaml credentials)
        └─ REST API calls to Image Server
```

The VM's managed identity needs:
- **GeoCatalog Reader** on the MPC Pro GeoCatalog resource

### ArcGIS Notebook Server

```
Scheduled Notebook Task (or manual run)
    │
    ▼
Notebook in Docker container
    │
    ├─ DefaultAzureCredential
    │   ├─ Option A: IMDS passthrough (VM's MI)
    │   └─ Option B: Env vars (service principal)
    │       └─ Gets Bearer token → STAC API
    │
    └─ ArcGIS Enterprise
        ├─ Option A: Portal-integrated auth (implicit)
        └─ Option B: Explicit username/password
```

## Key Design Decisions

### `arcgis` package over `arcpy`

The `arcgis` Python package is a pure REST client that can run anywhere — Azure Functions, any VM, Docker containers — without requiring ArcGIS Server/Pro licenses on the client. This eliminates the need for VM Run Command or other remote execution mechanisms from Azure Functions.

### Image Collections over Mosaic Datasets

Image Collections are the modern cloud-native approach in ArcGIS Enterprise. They are:
- Manageable entirely via REST API (no arcpy needed)
- Designed for cloud-stored imagery (COGs, CRFs)
- Support incremental additions via `add_rasters()`
- Have a queryable catalog for deduplication

### Raw Blob URLs over SAS Tokens

SAS tokens are short-lived and unsuitable for published imagery services. Instead:
1. ArcGIS Image Server is configured with a **registered [Planetary Computer Pro](https://enterprise.arcgis.com/en/portal/latest/use/add-data-store-item.htm) data store** pointing to each GeoCatalog collection's storage container
2. The pipeline discovers STAC items and extracts raw blob URLs
3. These URLs are mapped to data store paths (`/cloudStores/<name>/path/to/cog.tif`)
4. Image Server accesses the COGs directly using its own storage credentials

### MPC Pro SDK for STAC Queries

The MPC Pro SDK (`azure-planetarycomputer`) provides:
- Built-in `DefaultAzureCredential` integration (no manual token management)
- Typed search parameters with CQL2-JSON filter support
- Automatic API versioning
- Pagination handling

This was chosen over:
- **pystac-client**: Would need a custom `StacApiIO` subclass for Bearer token injection
- **ArcGIS built-in STAC**: Unclear support for Bearer token authentication
- **Raw HTTP requests**: Works but verbose; requires manual token lifecycle management

## Infrastructure

The Bicep templates deploy:

| Resource | Purpose |
|---|---|
| User-Assigned Managed Identity | Authentication to GeoCatalog + storage |
| Function App (Flex Consumption) | Timer-triggered pipeline execution |
| App Service Plan | Hosting for the Function App |
| Storage Account | Function App runtime storage + config blob container |
| Log Analytics + App Insights | Monitoring and logging |
| Role Assignments | GeoCatalog Reader on the GeoCatalog resource |
| Role Assignments | Storage Blob Data Contributor on the storage account |

The ArcGIS Server VMs are **not** provisioned by these templates — they are assumed to already exist.
