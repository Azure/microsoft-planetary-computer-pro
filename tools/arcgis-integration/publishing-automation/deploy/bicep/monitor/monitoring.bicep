@description('Name for the Log Analytics workspace.')
param logAnalyticsName string

@description('Name for the Application Insights instance.')
param applicationInsightsName string

@description('Azure region.')
param location string = resourceGroup().location

@description('Retention period in days.')
param retentionInDays int = 30

@description('Tags.')
param tags object = {}

resource logAnalytics 'Microsoft.OperationalInsights/workspaces@2023-09-01' = {
  name: logAnalyticsName
  location: location
  tags: tags
  properties: {
    retentionInDays: retentionInDays
    sku: {
      name: 'PerGB2018'
    }
  }
}

resource applicationInsights 'Microsoft.Insights/components@2020-02-02' = {
  name: applicationInsightsName
  location: location
  tags: tags
  kind: 'web'
  properties: {
    Application_Type: 'web'
    WorkspaceResourceId: logAnalytics.id
  }
}

output applicationInsightsName string = applicationInsights.name
output logAnalyticsName string = logAnalytics.name
