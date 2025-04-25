param principalId string
@allowed([ 'Device', 'ForeignGroup', 'Group', 'ServicePrincipal', 'User' ])
param principalType string = 'ServicePrincipal'
param appInsightsName string
param roleIds array

resource appInsights 'Microsoft.Insights/components@2020-02-02' existing = {
  name: appInsightsName
}

resource roleAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = [for roleId in roleIds: {
  name: guid(principalId, appInsights.id, roleId)
  scope: appInsights
  properties: {
    roleDefinitionId: resourceId('Microsoft.Authorization/roleDefinitions', roleId)
    principalId: principalId
    principalType: principalType
  }
}]
