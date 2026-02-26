@description('The principal ID of the managed identity to assign roles to.')
param principalId string

@description('The principal type.')
@allowed(['Device', 'ForeignGroup', 'Group', 'ServicePrincipal', 'User'])
param principalType string = 'ServicePrincipal'

@description('The resource ID of the GeoCatalog to grant access to.')
param geoCatalogResourceId string

@description('Array of role definition IDs to assign.')
param roleIds array

resource roleAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = [
  for roleId in roleIds: {
    name: guid(principalId, geoCatalogResourceId, roleId)
    properties: {
      roleDefinitionId: resourceId('Microsoft.Authorization/roleDefinitions', roleId)
      principalId: principalId
      principalType: principalType
    }
  }
]
