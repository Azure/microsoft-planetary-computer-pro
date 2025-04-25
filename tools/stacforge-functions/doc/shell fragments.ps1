$FUNCTION_KEY = az functionapp keys list --resource-group stacforgekommapr54321 --name baf27yfofv3qe --query functionKeys --output tsv
$FUNCTION_URL = "https://$(az functionapp show --resource-group stacforgekommapr54321 --name baf27yfofv3qe --query properties.defaultHostName --output tsv)/api/orchestrations/geotemplate_bulk_transform?code=$FUNCTION_KEY"
$body = @{
  crawlingType = "file"
  sourceStorageAccountName = "datazoo"
  sourceContainerName = "esri"
  pattern = "aerial/NAIP_COG/*.tif"
  templateUrl = "https://baf27yfofv3qedata.blob.core.windows.net/templates/generic_cog.j2"
  targetCollectionId = "weather-test"
}
$bodyJson = $body | ConvertTo-Json

Invoke-RestMethod -Uri $FUNCTION_URL -Method Post -Body $bodyJson -ContentType "application/json"