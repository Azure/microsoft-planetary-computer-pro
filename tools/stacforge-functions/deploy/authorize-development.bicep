@minLength(1)
@maxLength(64)
@description('Name of the the STACForge which is used to generate a short unique hash used in all resources.')
param forgeName string
param functionsStorageAccountName string = ''
param dataStorageAccountName string = ''
param location string
param principalId string
@allowed([ 'Device', 'ForeignGroup', 'Group', 'ServicePrincipal', 'User' ])
param principalType string

// Generate a unique name to be used in naming resources.
var nameUnique = toLower(uniqueString(resourceGroup().id, forgeName, location))

var roles = loadJsonContent('roles.json')

module functionsStoragePermissions 'permissions/storageaccountpermissions.bicep' = {
  name: 'functionsStoragePermissions'
  params: {
    principalId: principalId
    principalType: principalType
    storageAccountName: !empty(functionsStorageAccountName) ? functionsStorageAccountName : nameUnique
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
    principalId: principalId
    principalType: principalType
    storageAccountName: !empty(dataStorageAccountName) ? dataStorageAccountName : '${nameUnique}data'
    roleIds: [
      roles.storageBlobDataContributorRole
      roles.storageTableDataContributorRole
      roles.storageBlobDelegatorRole
    ]
  }
}

output dataStorageAccountName string = dataStoragePermissions.outputs.storageAccountName
