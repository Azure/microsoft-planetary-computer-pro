// =============================================================================
// ArcGIS Publishing Automation — Infrastructure
// =============================================================================
// Deploys an Azure Function App with a User-Assigned Managed Identity
// configured with GeoCatalog Reader access. The Function runs a timer-triggered
// pipeline that discovers new imagery from MPC Pro and publishes it to
// ArcGIS Enterprise via the ArcGIS API for Python.
//
// Usage:
//   az deployment group create \
//     --resource-group <rg> \
//     --template-file main.bicep \
//     --parameters deploymentName=<name> \
//                  geoCatalogEndpoint=<url> \
//                  geoCatalogName=<name> \
//                  geoCatalogResourceGroup=<rg> \
//                  arcgisPortalUrl=<url>
// =============================================================================

@minLength(1)
@maxLength(64)
@description('Name for this deployment, used to generate unique resource names.')
param deploymentName string

@minLength(1)
@description('Azure region for all resources.')
param location string = resourceGroup().location

@description('The type of function plan to use. Flex Consumption (FC1) is recommended.')
@allowed(['flex', 'consumption'])
param functionPlanType string = 'flex'

// GeoCatalog parameters
@description('MPC Pro GeoCatalog endpoint URL.')
param geoCatalogEndpoint string

@description('Name of the GeoCatalog resource (for role assignment scope).')
param geoCatalogName string

@description('Resource group containing the GeoCatalog (for role assignment scope).')
param geoCatalogResourceGroup string

@description('Subscription ID containing the GeoCatalog. Defaults to current subscription.')
param geoCatalogSubscriptionId string = subscription().subscriptionId

// ArcGIS Enterprise parameters
@description('ArcGIS Enterprise portal URL.')
param arcgisPortalUrl string

@description('ArcGIS Image Server URL.')
param arcgisImageServerUrl string = ''

@description('Pipeline schedule (NCRONTAB expression).')
param pipelineSchedule string = '0 0 */6 * * *'

// Optional overrides
param managedIdentityName string = ''
param functionPlanName string = ''
param functionAppName string = ''
param storageAccountName string = ''
param logAnalyticsName string = ''
param applicationInsightsName string = ''

@minValue(40)
@maxValue(1000)
param maximumInstanceCount int = 100

@allowed([2048, 4096])
param instanceMemoryMB int = 2048

// Generate unique names
var nameUnique = toLower(uniqueString(resourceGroup().id, deploymentName, location))
var appName = !empty(functionAppName) ? functionAppName : '${nameUnique}pub'
var deploymentStorageContainerName = 'app-package-${appName}'
var tags = {
  'publishing-automation': deploymentName
}

// ---- Managed Identity ----
module identity 'identity/managedidentity.bicep' = {
  name: 'identity'
  params: {
    identityName: !empty(managedIdentityName) ? managedIdentityName : '${nameUnique}-id'
    location: location
    tags: tags
  }
}

// ---- Monitoring ----
module monitoring 'monitor/monitoring.bicep' = {
  name: 'monitoring'
  params: {
    location: location
    tags: tags
    logAnalyticsName: !empty(logAnalyticsName) ? logAnalyticsName : '${nameUnique}-logs'
    applicationInsightsName: !empty(applicationInsightsName)
      ? applicationInsightsName
      : '${nameUnique}-ai'
  }
}

// ---- Storage ----
module storage 'storage/storageaccount.bicep' = {
  name: 'storage'
  params: {
    name: !empty(storageAccountName) ? storageAccountName : nameUnique
    allowSharedKeyAccess: functionPlanType != 'flex'
    location: location
    tags: tags
    containers: [
      { name: deploymentStorageContainerName }
      { name: 'config' }
    ]
  }
}

// ---- Function App ----
module functionApp 'host/function.bicep' = {
  name: 'functionapp'
  params: {
    location: location
    tags: tags
    planName: !empty(functionPlanName) ? functionPlanName : '${nameUnique}-plan'
    appName: appName
    planType: functionPlanType
    managedIdentityName: identity.outputs.name
    applicationInsightsName: monitoring.outputs.applicationInsightsName
    storageAccountName: storage.outputs.name
    geoCatalogEndpoint: geoCatalogEndpoint
    arcgisPortalUrl: arcgisPortalUrl
    arcgisImageServerUrl: arcgisImageServerUrl
    pipelineSchedule: pipelineSchedule
    maximumInstanceCount: maximumInstanceCount
    instanceMemoryMB: instanceMemoryMB
  }
}

// ---- Role Assignments ----
var roles = loadJsonContent('roles.json')

// Storage permissions for the Function App's managed identity
module storagePermissions 'permissions/storageaccountpermissions.bicep' = {
  name: 'storagePermissions'
  params: {
    principalId: identity.outputs.principalId
    storageAccountName: storage.outputs.name
    roleIds: [
      roles.storageBlobDataContributorRole
      roles.storageQueueDataContributorRole
      roles.storageTableDataContributorRole
    ]
  }
}

// GeoCatalog Reader role for the Function App's managed identity
// This allows the Function to query the STAC API on the GeoCatalog.
// Note: Cross-subscription role assignments cannot be deployed via Bicep
// from a resource-group-scoped deployment. When the GeoCatalog is in a
// different subscription, assign the role via Azure CLI after deployment.
var isSameSubscription = geoCatalogSubscriptionId == subscription().subscriptionId
var geoCatalogResourceId = isSameSubscription
  ? resourceId(
      geoCatalogResourceGroup,
      'Microsoft.Orbital/geoCatalogs',
      geoCatalogName
    )
  : resourceId(
      geoCatalogSubscriptionId,
      geoCatalogResourceGroup,
      'Microsoft.Orbital/geoCatalogs',
      geoCatalogName
    )

module geoCatalogPermissions 'permissions/roleassignments.bicep' = if (isSameSubscription) {
  name: 'geoCatalogPermissions'
  params: {
    principalId: identity.outputs.principalId
    geoCatalogResourceId: geoCatalogResourceId
    roleIds: [
      roles.geoCatalogReaderRole
    ]
  }
}

// ---- Outputs ----
output functionAppName string = functionApp.outputs.name
output functionAppHostName string = functionApp.outputs.defaultHostName
output managedIdentityName string = identity.outputs.name
output managedIdentityPrincipalId string = identity.outputs.principalId
output storageAccountName string = storage.outputs.name
