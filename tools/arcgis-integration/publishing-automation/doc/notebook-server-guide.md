# ArcGIS Notebook Server Deployment Guide

Run the publishing automation pipeline from ArcGIS Notebook Server as a scheduled notebook task.

## Prerequisites

- ArcGIS Enterprise with Notebook Server and Image Server
- MPC Pro GeoCatalog with imagery collections
- [Planetary Computer Pro data stores](https://enterprise.arcgis.com/en/portal/latest/use/add-data-store-item.htm) registered in ArcGIS Enterprise for each GeoCatalog collection
- ArcGIS Notebook Server license with scheduled task capability
- Azure credentials accessible from within Notebook Server containers (see Step 1)

## Step 1: Configure Azure Credentials for Notebooks

ArcGIS Notebook Server runs notebooks in Docker containers. The container needs access to Azure credentials so `DefaultAzureCredential` can authenticate to the MPC Pro GeoCatalog.

### Option A: IMDS Passthrough (Recommended)

If the Notebook Server VM has a system-assigned managed identity, configure Docker to allow containers to reach the Azure Instance Metadata Service (IMDS).

1. First, set up the VM's managed identity:

```bash
# From a machine with Azure CLI access
export VM_RESOURCE_GROUP="rg-notebook-server"
export VM_NAME="notebook-server-vm"
export GEOCATALOG_NAME="my-geocatalog"
export GEOCATALOG_RESOURCE_GROUP="rg-mpc-pro"

./deploy/scripts/setup-managed-identity.sh
```

2. Configure IMDS passthrough on the Notebook Server VM:

```powershell
.\deploy\scripts\configure-notebook-server.ps1 -Method IMDS
```

Follow the manual configuration steps output by the script for your Docker runtime.

### Option B: Service Principal

Create a service principal and inject its credentials as environment variables:

1. Create a service principal with GeoCatalog Reader role:

```bash
az ad sp create-for-rbac --name "notebook-geocatalog-reader" --role "GeoCatalog Reader" \
    --scopes "/subscriptions/<sub>/resourceGroups/<rg>/providers/Microsoft.Orbital/geoCatalogs/<name>"
```

2. Configure environment variables on the Notebook Server VM:

```powershell
.\deploy\scripts\configure-notebook-server.ps1 `
    -Method ServicePrincipal `
    -ClientId "<app-id>" `
    -ClientSecret "<password>" `
    -TenantId "<tenant-id>"
```

3. Restart ArcGIS Notebook Server:

```powershell
Restart-Service "ArcGIS Notebook Server"
```

## Step 2: Install Dependencies in the Notebook Runtime

Some dependencies may need to be installed in the Notebook Server's Docker container image. This can be done in the first notebook cell:

```python
!pip install azure-planetarycomputer azure-identity
```

> **Note:** The `arcgis` package should already be pre-installed in ArcGIS Notebook Server container images.

## Step 3: Upload the Notebook

1. Open the ArcGIS Enterprise portal in your browser
2. Navigate to **Notebook** in the app launcher
3. Upload `notebooks/publishing_automation.ipynb`
4. Open the notebook and edit the **Configuration** cell with your environment settings:
   - GeoCatalog endpoint
   - STAC query parameters
   - Image collection name
   - ArcGIS Enterprise credentials (or leave empty for portal-integrated auth)
   - Data store configuration

## Step 4: Test the Notebook

Run the notebook cells sequentially to verify the workflow:

1. **Configuration** — Verify settings are correct
2. **Dependencies** — Ensure all imports succeed
3. **Authenticate** — Verify both MPC Pro and ArcGIS Enterprise connections
4. **Discover** — Check that STAC items are returned
5. **Deduplicate** — Verify the image collection query works
6. **Ingest** — Add rasters (or verify dry run)
7. **Publish** — Confirm imagery layer is published/refreshed
8. **Summary** — Review the run report

## Step 5: Schedule the Notebook

1. In the ArcGIS Enterprise portal, navigate to the notebook item
2. Click **Schedule** (or go to **Notebook Manager** → **Tasks**)
3. Configure the schedule:
   - **Repeat**: Every 6 hours (or your preferred interval)
   - **Start time**: Next convenient time
   - **End time**: None (continuous)
4. Save the scheduled task

> **Note:** Scheduled notebook tasks run with the notebook owner's portal identity. Ensure the owner has the necessary permissions to create/modify image collections and imagery layers.

## Step 6: Monitor

### Check task history

In the ArcGIS Enterprise portal:
1. Go to **Notebook Manager** → **Tasks**
2. View the task history for execution status and logs

### View notebook output

Each scheduled execution saves the notebook with its output. Open the notebook to see the results of the last run, including the summary cell.

## Troubleshooting

### Azure credential errors from within notebooks

1. **Test IMDS access**:
```python
import requests
try:
    r = requests.get(
        "http://169.254.169.254/metadata/identity/oauth2/token",
        params={"api-version": "2018-02-01", "resource": "https://geocatalog.spatio.azure.com"},
        headers={"Metadata": "true"},
        timeout=5,
    )
    print(f"Status: {r.status_code}")
    print(f"Response: {r.json()}")
except Exception as e:
    print(f"IMDS not accessible: {e}")
    print("Try Service Principal method instead.")
```

2. **Test service principal**:
```python
import os
print(f"AZURE_CLIENT_ID: {'set' if os.environ.get('AZURE_CLIENT_ID') else 'not set'}")
print(f"AZURE_TENANT_ID: {'set' if os.environ.get('AZURE_TENANT_ID') else 'not set'}")
print(f"AZURE_CLIENT_SECRET: {'set' if os.environ.get('AZURE_CLIENT_SECRET') else 'not set'}")
```

### Package import errors

If `azure-planetarycomputer` is not available, install it in the notebook:
```python
!pip install azure-planetarycomputer
# Then restart the kernel
```

### Scheduled task not running

- Verify the Notebook Server service is running
- Check that the task owner has an active portal account
- View Notebook Server logs at `C:\Program Files\ArcGIS\notebookserver\logs\`
