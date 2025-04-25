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

function_app_name=$(az functionapp list --resource-group $resource_group --query "[].name" -o tsv)

# Deploy STACForge code
echo "Deploying function app code..."
cd $script_dir/../src
func azure functionapp publish $function_app_name
rm -rf $script_dir/../src/.python_packages

function_key=`az functionapp keys list \
    --resource-group $resource_group \
    --name $function_app_name \
    --query functionKeys \
    --output tsv`

if [ $app_plan == "consumption" ]; then
    hostname=`az functionapp show --resource-group $resource_group --name $function_app_name --query defaultHostName --output tsv`
else
    hostname=`az functionapp show --resource-group $resource_group --name $function_app_name --query properties.defaultHostName --output tsv`
fi

endpoint=https://$hostname/api/orchestrations/geotemplate_bulk_transform?code=$function_key

echo To invoke a STACForge transformation, use the following endpoint:
echo $endpoint

echo -e "\033[1;32mDeployment successfully completed!\033[0m"