#! env /bin/bash

# Fail script on error
set -e

script_dir=`dirname $0`

source $script_dir/user_params.txt

if [[ -z $resource_group || -z $stacforge_name || -z $location || -z $app_plan ]]
then
    echo "Mandatory field missing value. Please check $script_dir/user_params.txt file."
    exit 1
fi

# Create the resource group
echo Creating resource group $resource_group at $location
az group create --name $resource_group --location $location > /dev/null

# Deploy STACForge infrastructure
echo Deploying STACForge $stacforge_name
deployment=$(az deployment group create \
    --resource-group $resource_group \
    --template-file $script_dir/../deploy/main.bicep \
    --parameters \
        forgeName=$stacforge_name \
        functionPlanType=$app_plan)

data_storage_account=`echo $deployment | jq -r '.properties.outputs.dataStorageAccountName.value'`
function_app_name=`echo $deployment | jq -r '.properties.outputs.functionAppName.value'`
managed_identity=`echo $deployment | jq -r '.properties.outputs.managedIdentityName.value'`

echo Function created with name $function_app_name
echo Data storage account is $data_storage_account
echo Managed identity is $managed_identity

echo -e "\033[1;32mSTACForge deployment completed successfully!\033[0m"