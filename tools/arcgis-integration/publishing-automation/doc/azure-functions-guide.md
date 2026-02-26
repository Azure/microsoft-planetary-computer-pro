# ArcGIS Publishing for MPC Pro: Azure Functions Deployment Guide

Deploy the publishing automation pipeline as a timer-triggered Azure Function that automatically discovers new imagery from MPC Pro and publishes it to ArcGIS Enterprise.

## Prerequisites

- Azure CLI installed and authenticated (`az login`)
- Azure Functions Core Tools installed (`func`)
- An existing MPC Pro GeoCatalog with imagery collections
- An existing ArcGIS Enterprise deployment with Image Server
- [Planetary Computer Pro data stores](https://enterprise.arcgis.com/en/portal/latest/use/add-data-store-item.htm) registered in ArcGIS Enterprise for each GeoCatalog collection
- Owner or User Access Administrator role on the GeoCatalog resource (for role assignment)
- **App Service quota** in your target region (see note below)

> **Quota note:** The default Flex Consumption plan uses **FC1 VMs**. If you switch to the classic Consumption plan, it uses **Y1 VMs**. Some subscriptions have zero quota for these SKUs by default, which will cause deployment to fail with a `SubscriptionIsOverQuotaForSku` error. You can request quota through the self-service **App Service quota request** experience in the Azure Portal under **Subscriptions → Usage + quotas → App Service**. For details, see [Announcing the Public Preview of the New App Service Quota Self-Service Experience](https://techcommunity.microsoft.com/blog/appsonazureblog/announcing-the-public-preview-of-the-new-app-service-quota-self-service-experien/4450415).

## Step 1: Configure Parameters

Edit the deployment parameters file:

```bash
cd deploy/scripts
cp user_params.txt my_params.txt
# Edit my_params.txt with your values
```

Required parameters:

| Parameter | Description | Example |
|---|---|---|
| `resource_group` | Azure resource group for the Function App | `rg-pub-automation` |
| `deployment_name` | Unique name for this deployment | `pub-auto-prod` |
| `location` | Azure region | `eastus` |
| `geocatalog_endpoint` | MPC Pro GeoCatalog URL | `https://my-gc.geocatalog.spatio.azure.com` |
| `geocatalog_name` | GeoCatalog resource name | `my-geocatalog` |
| `geocatalog_resource_group` | Resource group of the GeoCatalog | `rg-mpc-pro` |
| `arcgis_portal_url` | ArcGIS Enterprise portal URL | `https://portal.domain.com/portal` |

## Step 2: Deploy Infrastructure and Code

### Using bash:
```bash
source my_params.txt
./deploy.sh
```

### Using PowerShell:
```powershell
.\deploy.ps1 `
    -ResourceGroup "rg-pub-automation" `
    -DeploymentName "pub-auto-prod" `
    -Location "eastus" `
    -GeoCatalogEndpoint "https://my-gc.geocatalog.spatio.azure.com" `
    -GeoCatalogName "my-geocatalog" `
    -GeoCatalogResourceGroup "rg-mpc-pro" `
    -ArcGISPortalUrl "https://portal.domain.com/portal"
```

This will:
1. Create a resource group
2. Deploy the Bicep templates (Function App, Managed Identity, Storage, Monitoring, Role Assignments)
3. Publish the Function App code

## Step 3: Configure Application Settings

After deployment, configure the STAC query and ArcGIS Enterprise settings:

### Option A: Individual app settings

```bash
FUNCTION_APP_NAME="<from deployment output>"
RESOURCE_GROUP="rg-pub-automation"

az functionapp config appsettings set \
    --name $FUNCTION_APP_NAME \
    --resource-group $RESOURCE_GROUP \
    --settings \
        STAC_COLLECTIONS="sentinel-2-l2a" \
        STAC_BBOX="-122.5,37.5,-122.0,38.0" \
        STAC_DATETIME="2024-01-01T00:00:00Z/2024-12-31T23:59:59Z" \
        STAC_LIMIT="100" \
        IMAGE_COLLECTION_NAME="sentinel2_imagery" \
        IMAGE_COLLECTION_DESCRIPTION="Sentinel-2 L2A" \
        SOURCE_ASSET_KEY="visual" \
        ARCGIS_AUTH_METHOD="username_password" \
        ARCGIS_USERNAME="<portal_admin>" \
        CLOUD_STORE_NAME="mpc_imagery_store" \
        CLOUD_STORE_ACCOUNT="<storage_account>" \
        CLOUD_STORE_CONTAINER="<container>"

# Set password separately (sensitive)
az functionapp config appsettings set \
    --name $FUNCTION_APP_NAME \
    --resource-group $RESOURCE_GROUP \
    --settings ARCGIS_PASSWORD="<portal_password>"
```

> **Security note:** For production, store `ARCGIS_PASSWORD` in Azure Key Vault and reference it via a Key Vault reference in the app settings.

### Option B: Upload a config.yaml

Upload a full configuration file to the Function App's blob storage:

```bash
STORAGE_ACCOUNT="<from deployment output>"

az storage blob upload \
    --account-name $STORAGE_ACCOUNT \
    --container-name config \
    --name config.yaml \
    --file /path/to/your/config.yaml

az functionapp config appsettings set \
    --name $FUNCTION_APP_NAME \
    --resource-group $RESOURCE_GROUP \
    --settings CONFIG_YAML_PATH="/config/config.yaml"
```

## Step 4: Test

Trigger the function manually from the Azure Portal:

1. Go to the Function App in the Azure Portal
2. Navigate to **Functions** → **publishing_automation_timer**
3. Click **Test/Run**
4. Check the **Monitor** tab for execution logs

Or via the CLI:

```bash
az functionapp function invoke \
    --name $FUNCTION_APP_NAME \
    --resource-group $RESOURCE_GROUP \
    --function-name publishing_automation_timer
```

## Step 5: Monitor

View logs in Application Insights:

```bash
# View recent function invocations
az monitor app-insights query \
    --app <app-insights-name> \
    --analytics-query "traces | where timestamp > ago(1h) | order by timestamp desc | take 50"
```

## Troubleshooting

### Authentication errors to GeoCatalog

The Function App's managed identity needs the **GeoCatalog Reader** role. Verify:

```bash
MI_PRINCIPAL_ID="<from deployment output>"
GEOCATALOG_SCOPE="/subscriptions/<sub>/resourceGroups/<rg>/providers/Microsoft.Orbital/geoCatalogs/<name>"

az role assignment list \
    --assignee $MI_PRINCIPAL_ID \
    --scope $GEOCATALOG_SCOPE
```

### Authentication errors to ArcGIS Enterprise

Verify the portal URL and credentials in the app settings. Ensure the ArcGIS Enterprise portal is accessible from Azure (may require VPN/Private Endpoint configuration).

### No new items found

- Check the STAC query parameters (collections, bbox, datetime)
- Verify the GeoCatalog has items in the specified collection
- Check that the `SOURCE_ASSET_KEY` matches an asset available in the STAC items
