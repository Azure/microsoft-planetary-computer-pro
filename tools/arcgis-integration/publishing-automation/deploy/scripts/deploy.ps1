# =============================================================================
# Deploy ArcGIS Publishing Automation — Azure Function App (PowerShell)
# =============================================================================
# Deploys the Bicep infrastructure and publishes the Function App code.
#
# Prerequisites:
#   - Azure CLI authenticated (az login)
#   - Azure Functions Core Tools installed (func)
#
# Usage:
#   .\deploy.ps1 -ResourceGroup <rg> -DeploymentName <name> ...
# =============================================================================

param(
    [Parameter(Mandatory=$true)]
    [string]$ResourceGroup,

    [Parameter(Mandatory=$true)]
    [string]$DeploymentName,

    [Parameter(Mandatory=$true)]
    [string]$Location,

    [Parameter(Mandatory=$true)]
    [string]$GeoCatalogEndpoint,

    [Parameter(Mandatory=$true)]
    [string]$GeoCatalogName,

    [Parameter(Mandatory=$true)]
    [string]$GeoCatalogResourceGroup,

    [Parameter(Mandatory=$true)]
    [string]$ArcGISPortalUrl,

    [string]$ArcGISImageServerUrl = "",
    [string]$GeoCatalogSubscriptionId = "",
    [string]$AppPlan = "flex",
    [string]$PipelineSchedule = "0 0 */6 * * *"
)

$ErrorActionPreference = "Stop"
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path

# Resolve GeoCatalog subscription ID
if (-not $GeoCatalogSubscriptionId) {
    $GeoCatalogSubscriptionId = (az account show --query id -o tsv)
}

# Create the resource group
Write-Host "Creating resource group $ResourceGroup at $Location..." -ForegroundColor Cyan
az group create --name $ResourceGroup --location $Location | Out-Null

# Deploy infrastructure
Write-Host "Deploying publishing automation infrastructure..." -ForegroundColor Cyan
$deployment = az deployment group create `
    --resource-group $ResourceGroup `
    --template-file "$scriptDir\..\bicep\main.bicep" `
    --parameters `
        deploymentName=$DeploymentName `
        location=$Location `
        functionPlanType=$AppPlan `
        geoCatalogEndpoint=$GeoCatalogEndpoint `
        geoCatalogName=$GeoCatalogName `
        geoCatalogResourceGroup=$GeoCatalogResourceGroup `
        geoCatalogSubscriptionId=$GeoCatalogSubscriptionId `
        arcgisPortalUrl=$ArcGISPortalUrl `
        arcgisImageServerUrl=$ArcGISImageServerUrl `
        pipelineSchedule=$PipelineSchedule | ConvertFrom-Json

$functionAppName = $deployment.properties.outputs.functionAppName.value
$managedIdentity = $deployment.properties.outputs.managedIdentityName.value
$managedIdentityPrincipalId = $deployment.properties.outputs.managedIdentityPrincipalId.value
$storageAccount = $deployment.properties.outputs.storageAccountName.value

Write-Host "Infrastructure deployed:" -ForegroundColor Green
Write-Host "  Function App:      $functionAppName"
Write-Host "  Managed Identity:  $managedIdentity"
Write-Host "  Storage Account:   $storageAccount"

# Cross-subscription GeoCatalog role assignment (if needed)
$currentSub = (az account show --query id -o tsv)
if ($GeoCatalogSubscriptionId -ne $currentSub) {
    Write-Host "`nAssigning GeoCatalog Reader role (cross-subscription)..." -ForegroundColor Cyan
    $geocatalogResourceId = "/subscriptions/$GeoCatalogSubscriptionId/resourceGroups/$GeoCatalogResourceGroup/providers/Microsoft.Orbital/geoCatalogs/$GeoCatalogName"
    $rolesJson = Get-Content "$scriptDir\..\bicep\roles.json" | ConvertFrom-Json
    $geocatalogReaderRole = $rolesJson.geoCatalogReaderRole
    az role assignment create `
        --assignee-object-id $managedIdentityPrincipalId `
        --assignee-principal-type ServicePrincipal `
        --role $geocatalogReaderRole `
        --scope $geocatalogResourceId | Out-Null
    Write-Host "  GeoCatalog Reader role assigned to $managedIdentity"
}

# Deploy Function App code
Write-Host "`nDeploying Function App code..." -ForegroundColor Cyan
Push-Location "$scriptDir\..\azure-function"

# Copy the shared src module for deployment
Copy-Item -Path "$scriptDir\..\..\src" -Destination ".\src" -Recurse -Force

func azure functionapp publish $functionAppName

# Clean up
Remove-Item -Path ".\src" -Recurse -Force

Pop-Location

Write-Host "`nDeployment completed successfully!" -ForegroundColor Green
Write-Host "`nNext steps:" -ForegroundColor Yellow
Write-Host "  1. Configure ArcGIS Enterprise credentials in Function App settings"
Write-Host "  2. Configure STAC query and image collection settings"
Write-Host "  3. See the Azure Functions deployment guide for details"
