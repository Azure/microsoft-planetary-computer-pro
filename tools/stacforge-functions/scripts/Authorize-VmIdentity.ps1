param (
    [Parameter(Mandatory=$true)]
    [string]$StacforgeName,

    [Parameter(Mandatory=$true)]
    [string]$StacforgeResourceGroupName,

    [Parameter(Mandatory=$true)]
    [string]$StacforgeLocation

)

$script_dir = Split-Path -Parent $MyInvocation.MyCommand.Path

# Get VM Principal ID
$azure_vm_id = (Invoke-RestMethod -Headers @{Metadata="true"} -Uri "http://169.254.169.254/metadata/instance?api-version=2021-02-01" -UseBasicParsing).compute.resourceId
$azure_vm_mi_id = az vm show --id $azure_vm_id --query 'identity.principalId' -o tsv

az deployment group create `
    --resource-group $StacforgeResourceGroupName `
    --template-file "$script_dir/../deploy/authorize-development.bicep" `
    --parameters `
        forgeName=$StacforgeName `
        location=$StacforgeLocation `
        principalId=$azure_vm_mi_id `
        principalType=ServicePrincipal
