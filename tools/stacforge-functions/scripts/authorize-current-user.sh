#! env /bin/bash

# $1: STACForge Name -> Required
# $2: STACForge Resource Group -> Required
# $3: Location -> Required

if [ $# -lt 3 ]; then
    echo "Usage: `basename $0` <stacforge_name> <stacforge_rg> <stacforge_location>"
    exit 1
fi

stacforge_name=$1
stacforge_rg=$2
stacforge_location=$3

script_dir=`dirname $0`

# Get the current user's ID
user_id=`az ad signed-in-user show --query id --output tsv`

az deployment group create \
    --resource-group $stacforge_rg \
    --template-file $script_dir/../deploy/authorize-development.bicep \
    --parameters \
        forgeName=$stacforge_name \
        location=$stacforge_location \
        principalId=$user_id \
        principalType=User
