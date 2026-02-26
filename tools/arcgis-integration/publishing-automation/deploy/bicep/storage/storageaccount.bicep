@description('Storage account name.')
param name string

@description('Azure region.')
param location string = resourceGroup().location

@description('Tags.')
param tags object = {}

@description('Allow shared key access (required for consumption plan).')
param allowSharedKeyAccess bool = true

@description('Blob containers to create.')
param containers array = []

resource storageAccount 'Microsoft.Storage/storageAccounts@2023-05-01' = {
  name: name
  location: location
  tags: tags
  kind: 'StorageV2'
  sku: {
    name: 'Standard_LRS'
  }
  properties: {
    allowSharedKeyAccess: allowSharedKeyAccess
    minimumTlsVersion: 'TLS1_2'
    supportsHttpsTrafficOnly: true
  }
}

resource blobService 'Microsoft.Storage/storageAccounts/blobServices@2023-05-01' = {
  parent: storageAccount
  name: 'default'
}

resource container 'Microsoft.Storage/storageAccounts/blobServices/containers@2023-05-01' = [
  for c in containers: {
    parent: blobService
    name: c.name
    properties: {
      publicAccess: 'None'
    }
  }
]

output name string = storageAccount.name
