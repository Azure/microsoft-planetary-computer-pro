#!/bin/bash
# =============================================================================
# Deploy ArcGIS Publishing Automation — Azure Function App
# =============================================================================
# Deploys the Bicep infrastructure and publishes the Function App code.
#
# Prerequisites:
#   - Azure CLI authenticated (az login)
#   - Azure Functions Core Tools installed (func)
#   - user_params.txt configured in parent directory
#
# Usage:
#   ./deploy.sh
# =============================================================================

set -e

script_dir=$(dirname "$0")

# Check prerequisites
for cmd in az func jq; do
    if ! command -v "$cmd" &> /dev/null; then
        echo "ERROR: '$cmd' is required but not installed."
        exit 1
    fi
done

# Load parameters
source "$script_dir/user_params.txt"

# Validate required parameters
if [[ -z $resource_group || -z $deployment_name || -z $location || \
      -z $geocatalog_endpoint || -z $geocatalog_name || \
      -z $geocatalog_resource_group || -z $arcgis_portal_url ]]; then
    echo "ERROR: Missing required parameters. Please check $script_dir/user_params.txt"
    echo "Required: resource_group, deployment_name, location, geocatalog_endpoint,"
    echo "          geocatalog_name, geocatalog_resource_group, arcgis_portal_url"
    exit 1
fi

# Set defaults
app_plan=${app_plan:-"flex"}
pipeline_schedule=${pipeline_schedule:-"0 0 */6 * * *"}

# Create the resource group
echo "Creating resource group $resource_group at $location..."
az group create --name "$resource_group" --location "$location" > /dev/null

# Deploy infrastructure
echo "Deploying publishing automation infrastructure..."
deployment=$(az deployment group create \
    --resource-group "$resource_group" \
    --template-file "$script_dir/../bicep/main.bicep" \
    --parameters \
        deploymentName="$deployment_name" \
        location="$location" \
        functionPlanType="$app_plan" \
        geoCatalogEndpoint="$geocatalog_endpoint" \
        geoCatalogName="$geocatalog_name" \
        geoCatalogResourceGroup="$geocatalog_resource_group" \
        geoCatalogSubscriptionId="${geocatalog_subscription_id:-$(az account show --query id -o tsv)}" \
        arcgisPortalUrl="$arcgis_portal_url" \
        arcgisImageServerUrl="${arcgis_image_server_url:-}" \
        pipelineSchedule="$pipeline_schedule")

function_app_name=$(echo "$deployment" | jq -r '.properties.outputs.functionAppName.value')
managed_identity=$(echo "$deployment" | jq -r '.properties.outputs.managedIdentityName.value')
storage_account=$(echo "$deployment" | jq -r '.properties.outputs.storageAccountName.value')

echo "Infrastructure deployed:"
echo "  Function App:      $function_app_name"
echo "  Managed Identity:  $managed_identity"
echo "  Storage Account:   $storage_account"

# Cross-subscription GeoCatalog role assignment (if needed)
current_sub=$(az account show --query id -o tsv)
geocatalog_sub="${geocatalog_subscription_id:-$current_sub}"
if [[ "$geocatalog_sub" != "$current_sub" ]]; then
    echo ""
    echo "Assigning GeoCatalog Reader role (cross-subscription)..."
    principal_id=$(echo "$deployment" | jq -r '.properties.outputs.managedIdentityPrincipalId.value')
    geocatalog_resource_id="/subscriptions/$geocatalog_sub/resourceGroups/$geocatalog_resource_group/providers/Microsoft.Orbital/geoCatalogs/$geocatalog_name"
    # GeoCatalog Reader role ID from roles.json
    geocatalog_reader_role=$(jq -r '.geoCatalogReaderRole' "$script_dir/../bicep/roles.json")
    az role assignment create \
        --assignee-object-id "$principal_id" \
        --assignee-principal-type ServicePrincipal \
        --role "$geocatalog_reader_role" \
        --scope "$geocatalog_resource_id" > /dev/null
    echo "  GeoCatalog Reader role assigned to $managed_identity"
fi

# Deploy Function App code
echo ""
echo "Deploying Function App code..."
cd "$script_dir/../azure-function"

# Copy the shared src module into the function app directory for deployment
cp -r "$script_dir/../../src" ./src

func azure functionapp publish "$function_app_name"

# Clean up copied source
rm -rf ./src

echo ""
echo -e "\033[1;32mDeployment completed successfully!\033[0m"
echo ""
echo "Next steps:"
echo "  1. Configure ArcGIS Enterprise credentials in the Function App settings:"
echo "     az functionapp config appsettings set --name $function_app_name \\"
echo "       --resource-group $resource_group \\"
echo "       --settings ARCGIS_USERNAME=<user> ARCGIS_PASSWORD=<pass>"
echo ""
echo "  2. Configure STAC query and image collection settings:"
echo "     az functionapp config appsettings set --name $function_app_name \\"
echo "       --resource-group $resource_group \\"
echo "       --settings STAC_COLLECTIONS=sentinel-2-l2a \\"
echo "         IMAGE_COLLECTION_NAME=sentinel2_imagery \\"
echo "         CLOUD_STORE_NAME=mpc_imagery_store \\"
echo "         CLOUD_STORE_ACCOUNT=<storage_account> \\"
echo "         CLOUD_STORE_CONTAINER=<container>"
echo ""
echo "  3. Or upload a config.yaml to the 'config' blob container and set:"
echo "     CONFIG_YAML_PATH=/config/config.yaml"
