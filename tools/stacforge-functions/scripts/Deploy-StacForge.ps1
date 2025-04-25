# Set the error action preference to stop on any error
$ErrorActionPreference = "Stop"

# Get the directory of the script
$script_dir = Split-Path -Parent $MyInvocation.MyCommand.Path

# Define the path to the input file
$inputFilePath = "$script_dir\user_params.txt"

# Initialize a hashtable to store the key-value pairs
$config = @{}

# Read the file line by line
Get-Content -Path $inputFilePath | ForEach-Object {
    # Split each line into key and value
    $parts = $_ -split '='
    if ($parts.Length -eq 2) {
        $key = $parts[0].Trim()
        $value = $parts[1].Trim()
        # Check if the value is empty
        if (-not $value) {
            Write-Output "Error: The value for '$key' cannot be empty. Please check $inputFilePath."
            exit 1
        }
        # Add the key-value pair to the hashtable
        $config[$key] = $value
    }
}

# Access the values
$StacforgeResourceGroupName = $config["resource_group"]
$StacforgeLocation = $config["location"]
$StacforgeName = $config["stacforge_name"]
$FunctionAppPlan = $config["app_plan"]
$DataSourceStorageAccountName = $config["source_storage_account"]

# Create the resource group
Write-Output "Creating resource group $StacforgeResourceGroupName at $StacforgeLocation"
az group create --name $StacforgeResourceGroupName --location $StacforgeLocation > $null

# Deploy STACForge infrastructure
Write-Output "Deploying STACForge $StacforgeName"
$deployment = az deployment group create `
    --resource-group $StacforgeResourceGroupName `
    --template-file "$script_dir/../deploy/main.bicep" `
    --parameters `
        forgeName=$StacforgeName `
        functionPlanType=$FunctionAppPlan | ConvertFrom-Json

$data_storage_account = $deployment.properties.outputs.dataStorageAccountName.value
$function_app_name = $deployment.properties.outputs.functionAppName.value
$managed_identity = $deployment.properties.outputs.managedIdentityName.value

Write-Output "Function created with name $function_app_name"
Write-Output "Data storage account is $data_storage_account"

# Assign permissions to user
Write-Output "Assigning permissions to user"
$user_id = az ad signed-in-user show --query id --output tsv
az deployment group create `
    --resource-group $StacforgeResourceGroupName `
    --template-file "$script_dir/../deploy/authorize-development.bicep" `
    --parameters `
        forgeName=$StacforgeName `
        location=$StacforgeLocation `
        principalId=$user_id `
        principalType=User > $null

# Assign read permissions to source storage if provided
if ($DataSourceStorageAccountName) {
    $DataSourceStorageResourceGroupName = az storage account show --name $DataSourceStorageAccountName --query "resourceGroup" -o tsv
    Write-Output "Assigning read permissions to source storage account"
    $principalId = az identity show --resource-group $StacforgeResourceGroupName --name $managed_identity --query principalId --output tsv
    $scope = az storage account show --name $DataSourceStorageAccountName --resource-group $DataSourceStorageResourceGroupName --query id --output tsv
    az role assignment create `
        --role "Storage Blob Data Reader" `
        --assignee-object-id $principalId `
        --scope $scope `
        --assignee-principal-type ServicePrincipal > $null

    # Wait for the role assignment to propagate
    $roleAssigned = $false
    while (-not $roleAssigned) {
        Start-Sleep -Seconds 10
        $roleAssignment = az role assignment list --assignee $principalId --scope $scope --query "[?roleDefinitionName=='Storage Blob Data Reader']" -o tsv
        if ($roleAssignment) {
            $roleAssigned = $true
        } else {
            Write-Output "Waiting for role assignment to propagate..."
        }
    }
    Write-Output "Role assignment successful. Proceeding with file upload."
}

# Upload templates
Write-Output "Uploading templates"
az storage blob upload-batch `
    --account-name $data_storage_account `
    --destination templates `
    --source "$script_dir/../templates" `
    --auth-mode login `
    --overwrite > $null

# Deploy STACForge code
Write-Output "Deploying code"
$current_dir = Get-Location
Set-Location "$script_dir/../src"
func azure functionapp publish $function_app_name
Remove-Item -Recurse -Force "$script_dir/../src/.python_packages"
Set-Location $current_dir

$function_key = az functionapp keys list `
    --resource-group $StacforgeResourceGroupName `
    --name $function_app_name `
    --query functionKeys `
    --output tsv

if ($FunctionAppPlan -eq "consumption") {
    $hostname = az functionapp show --resource-group $StacforgeResourceGroupName --name $function_app_name --query defaultHostName --output tsv
} else {
    $hostname = az functionapp show --resource-group $StacforgeResourceGroupName --name $function_app_name --query properties.defaultHostName --output tsv
}

$endpoint = "https://$hostname/api/orchestrations/geotemplate_bulk_transform?code=$function_key"

Write-Output ""
Write-Output "Deployment successfully completed!"
Write-Output "To invoke a STACForge transformation, use the following endpoint:"
Write-Output $endpoint
