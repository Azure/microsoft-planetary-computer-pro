param principalId string
@allowed([ 'Device', 'ForeignGroup', 'Group', 'ServicePrincipal', 'User' ])
param principalType string = 'ServicePrincipal'
param storageAccountName string
param roleIds array

resource storage 'Microsoft.Storage/storageAccounts@2023-05-01' existing = {
  name: storageAccountName
}

resource roleAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = [for roleId in roleIds: {
  name: guid(principalId, storage.id, roleId)
  scope: storage
  properties: {
    roleDefinitionId: resourceId('Microsoft.Authorization/roleDefinitions', roleId)
    principalId: principalId
    principalType: principalType
  }
}]

output storageAccountName string = storage.name
