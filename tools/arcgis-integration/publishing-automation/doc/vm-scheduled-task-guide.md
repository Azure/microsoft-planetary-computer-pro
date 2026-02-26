# VM Scheduled Task Deployment Guide

Run the publishing automation pipeline as a Windows Scheduled Task on an ArcGIS Server VM.

## Prerequisites

- ArcGIS Server VM running Windows with Python 3.9+
- ArcGIS Enterprise with Image Server configured and accessible
- MPC Pro GeoCatalog with imagery collections
- [Planetary Computer Pro data stores](https://enterprise.arcgis.com/en/portal/latest/use/add-data-store-item.htm) registered in ArcGIS Enterprise for each GeoCatalog collection
- Administrator access to the ArcGIS Server VM
- Azure CLI access (for managed identity setup)

## Step 1: Enable VM Managed Identity

The VM needs a system-assigned managed identity with **GeoCatalog Reader** role to authenticate to the MPC Pro GeoCatalog.

```bash
# Set environment variables
export VM_RESOURCE_GROUP="rg-arcgis-server"
export VM_NAME="arcgis-server-vm"
export GEOCATALOG_NAME="my-geocatalog"
export GEOCATALOG_RESOURCE_GROUP="rg-mpc-pro"

# Run the setup script
./deploy/scripts/setup-managed-identity.sh
```

This will:
1. Enable system-assigned managed identity on the VM
2. Assign the GeoCatalog Reader role on the specified GeoCatalog resource

### Verify

From the VM, test that the managed identity can acquire a token:

```python
from azure.identity import DefaultAzureCredential
credential = DefaultAzureCredential()
token = credential.get_token("https://geocatalog.spatio.azure.com/.default")
print("Token acquired successfully" if token else "Failed")
```

## Step 2: Install Dependencies

Run the install script as Administrator on the ArcGIS Server VM:

```powershell
.\deploy\scripts\install-dependencies.ps1
```

This installs `azure-planetarycomputer`, `azure-identity`, `arcgis`, and `pyyaml` into the detected ArcGIS Python environment.

If you need to specify a custom Python path:

```powershell
.\deploy\scripts\install-dependencies.ps1 -PythonPath "C:\Python311\python.exe"
```

## Step 3: Copy Pipeline Code and Configure

1. Copy the `src/` directory and `config.example.yaml` to the VM (e.g., `D:\automation\`):

```powershell
# Example: copy from a network share or download
Copy-Item -Path "\\server\share\publishing-automation\src" -Destination "D:\automation\src" -Recurse
Copy-Item -Path "\\server\share\publishing-automation\config.example.yaml" -Destination "D:\automation\config.yaml"
```

2. Edit `D:\automation\config.yaml` with your GeoCatalog endpoint, ArcGIS Enterprise URL, STAC query parameters, and data store configuration.

## Step 4: Test the Pipeline

Run a dry run to verify configuration:

```powershell
cd D:\automation
python -m src.run --config config.yaml --dry-run --verbose
```

Then a full run:

```powershell
python -m src.run --config config.yaml --verbose
```

## Step 5: Create the Scheduled Task

Run the setup script as Administrator:

```powershell
.\deploy\scripts\setup-vm-task.ps1 -ConfigPath "D:\automation\config.yaml" -IntervalHours 6
```

Options:

| Parameter | Default | Description |
|---|---|---|
| `-ConfigPath` | (required) | Path to config.yaml |
| `-IntervalHours` | 6 | Run interval in hours |
| `-TaskName` | `MPC-Publishing-Automation` | Name of the scheduled task |
| `-PythonPath` | (auto-detected) | Path to Python executable |

## Step 6: Verify

Check the task is registered:

```powershell
Get-ScheduledTask -TaskName "MPC-Publishing-Automation"
```

Run it manually to test:

```powershell
Start-ScheduledTask -TaskName "MPC-Publishing-Automation"
```

Check results:

```powershell
Get-ScheduledTask -TaskName "MPC-Publishing-Automation" | Get-ScheduledTaskInfo
```

## Troubleshooting

### Managed identity token errors

- Verify the VM has a system-assigned managed identity: `az vm show --name <vm> --resource-group <rg> --query identity`
- Verify the role assignment: `az role assignment list --assignee <principal-id> --scope <geocatalog-scope>`
- Ensure the VM can reach Azure AD endpoints (outbound HTTPS on port 443)

### ArcGIS Enterprise connection errors

- Verify the portal URL is reachable from the VM
- Test credentials manually: `GIS("https://portal/portal", "user", "pass")`
- If using Windows IWA, verify the VM's service account has portal access

### Module import errors

- Verify dependencies are installed in the correct Python environment
- Run `python -c "import azure.planetarycomputer; import arcgis; print('OK')"`
- The ArcGIS Server Python environment may need `pip` upgraded: `python -m pip install --upgrade pip`
