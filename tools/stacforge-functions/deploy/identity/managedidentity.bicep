param identityName string
param location string = resourceGroup().location
param tags object = {}

resource managedIdentity 'Microsoft.ManagedIdentity/userAssignedIdentities@2023-07-31-preview' = {
  name: identityName
  location: location
  tags: tags
}

output name string = managedIdentity.name
output principalId string = managedIdentity.properties.principalId
