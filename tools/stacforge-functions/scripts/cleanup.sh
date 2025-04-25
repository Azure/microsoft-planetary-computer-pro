#! env /bin/bash

# Fail script on error
set -e

script_dir=`dirname $0`

source $script_dir/user_params.txt

if [[ -z $resource_group ]]
then
    echo "Mandatory field missing value. Please check $script_dir/user_params.txt file."
    exit 1
fi

# Function to delete Azure resources
delete_resources() {
    echo "Deleting Azure resources group $resource_group..."
    az group delete --name $resource_group --yes --no-wait
}

# Prompt the user for confirmation
read -p "This action will permanently delete all the resources under $resource_group and is irreversible. \
Are you sure you want to proceed? (yes/no): " CONFIRMATION

# Check the user's response
if [[ "$CONFIRMATION" == "yes" ]]; then
    resource_group_exists=$(az group exists --name $resource_group)

    if [[ "$resource_group_exists" == "true" ]]; then
        delete_resources
    else
        echo "Resource group $resource_group does not exist."
    fi
else
    echo "Action cancelled. No resources were deleted."
fi