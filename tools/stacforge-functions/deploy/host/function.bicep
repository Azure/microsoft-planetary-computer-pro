param planName string
param appName string
param planType string
param location string = resourceGroup().location
param managedIdentityName string
param functionsStorageAccountName string
param dataStorageAccountName string
param logsTableName string
param deploymentStorageContainerName string
param applicationInsightsName string
param tags object = {}
param functionAppRuntime string = 'python'
param functionAppRuntimeVersion string = '3.11'
param maximumInstanceCount int = 100
param instanceMemoryMB int = 2048

resource managedIdentity 'Microsoft.ManagedIdentity/userAssignedIdentities@2023-07-31-preview' existing = {
  name: managedIdentityName
}

resource storage 'Microsoft.Storage/storageAccounts@2023-05-01' existing = {
  name: functionsStorageAccountName
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
  // {
  //   name: 'FUNCTIONS_WORKER_RUNTIME_VERSION'
  //   value: functionAppRuntimeVersion
  // }
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
  {
    name: 'LOGS_STORAGE_ACCOUNT'
    value: dataStorageAccountName
  }
  {
    name: 'STORAGE_TABLE_LOGS_LEVEL'
    value: 'INFO'
  }
  {
    name: 'LOGS_TABLE'
    value: logsTableName
  }
  {
    name: 'DATA_STORAGE_ACCOUNT'
    value: dataStorageAccountName
  }
  {
    name: 'DATA_CONTAINER'
    value: 'collections'
  }
  {
    name: 'MIN_SAS_TOKEN_EXPIRATION_HOURS'
    value: '12'
  }
  {
    name: 'DEFAULT_SAS_TOKEN_EXPIRATION_HOURS'
    value: '24'
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
    functionAppConfig: planType == 'flex' ? {
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
    } : null
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
      {
        category: 'AppServiceAuthenticationLogs'
        enabled: true
      }
    ]
  }
}

resource metricsSettings 'Microsoft.Insights/diagnosticSettings@2021-05-01-preview' = {
  name: 'metrics'
  scope: functionApp
  properties: {
    workspaceId: appInsights.properties.WorkspaceResourceId
    metrics: [
      {
        category: 'AllMetrics'
        enabled: true
      }
    ]
  }
}



// ZipDeploy example
// param appServiceName string
// param deployToProduction bool = false
// param slot string = 'staging'

// @secure()
// param packageUri string

// resource appServiceName_ZipDeploy 'Microsoft.Web/sites/extensions@2021-02-01' = if (deployToProduction) {
//   name: '${appServiceName}/ZipDeploy'
//   properties: {
//     packageUri: packageUri
//     appOffline: true
//   }
// }

// resource appServiceName_slot_ZipDeploy 'Microsoft.Web/sites/slots/extensions@2021-02-01' = if (!deployToProduction) {
//   name: '${appServiceName}/${slot}/ZipDeploy'
//   properties: {
//     packageUri: packageUri
//     appOffline: true
//   }
// }

output name string = functionApp.name
