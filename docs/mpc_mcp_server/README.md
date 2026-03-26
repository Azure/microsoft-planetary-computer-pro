# <img height="36" width="36" src="media/logo.png" alt="Microsoft Planetary Computer" /> Microsoft Planetary Computer MCP Tools

A Model Context Protocol (MCP) server that enables GitHub Copilot to interact with Microsoft Planetary Computer Pro.

## Table of Contents

- [Overview](#overview)
- [Installation](#installation)
  - [VS Code](#vs-code)
- [User Guide](#user-guide)
  - [Prerequisite](#prerequisite)
  - [Getting Started](#getting-started)
  - [Toolsets](#toolsets)
- [Reference](#reference)
  - [Documentation](#documentation)
  - [Security](#security)
  - [Data Collection](#data-collection)

## Overview

**Microsoft Planetary Computer MCP Tools** is an MCP Server-compatible service that exposes a set of tools for working with geospatial data on [Microsoft Planetary Computer Pro](https://aka.ms/planetarycomputerpro). It provides capabilities for Spatio Temporal Asset Catalog ([STAC](https://learn.microsoft.com/en-us/azure/planetary-computer/stac-overview)) search and discovery, format conversion, and interactive map-based data selection. Delivered as a VS Code extension, the MCP Server allows users to interact with Planetary Computer Pro entirely through natural language queries via GitHub Copilot, eliminating the need to navigate traditional UI workflows and significantly accelerating geospatial analysis and MPC Pro workflows.

Key Capabilities:

- **STAC Search & Discovery**: Browse and search for public datasets from Microsoft Planetary Computer and your private data with Microsoft Planetary Computer Pro GeoCatalog collections by location, time, and metadata
- **Collection Management**: Create, configure, and clone STAC collections—including render options, mosaic definitions, and thumbnails
- **Data Ingestion**: Ingest individual items, batch import, or bulk ingest from Microsoft Planetary Computer APIs into your GeoCatalog
- **Natural Language Interface**: Interact with Planetary Computer Pro entirely through conversational prompts via GitHub Copilot

## Installation

### VS Code

Compatible with both the [Stable](https://code.visualstudio.com/download) and [Insiders](https://code.visualstudio.com/insiders) builds of VS Code.

1. Install the [GitHub Copilot Chat](https://marketplace.visualstudio.com/items?itemName=GitHub.copilot-chat) extension.
2. Install the **Microsoft Planetary Computer Pro MCP Tools** extension.

- Start (or Auto-Start) the MCP Server

**VS Code (version 1.105 or above):** You can configure MCP servers to start automatically using the `chat.mcp.autostart` setting.

#### Enable Autostart

1. Open **Settings** in VS Code.
2. Search for `chat.mcp.autostart`.
3. Select **newAndOutdated** to automatically start MCP servers without manual refresh.

#### Manual Start (if autostart is off)

1. Open Command Palette (`Ctrl+Shift+P` / `Cmd+Shift+P`).
2. Run `MCP: List Servers`.
3. Select `Microsoft Planetary Computer Pro MCP Tools`, then click **Start Server**.
4. **Check That It's Running**
   - Go to the **Output** tab in VS Code.
   - Look for log messages confirming the server started successfully.

- (Optional) Configure server behavior in VS Code settings (search for "Microsoft Planetary Computer Pro MCP")

Installation is complete! Microsoft Planetary Computer MCP Tools is now ready to use in VS Code.

## User Guide

### Prerequisite

The Azure CLI client and an existing Microsoft Planetary Computer Pro GeoCatalog instance must be configured prior to use. Instructions on how to install the Azure CLI are included in this [link](https://learn.microsoft.com/en-us/cli/azure/install-azure-cli?view=azure-cli-latest).

GitHub Copilot Individual/Pro plan required. Agent mode not available in Free mode.

### Getting Started

1. In a PowerShell terminal run `az login` to log in and select the Azure subscription where your GeoCatalog was provisioned.
2. Open GitHub Copilot in [VS Code](https://code.visualstudio.com/docs/copilot/chat/chat-agent-mode) and switch to Agent mode.
3. Click `refresh` on the tools list
   - You should see the "Microsoft Planetary Computer MCP Tools" in the list of tools
4. Try a prompt that uses Planetary Computer context, such as `How many collections are in the Geocatalog <url>`
   - The agent should be able to use the Planetary Computer MCP Tools to complete your query
5. Reference the [Microsoft Planetary Computer MS Learns](https://learn.microsoft.com/en-us/azure/planetary-computer/) page for information on MPC Pro

### List of Tools

✨ Microsoft Planetary Computer MCP Tools function as an assistant layer that augments Microsoft Planetary Computer Pro workflow, helping users to discover, access, and operate geospatial data and services more efficiently. Below is a list of tools, their descriptions, and example prompts to get started:

#### Discovery & Browsing

| **Tool Name** | **Description** | **Sample Prompt** |
| --- | --- | --- |
| `list_mpc_stac_collections` | Browse all available public datasets in Microsoft Planetary Computer | "What satellite datasets are available in Planetary Computer Pro?" |
| `get_mpc_collection_json` | Get detailed metadata about a specific Planetary Computer dataset | "Tell me about the Sentinel-2 collection in Planetary Computer Pro" |
| `list_personal_stac_collections` | List all collections in your private GeoCatalog instance | "Show me all collections in my GeoCatalog" |
| `get_personal_collection_details` | Get details of a specific collection in your GeoCatalog | "Get details for my sentinel-tutorial collection" |
| `get_personal_collection_json` | Retrieve a STAC collection from GeoCatalog | "Fetch the STAC collection metadata for my-collection" |
| `check_personal_collection_exists` | Check if a personal collection exists in GeoCatalog | "Does the naip-2021 collection exist in my GeoCatalog?" |
| `check_mpc_collection_exists` | Check if a Planetary Computer collection exists in GeoCatalog | "Check if sentinel-2-l2a is available in Planetary Computer" |

#### Searching Data

| **Tool Name** | **Description** | **Sample Prompt** |
| --- | --- | --- |
| `search_mpc_items` | Search for satellite imagery in Planetary Computer by location and time | "Find Sentinel-2 imagery over Seattle from January 2024" |
| `search_personal_collection_items` | Search for items within your private GeoCatalog collections | "Search my GeoCatalog for imagery near San Francisco" |
| `search_stac_items` | Search any STAC API with spatial and temporal filters | "Search the Planetary Computer STAC API for Landsat data" |

#### Collection Management

| **Tool Name** | **Description** | **Sample Prompt** |
| --- | --- | --- |
| `create_personal_stac_collection` | Create a new STAC collection from a template | "Create a basic collection called my-imagery" |
| `create_personal_collection_from_mpc` | Clone a Planetary Computer collection to your GeoCatalog | "Create a collection based on Sentinel-2 from Planetary Computer" |
| `create_and_ingest_personal_collection_from_mpc` | Full workflow to copy a collection from external STAC API | "Copy the NAIP collection from Planetary Computer to my GeoCatalog" |
| `delete_personal_collection` | Delete a STAC collection from GeoCatalog | "Delete the test-collection from my GeoCatalog" |

#### Collection Configuration

| **Tool Name** | **Description** | **Sample Prompt** |
| --- | --- | --- |
| `configure_personal_collection_render_options` | Set up visualization presets (Natural Color, NDVI, etc.) | "Configure render options for my Sentinel-2 collection" |
| `configure_collection_mosaic_definitions` | Define filtering rules for dynamic mosaics | "Set up mosaic definitions for my imagery collection" |
| `replace_personal_collection_thumbnail` | Add or update a collection's preview image | "Upload a new thumbnail for my naip-data collection" |
| `delete_personal_collection_thumbnail` | Remove a collection's thumbnail image | "Remove the thumbnail from my test collection" |

#### Ingestion Sources

| **Tool Name** | **Description** | **Sample Prompt** |
| --- | --- | --- |
| `create_ingestion_source` | Register a cloud storage container as a data source | "Set up an ingestion source for my Azure blob container" |
| `list_ingestion_sources` | List all registered ingestion sources | "Show all ingestion sources in my GeoCatalog" |
| `get_ingestion_source_details` | Get details of a specific ingestion source | "Get details for ingestion source abc123" |
| `delete_ingestion_source` | Remove an ingestion source | "Delete ingestion source xyz789" |

#### Data Ingestion

| **Tool Name** | **Description** | **Sample Prompt** |
| --- | --- | --- |
| `ingest_stac_item` | Add a single STAC item to your collection | "Ingest this Sentinel-2 scene into my collection" |
| `batch_ingest_stac_items` | Ingest multiple STAC items at once | "Batch ingest these 5 STAC item files into my collection" |
| `bulk_ingest_stac_items` | Search external API and bulk ingest results | "Bulk ingest Landsat data from Planetary Computer into my collection" |

#### Ingestion Monitoring

| **Tool Name** | **Description** | **Sample Prompt** |
| --- | --- | --- |
| `check_operation_status` | Check status of a single ingestion operation | "Check the status of ingestion operation op-12345" |
| `check_multiple_operations` | Monitor multiple ingestion operations at once | "Check status of all my pending ingestion jobs" |

#### Asset Downloads

| **Tool Name** | **Description** | **Sample Prompt** |
| --- | --- | --- |
| `download_asset_from_url` | Download a geospatial file from a signed URL | "Download the red band from this Sentinel-2 scene" |
| `download_spacenet_chips` | Download SpaceNet 5 training chips | "Download SpaceNet Moscow training chips 990-999" |

#### Item Management

| **Tool Name** | **Description** | **Sample Prompt** |
| --- | --- | --- |
| `delete_stac_item_in_personal_collection` | Delete a STAC item from a collection | "Delete item scene-001 from my collection" |

#### Debugging & Testing

| **Tool Name** | **Description** | **Sample Prompt** |
| --- | --- | --- |
| `generate_jsonrpc_initialize` | Generate JSON-RPC initialization message for debugging | "Generate the MCP initialization handshake message" |
| `generate_jsonrpc_tool_call` | Generate JSON-RPC tool call for debugging | "Generate a JSON-RPC message to call search\_planetary\_computer" |

#### Tool Dispatcher & Discovery

| **Tool Name** | **Description** | **Sample Prompt** |
| --- | --- | --- |
| `call_mpc_tools` | Call any registered MPC tool by name, even those not directly visible | "Call the search\_mpc\_items tool with collection sentinel-2-l2a" |
| `list_available_tools` | List all tools registered in the MCP tool | "List all available tools in Geocatalog Tools MCP" |

### End-to-End Example

**User Objective:** Copy Sentinel-2 L2A (2025) imagery into an MPC Pro GeoCatalog *"california-wildfires-2025-sentinel2-l2a"* Collection for downstream analysis on California wildfires.

**User Prompt:**

> *Can you pull the Sentinel-2 Level-2A satellite imagery data from Microsoft Planetary Computer for the 2025 California wildfires and put it into a new collection in the geocatalog: `https://example.id.region.geocatalog.spatio.azure.com`*

---

**GitHub Copilot:**

*Created 5 todos*

*Starting: **Load geocatalog MCP tools** (1/5)*

*Starting: **Check MPC for Sentinel-2 L2A collection** (2/5)*

*Good, I have all the geocatalog tools loaded. Now let me first verify the Sentinel-2 L2A collection exists on MPC, then use the combined create-and-ingest tool to set everything up. The 2025 California wildfires (Palisades, Eaton fires) primarily affected the Los Angeles area starting January 7, 2025. I'll use a bounding box covering the affected area and a time range covering the fire period.*

Ran `check_mpc_collection_exists`

*Completed with input:*

```json
{
  "collection_id": "sentinel-2-l2a"
}
```

*Result: exists = true, HTTP 200*

*Starting: **Search MPC items for CA wildfires area** (3/5)*

*Sentinel-2 L2A exists on MPC. Now let me search for items covering the 2025 California wildfire area. The major fires were in the Los Angeles area (Palisades Fire near Pacific Palisades, Eaton Fire near Altadena). I'll use a bounding box roughly covering the LA wildfire zone and a date range from early January through late January 2025.*

Ran `search_mpc_items`

*Completed with input:*

```json
{
  "bbox": [-118.8, 33.9, -117.8, 34.4],
  "collection": "sentinel-2-l2a",
  "datetime": "2025-01-01/2025-02-28",
  "limit": 50
}
```

*The search results are returning recent 2026 items instead of 2025 wildfire dates. Let me use the dedicated tool that creates a collection from MPC data directly, which should handle the filtering and ingestion together.*

*Starting: **Create collection & ingest into geocatalog** (4/5)*

*Now I have the right tool. Let me create the collection and ingest Sentinel-2 L2A items for the 2025 California wildfire area. The major fires (Palisades, Eaton, Kenneth, Hurst) were in the Los Angeles area. I'll use a bounding box covering the affected zone and a date range spanning January–February 2025.*

Ran `create_and_ingest_personal_collection_from_mpc`

*Completed with input:*

```json
{
  "bbox": "-118.8,33.9,-117.8,34.4",
  "datetime_range": "2025-01-01/2025-02-28",
  "geocatalog_url": "https://example.id.region.geocatalog.spatio.azure.com",
  "max_items": 50,
  "source_collection_id": "sentinel-2-l2a",
  "stac_api_url": "https://planetarycomputer.microsoft.com/api/stac/v1",
  "target_collection_name": "california-wildfires-2025-sentinel2-l2a"
}
```

*Workflow steps completed:*

- *Step 1: Fetched sentinel-2-l2a collection from STAC API — SUCCESS*
- *Step 2: Removed thumbnail from collection JSON — SUCCESS*
- *Step 3: Created STAC collection in GeoCatalog — SUCCESS*
  - *Collection ID: california-wildfires-2025-sentinel2-l2a, HTTP 202, ready after 2s*
- *Step 4: Added thumbnail to collection — SUCCESS*
- *Step 5: Created ingestion source with SAS token — SUCCESS*
  - *Ingestion source ID: ea399c95-a958-4acc-af5e-61b94f9cc254*
- *Step 6: Searched and ingested STAC items — SUCCESS*
  - *Total found: 50, Ingested: 50, Failed: 0*

*The collection was created and items are being ingested. 35 of 50 succeeded so far, 15 still running, 0 failed. Let me check the remaining operations.*

Ran `check_multiple_operations`

*Completed with input:*

```json
{
  "geocatalog_url": "https://example.id.region.geocatalog.spatio.azure.com",
  "operation_ids": ["dc74fdf5-...", "cd376b46-...", "... (15 remaining operation IDs)"]
}
```

*Result: All 15 remaining operations succeeded. Total: 50/50 succeeded, 0 failed.*

*Starting: **Configure render options & mosaics** (5/5)*

*All 50 items have been successfully ingested. Now let me configure render options and mosaic definitions to make the collection viewable on the map.*

Ran `configure_personal_collection_render_options`

*Completed with input:*

```json
{
  "collection_id": "california-wildfires-2025-sentinel2-l2a",
  "geocatalog_url": "https://example.id.region.geocatalog.spatio.azure.com",
  "pc_collection_id": "sentinel-2-l2a"
}
```

*Result: 8 render options configured successfully:*

1. *Natural color (natural-color)*
2. *Natural color pre-Feb 2022 (natural-color-pre-feb-2022)*
3. *Color infrared (color-infrared)*
4. *Short wave infrared (short-wave-infrared)*
5. *Agriculture (agriculture)*
6. *Normalized Difference Veg. Index / NDVI (normalized-difference-veg-inde)*
7. *Moisture Index / NDWI (moisture-index-ndwi)*
8. *Atmospheric penetration (atmospheric-penetration)*

*Now let me configure the mosaic definitions so the tiles can be served.*

Ran `configure_collection_mosaic_definitions`

*Completed with input:*

```json
{
  "collection_id": "california-wildfires-2025-sentinel2-l2a",
  "geocatalog_url": "https://example.id.region.geocatalog.spatio.azure.com"
}
```

*Result: 1 mosaic definition configured: "Most recent available" (mos1)*

*Completed: **Configure render options & mosaics** (5/5)*

---

*Done! Here's a summary of what was set up:*

**Collection created:** `california-wildfires-2025-sentinel2-l2a`

**GeoCatalog:** `https://example.id.region.geocatalog.spatio.azure.com`

**Items ingested:** 50 Sentinel-2 Level-2A scenes — all 50 succeeded

- **Date range:** January 10 – February 26, 2025
- **Area:** Los Angeles wildfire zone (bbox: -118.8, 33.9 to -117.8, 34.4), covering the Palisades, Eaton, Kenneth, and Hurst fire areas
- **Tiles covered:** T11SLT, T11SLU, T11SMT, T11SMU

**Render options configured (8):**

- Natural color, Color infrared, Short wave infrared, Agriculture, NDVI, Moisture Index (NDWI), Atmospheric penetration, and Natural color (pre-Feb 2022)

**Mosaic definition:** "Most recent available" configured for tile serving.

*The collection is live and ready to explore in your GeoCatalog. The Short wave infrared and NDVI render options are particularly useful for visualizing fire burn scars and vegetation damage.*

## Reference

### Documentation

Visit [Microsoft Planetary Computer Pro MS Learn](https://learn.microsoft.com/en-us/azure/planetary-computer/) for information on the Microsoft Planetary Computer Pro platform.

### Security

As with all new technology standards, consider doing a security review to ensure any systems that integrate with MCP servers follow all regulations and standards your system is expected to adhere to.

### Data Collection

The software may collect information about you and your use of the software and send it to Microsoft. Microsoft may use this information to provide services and improve our products and services. You may turn off the telemetry by following the instructions [here](https://code.visualstudio.com/docs/configure/telemetry#_disable-telemetry-reporting).
