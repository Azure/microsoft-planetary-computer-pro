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

# Get VM Principal ID
azure_vm_id=`curl -s -H Metadata:true --noproxy "*" "http://169.254.169.254/metadata/instance?api-version=2021-02-01" | jq -r '.compute.resourceId'`
azure_vm_mi_id=`az vm show --id $azure_vm_id --query 'identity.principalId' -o tsv`

az deployment group create \
    --resource-group $stacforge_rg \
    --template-file $script_dir/../deploy/authorize-development.bicep \
    --parameters \
        forgeName=$stacforge_name \
        location=$stacforge_location \
        principalId=$azure_vm_mi_id \
        principalType=ServicePrincipal
