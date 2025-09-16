## Databricks Notebooks: Microsoft Planetary Computer Pro Access

These notebooks illustrate end‑to‑end patterns for discovering, ingesting, and analyzing raster data from the Microsoft Planetary Computer Pro (MPC Pro) inside an Azure Databricks workspace using a User Assigned Managed Identity (UAMI). They show how to:

- Authenticate with the GeoCatalog service via `ManagedIdentityCredential`
- Enumerate STAC Items for a collection (Sentinel‑2 Level‑2A in the examples)
- Normalize STAC JSON into strongly typed Spark DataFrames / Delta tables
- Request short‑lived SAS tokens for secured collection assets
- Open Cloud Optimized GeoTIFF (COG) assets directly with `rasterio`
- Compute descriptive statistics locally and in a distributed fashion (RDD)
- Produce simple visualizations (histogram) for exploratory data analysis

> The examples intentionally focus on clarity over exhaustiveness so you can adapt them quickly to other collections and downstream analytics.

### Notebook Index (Recommended Order)

| Order | Notebook | Purpose | Key Concepts |
|-------|----------|---------|--------------|
| 1 | `RT Sentinel2 Demo.ipynb` | Enumerate Sentinel‑2 L2A STAC Items and materialize them into a Delta table. | STAC Item retrieval, schema definition, Spark DataFrame creation, Delta write |
| 2 | `RT rasterio Demo.ipynb` | Fetch a SAS token, read a single visual asset, compute basic stats and plot a histogram. | Managed identity auth, SAS token endpoint, `rasterio` read, NumPy stats, Matplotlib |
| 3 | `RT rasterio RDD Demo.ipynb` | Distribute per‑item raster statistics computation across many assets using Spark RDD. | Broadcast SAS token, RDD map, resilient error handling, structured results DataFrame |

### Detailed Summaries

#### 1. RT Sentinel2 Demo
Retrieves STAC Items for the `sentinel-2-l2a` collection via the GeoCatalog STAC endpoint using a Bearer token acquired through `ManagedIdentityCredential`. It:
- Calls `.../stac/collections/{collection_id}/items` with preview API version.
- Normalizes nested STAC JSON into a rich Spark schema (assets, bands, properties, geometry, links, providers).
- Applies a helper to coerce numeric band metadata (nodata / scale / offset) to floats for consistent typing.
- Writes the resulting DataFrame as a managed Delta table: `rt_demo.default.sentinel2` (overwrite mode).

Use this notebook first to establish the canonical Item metadata store you will query in later steps.

#### 2. RT rasterio Demo
Demonstrates point access & inspection of a single raster asset:
- Acquires a GeoCatalog access token via managed identity and requests a SAS token for the `sentinel-2-l2a` collection (`/sas/token/{collection_id}`).
- Queries the previously created Delta table for a specific Item ID and extracts the `assets.visual.href` (COG URL base).
- Appends the SAS token query string and opens the asset with `rasterio`.
- Computes min / max / mean / std statistics for band 1 using NumPy.
- Filters valid pixel values and renders a histogram with Matplotlib for a quick quality & distribution check.

This notebook is ideal for validating connectivity, permissions, and data integrity for an individual scene.

#### 3. RT rasterio RDD Demo
Extends the previous pattern to many Items simultaneously:
- Broadcasts the SAS token to executors to avoid redundant retrieval.
- Selects Item IDs and visual asset HREFs from the Delta table into an RDD.
- Defines `compute_stats_rdd` which opens each asset, computes statistics (min / max / mean / std) or captures an error string if reading fails.
- Maps results into a typed Spark DataFrame (schema with numeric columns + error).
- Displays aggregated results for comparison, surfacing problematic assets via the `error` field.

Use this for scalable exploratory statistics or lightweight data quality checks prior to heavier analytics or tiling workflows.

### Prerequisites

- Azure Databricks workspace with:
	- A User Assigned Managed Identity (UAMI) attached to the compute (job or cluster) and granted appropriate access to the MPC Pro GeoCatalog resource.
- Python environment containing: `azure-identity`, `requests`, `rasterio`, `matplotlib`, `numpy`, and Spark (provided by Databricks runtime) plus any system GDAL dependencies (bundled in most ML/Geo runtimes; if not, use a cluster init script or `%pip install rasterio`).
- Network access / firewall rules allowing outbound calls to the GeoCatalog service endpoints.

### Minimal Library Installation Cell (If Needed)

Add this as the first cell (only if the runtime image does not already include these):

```python
# Databricks %pip magic recommended in notebooks
%pip install azure-identity requests rasterio matplotlib
```

After running a `%pip` cell, restart the Python kernel in Databricks (it will prompt you) before proceeding to avoid import conflicts.

### Authentication Flow

1. `ManagedIdentityCredential()` obtains an access token for resource ID: `https://geocatalog.spatio.azure.com` (MPC Pro GeoCatalog scope).
2. Bearer token used in `Authorization` header for:
	 - STAC Items listing endpoint
	 - SAS token retrieval endpoint
3. SAS token appended to asset HREFs when reading COGs with `rasterio`.

### Customization Points

- `geocatalog_url`: Replace with your environment / region endpoint.
- `collection_id`: Switch to other available collections (e.g., Landsat, custom ingested data) once permissions are granted.
- Item selection filters: Add spatial / temporal filters at STAC query time or filter the Delta table (e.g., cloud cover thresholds).
- Statistics logic: Extend to additional bands, compute percentiles, histograms per band, or write summary tables.

### Troubleshooting

| Symptom | Likely Cause | Mitigation |
|---------|--------------|-----------|
| 401 / 403 responses | Managed identity lacks role or scope | Assign required MPC Pro roles / re-attach identity to cluster |
| `rasterio` cannot open asset | Missing SAS token or expired token | Re-run SAS token retrieval; ensure query string appended |
| Empty Delta table | STAC endpoint returned zero features (filtering) | Inspect raw JSON; adjust collection ID or API version |
| Slow distributed stats | Large assets & serialization overhead | Limit to subset, increase cluster size, cache SAS token (already broadcast) |

### Extending the Pattern

- Batch ingestion: Schedule the Sentinel‑2 listing notebook to refresh Items incrementally (add partitioning on acquisition date).
- Advanced analytics: Join Item stats to external observation datasets or feed into ML feature engineering pipelines.
- Visualization: Feed Delta table into Databricks SQL / dashboards or create tile services downstream.

### Learn More

- MPC Pro Getting Started: (See repository `docs/learn/get-started-planetary-computer.md`)
- STAC Specification: https://stacspec.org
- Azure Identity (Managed Identity): https://learn.microsoft.com/azure/active-directory/managed-identities-azure-resources/overview
- Rasterio: https://rasterio.readthedocs.io

> For comprehensive service concepts, API surfaces, and ingestion patterns, consult the `docs/learn` directory in this repository.

---
If you have suggestions or encounter issues, please open an issue or PR referencing the notebook name and a concise problem description.

