@description('Name for the Function App.')
param appName string

@description('Name for the App Service Plan.')
param planName string

@description('Azure region for all resources.')
param location string = resourceGroup().location

@description('The type of function plan to use. Flex Consumption (FC1) is recommended.')
@allowed(['flex', 'consumption'])
param planType string = 'flex'

@description('Name of the user-assigned managed identity.')
param managedIdentityName string

@description('Name of the Application Insights instance.')
param applicationInsightsName string

@description('Name of the storage account for Functions runtime.')
param storageAccountName string

@description('GeoCatalog endpoint URL.')
param geoCatalogEndpoint string

@description('ArcGIS Enterprise portal URL.')
param arcgisPortalUrl string

@description('ArcGIS Image Server URL.')
param arcgisImageServerUrl string = ''

@description('Pipeline schedule (NCRONTAB expression).')
param pipelineSchedule string = '0 0 */6 * * *'

@description('Tags to apply to all resources.')
param tags object = {}

param functionAppRuntime string = 'python'
param functionAppRuntimeVersion string = '3.11'

@description('Maximum instance count for Flex plan.')
@minValue(40)
@maxValue(1000)
param maximumInstanceCount int = 100

@description('Instance memory for Flex plan.')
@allowed([2048, 4096])
param instanceMemoryMB int = 2048

// Container name for deployment packages
var deploymentStorageContainerName = 'app-package-${appName}'

resource managedIdentity 'Microsoft.ManagedIdentity/userAssignedIdentities@2023-07-31-preview' existing = {
  name: managedIdentityName
}

resource storage 'Microsoft.Storage/storageAccounts@2023-05-01' existing = {
  name: storageAccountName
}

resource appInsights 'Microsoft.Insights/components@2020-02-02' existing = {
  name: applicationInsightsName
}

var consumptionSku = {
  tier: 'Dynamic'
  name: 'Y1'
}

var flexSku = {
  tier: 'FlexConsumption'
  name: 'FC1'
}

resource functionPlan 'Microsoft.Web/serverfarms@2023-12-01' = {
  name: planName
  location: location
  tags: tags
  kind: 'functionapp'
  sku: planType == 'flex' ? flexSku : consumptionSku
  properties: {
    reserved: true
  }
}

var storageConnectionString = 'DefaultEndpointsProtocol=https;AccountName=${storage.name};EndpointSuffix=${environment().suffixes.storage};AccountKey=${storage.listKeys().keys[0].value}'

var consumptionAppSettings = [
  {
    name: 'AzureWebJobsStorage'
    value: storageConnectionString
  }
  {
    name: 'WEBSITE_CONTENTAZUREFILECONNECTIONSTRING'
    value: storageConnectionString
  }
  {
    name: 'WEBSITE_CONTENTSHARE'
    value: toLower(appName)
  }
  {
    name: 'FUNCTIONS_EXTENSION_VERSION'
    value: '~4'
  }
  {
    name: 'FUNCTIONS_WORKER_RUNTIME'
    value: functionAppRuntime
  }
]

var flexAppSettings = [
  {
    name: 'AzureWebJobsStorage__accountName'
    value: storage.name
  }
  {
    name: 'AzureWebJobsStorage__credential'
    value: 'managedidentity'
  }
  {
    name: 'AzureWebJobsStorage__clientId'
    value: managedIdentity.properties.clientId
  }
]

var commonAppSettings = [
  {
    name: 'APPLICATIONINSIGHTS_CONNECTION_STRING'
    value: appInsights.properties.ConnectionString
  }
  {
    name: 'AZURE_CLIENT_ID'
    value: managedIdentity.properties.clientId
  }
  {
    name: 'AZURE_TENANT_ID'
    value: managedIdentity.properties.tenantId
  }
  // Publishing automation settings
  {
    name: 'GEOCATALOG_ENDPOINT'
    value: geoCatalogEndpoint
  }
  {
    name: 'ARCGIS_PORTAL_URL'
    value: arcgisPortalUrl
  }
  {
    name: 'ARCGIS_IMAGE_SERVER_URL'
    value: arcgisImageServerUrl
  }
  {
    name: 'PIPELINE_SCHEDULE'
    value: pipelineSchedule
  }
]

resource functionApp 'Microsoft.Web/sites@2023-12-01' = {
  name: appName
  location: location
  tags: tags
  kind: 'functionapp,linux'
  identity: {
    type: 'UserAssigned'
    userAssignedIdentities: {
      '${managedIdentity.id}': {}
    }
  }
  properties: {
    serverFarmId: functionPlan.id
    reserved: true
    containerSize: planType == 'consumption' ? instanceMemoryMB : null
    siteConfig: {
      linuxFxVersion: planType != 'flex' ? '${functionAppRuntime}|${functionAppRuntimeVersion}' : null
      appSettings: union(
        commonAppSettings,
        planType == 'flex' ? flexAppSettings : consumptionAppSettings
      )
      functionAppScaleLimit: planType == 'consumption' ? maximumInstanceCount : null
    }
    functionAppConfig: planType == 'flex'
      ? {
          deployment: {
            storage: {
              type: 'blobContainer'
              value: '${storage.properties.primaryEndpoints.blob}${deploymentStorageContainerName}'
              authentication: {
                type: 'UserAssignedIdentity'
                userAssignedIdentityResourceId: managedIdentity.id
              }
            }
          }
          scaleAndConcurrency: {
            maximumInstanceCount: maximumInstanceCount
            instanceMemoryMB: instanceMemoryMB
          }
          runtime: {
            name: functionAppRuntime
            version: functionAppRuntimeVersion
          }
        }
      : null
  }
}

resource logSettings 'Microsoft.Insights/diagnosticSettings@2021-05-01-preview' = {
  name: 'logs'
  scope: functionApp
  properties: {
    workspaceId: appInsights.properties.WorkspaceResourceId
    logs: [
      {
        category: 'FunctionAppLogs'
        enabled: true
      }
    ]
  }
}

output name string = functionApp.name
output defaultHostName string = functionApp.properties.defaultHostName
