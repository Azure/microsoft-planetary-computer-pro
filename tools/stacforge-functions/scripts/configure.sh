#! env /bin/bash

# Fail script on error
set -e

script_dir=`dirname $0`

source $script_dir/user_params.txt

if [[ -z $resource_group || -z $stacforge_name || -z $location ]]
then
    echo "Mandatory field missing value. Please check $script_dir/user_params.txt file."
    exit 1
fi

# Assign the required permissions to the user running the script.
echo "Assigning permissions to user..."
user_id=`az ad signed-in-user show --query id --output tsv`
deployment=$(az deployment group create \
    --resource-group $resource_group \
    --template-file $script_dir/../deploy/authorize-development.bicep \
    --parameters \
        forgeName=$stacforge_name \
        location=$location \
        principalId=$user_id \
        principalType=User)

# Retrieve the data storage account name.
data_storage_account=`echo $deployment | jq -r '.properties.outputs.dataStorageAccountName.value'`

# Upload templates
echo Uploading templates
az storage blob upload-batch \
    --account-name $data_storage_account \
    --destination templates \
    --source $script_dir/../templates \
    --auth-mode login \
    --overwrite > /dev/null

# Assign read permissions to source storage if provided
if [ -n "$source_storage_account" ]; then
    managed_identity=$(az identity list --resource-group $resource_group --query "[].name" -o tsv)
    source_storage_rg=$(az storage account show --name $source_storage_account --query resourceGroup -o tsv)
    echo Assigning read permissions to source storage account
    az role assignment create \
        --role "Storage Blob Data Reader" \
        --assignee-object-id `az identity show --resource-group $resource_group --name $managed_identity --query principalId --output tsv` \
        --scope `az storage account show --name $source_storage_account --resource-group $source_storage_rg --query id --output tsv` \
        --assignee-principal-type ServicePrincipal > /dev/null
fi

echo -e "\033[1;32mSuccessfully configured the STACForge!\033[0m"