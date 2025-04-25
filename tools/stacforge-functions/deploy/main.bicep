@minLength(1)
@maxLength(64)
@description('Name of the the STACForge which is used to generate a short unique hash used in all resources.')
param forgeName string

@minLength(1)
@description('Primary location for all resources')
// @allowed(['australiaeast', 'eastasia', 'eastus', 'eastus2', 'northeurope', 'southcentralus', 'southeastasia', 'swedencentral', 'uksouth', 'westus2', 'eastus2euap'])
param location string = resourceGroup().location

@description('The type of function plan to use.')
@allowed(['flex', 'consumption'])
param functionPlanType string = 'flex'

param managedIdentityName string = ''
param functionPlanName string = ''
param functionAppName string = ''
param functionsStorageAccountName string = ''
param dataStorageAccountName string = ''
param logAnalyticsName string = ''
param applicationInsightsName string = ''
param monitoringRetentionInDays int = 30

@minValue(40)
@maxValue(1000)
param maximumInstanceCount int = 100

@allowed([2048,4096])
param instanceMemoryMB int = 2048

// Generate a unique name to be used in naming resources.
var nameUnique = toLower(uniqueString(resourceGroup().id, forgeName, location))
// Generate a unique function app name if one is not provided.
var appName = !empty(functionAppName) ? functionAppName : nameUnique
// Generate a unique container name that will be used for deployments.
var deploymentStorageContainerName = 'app-package-${appName}'
// tags that should be applied to all resources.
var tags = {
  // Tag all resources with the environment name.
  'stacforge-name': forgeName
}
var functionAppRuntime = 'python'
var functionAppRuntimeVersion = '3.11'

// Monitor application with Azure Monitor
module identity 'identity/managedidentity.bicep' = {
  name: 'identity'
  params: {
    identityName: !empty(managedIdentityName) ? managedIdentityName : nameUnique
    location: location
    tags: tags
  }
}

// Monitor application with Azure Monitor
module monitoring 'monitor/monitoring.bicep' = {
  name: 'monitoring'
  params: {
    location: location
    retentionInDays: monitoringRetentionInDays
    tags: tags
    logAnalyticsName: !empty(logAnalyticsName) ? logAnalyticsName : nameUnique
    applicationInsightsName: !empty(applicationInsightsName) ? applicationInsightsName : nameUnique
  }
}

// Backing storage for Azure Functions
module functionsStorage 'storage/storageaccount.bicep' = {
  name: 'functionsStorage'
  params: {
    name: !empty(functionsStorageAccountName) ? functionsStorageAccountName : nameUnique
    allowSharedKeyAccess: functionPlanType != 'flex'
    location: location
    tags: union(tags, { 'storage-role': 'functions' })
    containers: [
      {name: deploymentStorageContainerName}
    ]
  }
}

var logsTableName = '${replace(forgeName, '-', '')}logs'

// Data storage
module dataStorage 'storage/storageaccount.bicep' = {
  name: 'dataStorage'
  params: {
    name: !empty(dataStorageAccountName) ? dataStorageAccountName : '${nameUnique}data'
    location: location
    tags: union(tags, { 'storage-role': 'data' })
    containers: [
      {name: 'templates'}
      {name: 'collections'}
    ]
    tables: [
      {name: logsTableName}
    ]
  }
}

// Azure Function App
module functionApp 'host/function.bicep' = {
  name: 'functionapp'
  params: {
    location: location
    tags: tags
    planName: !empty(functionPlanName) ? functionPlanName : nameUnique
    appName: appName
    planType: functionPlanType
    managedIdentityName: identity.outputs.name
    applicationInsightsName: monitoring.outputs.applicationInsightsName
    functionsStorageAccountName: functionsStorage.outputs.name
    dataStorageAccountName: dataStorage.outputs.name
    logsTableName: logsTableName
    deploymentStorageContainerName: deploymentStorageContainerName
    functionAppRuntime: functionAppRuntime
    functionAppRuntimeVersion: functionAppRuntimeVersion
    maximumInstanceCount: maximumInstanceCount
    instanceMemoryMB: instanceMemoryMB
  }
}

var roles = loadJsonContent('roles.json')

module functionsStoragePermissions 'permissions/storageaccountpermissions.bicep' = {
  name: 'functionsStoragePermissions'
  params: {
    principalId: identity.outputs.principalId
    storageAccountName: functionsStorage.outputs.name
    roleIds: [
      roles.storageBlobDataContributorRole
      roles.storageQueueDataContributorRole
      roles.storageTableDataContributorRole
    ]
  }
}

module dataStoragePermissions 'permissions/storageaccountpermissions.bicep' = {
  name: 'dataStoragePermissions'
  params: {
    principalId: identity.outputs.principalId
    principalType: 'ServicePrincipal'
    storageAccountName: dataStorage.outputs.name
    roleIds: [
      roles.storageBlobDataContributorRole
      roles.storageTableDataContributorRole
      roles.storageBlobDelegatorRole
    ]
  }
}

module appInsightsPermissions 'permissions/appinsightspermissions.bicep' = {
  name: 'appInsightsPermissions'
  params: {
    principalId: identity.outputs.principalId
    principalType: 'ServicePrincipal'
    appInsightsName: monitoring.outputs.applicationInsightsName
    roleIds: [
      roles.monitoringMetricsPublisherRole
    ]
  }
}


output functionAppName string = functionApp.outputs.name
output managedIdentityName string = identity.outputs.name
output appInsightsName string = monitoring.outputs.applicationInsightsName
output logAnalyticsName string = monitoring.outputs.logAnalyticsWorkspaceName
output functionsStorageAccountName string = functionsStorage.outputs.name
output dataStorageAccountName string = dataStorage.outputs.name
