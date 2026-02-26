# ArcGIS Publishing Automation for MPC Pro (Preview)

Automated pipeline for discovering new imagery from a Microsoft Planetary Computer (MPC) Pro GeoCatalog and publishing it to ArcGIS Enterprise as an imagery layer via Image Server.

## Overview

This tool monitors an MPC Pro GeoCatalog for new imagery (e.g., Sentinel-2, Landsat, NAIP) and automatically adds it to an ArcGIS Image Collection, then publishes or refreshes an imagery layer on ArcGIS Image Server. It supports three deployment methods:

| Deployment Method | Description | Best For |
|---|---|---|
| **Azure Functions** | Timer-triggered serverless function | Hands-off scheduled automation |
| **VM Scheduled Task** | Windows Task Scheduler on the ArcGIS Server VM | Environments without Azure Functions |
| **ArcGIS Notebook Server** | Scheduled notebook task | Users who prefer the ArcGIS notebook experience |

### Architecture

```
┌─────────────────────┐     STAC Search     ┌──────────────────────┐
│   MPC Pro SDK        │◄──────────────────►│   MPC Pro GeoCatalog  │
│   (azure-planetary-  │   (Bearer Token     │   (STAC API)          │
│    computer)         │    via MI/CLI)      │                       │
└────────┬────────────┘                     └──────────────────────┘
         │
         │ Raw blob URLs (no SAS)
         ▼
┌─────────────────────┐                     ┌──────────────────────┐
│   ArcGIS API for    │   REST API calls    │   ArcGIS Enterprise   │
│   Python (arcgis)   │◄──────────────────►│   + Image Server      │
│                     │                     │                       │
└─────────────────────┘                     └──────────┬───────────┘
                                                        │
                                            Direct blob │ access via
                                            registered  │ Planetary Computer
                                            Pro data    │ store
                                                        ▼
                                            ┌──────────────────────┐
                                            │   Azure Storage       │
                                            │   (COGs)              │
                                            └──────────────────────┘
```

**Key design decisions:**
- Uses the **`arcgis` Python package** (ArcGIS API for Python) instead of `arcpy`, enabling the pipeline to run anywhere — including Azure Functions — without ArcGIS Server/Pro installed.
- Uses **raw blob URLs** (not SAS-signed). ArcGIS Image Server accesses COGs directly via a registered [Planetary Computer Pro](https://enterprise.arcgis.com/en/portal/latest/use/add-data-store-item.htm) data store.
- Uses **Image Collections** (the modern cloud-native model) instead of traditional mosaic datasets.

## Prerequisites

1. **MPC Pro GeoCatalog** with one or more imagery collections
2. **ArcGIS Enterprise** with Image Server capability
3. **Azure storage** containing the COGs (same storage backing the GeoCatalog)
4. **[Planetary Computer Pro data store](https://enterprise.arcgis.com/en/portal/latest/use/add-data-store-item.htm)** registered in ArcGIS Enterprise for each GeoCatalog collection
5. **Managed identity** (or service principal) with **GeoCatalog Reader** role assigned on the GeoCatalog resource

## Quick Start

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure

Copy the example configuration and fill in your values:

```bash
cp config.example.yaml config.yaml
# Edit config.yaml with your GeoCatalog endpoint, ArcGIS Enterprise URL, etc.
```

### 3. Register the Planetary Computer Pro data store (one-time setup)

Use the dedicated [register-arcgis-enterprise](../register-arcgis-enterprise/) tool to discover
MPC Pro collections and register them as Planetary Computer Pro data stores on your ArcGIS Enterprise server:

```bash
cd ../register-arcgis-enterprise
pip install -r requirements.txt
cp .env.example .env
# Edit .env with your values
python register_cloud_stores.py
```

### 4. Run

```bash
# Full run
python -m src.run --config config.yaml

# Dry run (query only, no changes)
python -m src.run --config config.yaml --dry-run

# Verbose output
python -m src.run --config config.yaml --verbose
```

## Deployment Guides

| Guide | Description |
|---|---|
| [Azure Functions](doc/azure-functions-guide.md) | Deploy as a timer-triggered Azure Function |
| [VM Scheduled Task](doc/vm-scheduled-task-guide.md) | Run on an ArcGIS Server VM with Windows Task Scheduler |
| [ArcGIS Notebook Server](doc/notebook-server-guide.md) | Run from ArcGIS Notebook Server with scheduled tasks |
| [Architecture](doc/architecture.md) | Detailed architecture and design decisions |

## Configuration Reference

See [config.example.yaml](config.example.yaml) for the full configuration schema with comments. Key sections:

| Section | Purpose |
|---|---|
| `geocatalog` | MPC Pro GeoCatalog endpoint URL |
| `stac_query` | STAC search parameters (collections, bbox, datetime, filter) |
| `image_collection` | Target ArcGIS image collection settings |
| `arcgis_enterprise` | Portal URL and authentication method |
| `cloud_store` | Registered Planetary Computer Pro data store for URL mapping |
| `deployment` | Schedule and logging settings |

## Project Structure

```
publishing-automation/
├── config.example.yaml          # Configuration template
├── requirements.txt             # Python dependencies
├── src/                         # Core pipeline code
│   ├── config.py                # Config loader + validation
│   ├── stac_client.py           # MPC Pro SDK STAC query wrapper
│   ├── imagery_manager.py       # ArcGIS image collection management
│   ├── service_publisher.py     # Imagery layer publishing
│   ├── pipeline.py              # Pipeline orchestrator
│   └── run.py                   # CLI entry point
├── deploy/
│   ├── azure-function/          # Azure Function App code
│   ├── bicep/                   # Infrastructure-as-Code (Bicep)
│   └── scripts/                 # Deployment and setup scripts
├── notebooks/
│   └── publishing_automation.ipynb  # Interactive notebook version
└── doc/                         # Documentation
```

## Authentication

| Deployment | GeoCatalog Auth | ArcGIS Enterprise Auth |
|---|---|---|
| Azure Functions | Function's managed identity → `DefaultAzureCredential` | Service account (app settings / Key Vault) |
| VM Scheduled Task | VM's managed identity → `DefaultAzureCredential` | Username/password or Windows IWA |
| Notebook Server | VM MI (IMDS) or service principal env vars | Portal-integrated or explicit credentials |

## License

See [LICENSE](../../LICENSE) in the repository root.

## Intended use

Please note that this software, scripts, code samples, etc are provided AS IS. They are intended to guide the user to creating their own solution for test and evaluation purposes and they are not intended to be used for production workloads. If you discover issues, have questions, or want to recommend new features or revisions, please open a Github Issue. 