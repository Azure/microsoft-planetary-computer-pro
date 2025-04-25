param (
    [Parameter(Mandatory=$true)]
    [string]$StacforgeName,

    [Parameter(Mandatory=$true)]
    [string]$StacforgeResourceGroupName,

    [Parameter(Mandatory=$true)]
    [string]$StacforgeLocation
)

$script_dir = Split-Path -Parent $MyInvocation.MyCommand.Path

# Get the current user's ID
$user_id = az ad signed-in-user show --query id --output tsv

az deployment group create `
    --resource-group $StacforgeResourceGroupName `
    --template-file "$script_dir/../deploy/authorize-development.bicep" `
    --parameters `
        forgeName=$StacforgeName `
        location=$StacforgeLocation `
        principalId=$user_id `
        principalType=User
