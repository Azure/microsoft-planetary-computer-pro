#!/bin/bash
# =============================================================================
# Setup Managed Identity for ArcGIS Server VM
# =============================================================================
# Enables system-assigned managed identity on the ArcGIS Server VM and
# assigns the GeoCatalog Reader role so the pipeline can query STAC.
#
# Prerequisites:
#   - Azure CLI authenticated (az login)
#   - Owner or User Access Administrator role on the GeoCatalog resource
#
# Usage:
#   ./setup-managed-identity.sh
# =============================================================================

set -e

script_dir=$(dirname "$0")

# Default parameter values — override via environment or edit below
VM_RESOURCE_GROUP="${VM_RESOURCE_GROUP:?Set VM_RESOURCE_GROUP}"
VM_NAME="${VM_NAME:?Set VM_NAME}"
GEOCATALOG_NAME="${GEOCATALOG_NAME:?Set GEOCATALOG_NAME}"
GEOCATALOG_RESOURCE_GROUP="${GEOCATALOG_RESOURCE_GROUP:?Set GEOCATALOG_RESOURCE_GROUP}"
SUBSCRIPTION_ID="${SUBSCRIPTION_ID:=$(az account show --query id -o tsv)}"

echo "========================================"
echo "  Managed Identity Setup"
echo "========================================"
echo "  VM:                $VM_NAME ($VM_RESOURCE_GROUP)"
echo "  GeoCatalog:        $GEOCATALOG_NAME ($GEOCATALOG_RESOURCE_GROUP)"
echo "  Subscription:      $SUBSCRIPTION_ID"
echo ""

# Step 1: Enable system-assigned managed identity on the VM
echo "Enabling system-assigned managed identity on VM '$VM_NAME'..."
az vm identity assign \
    --resource-group "$VM_RESOURCE_GROUP" \
    --name "$VM_NAME" \
    --output none

# Get the VM's principal ID
PRINCIPAL_ID=$(az vm show \
    --resource-group "$VM_RESOURCE_GROUP" \
    --name "$VM_NAME" \
    --query "identity.principalId" \
    --output tsv)

echo "  VM Principal ID: $PRINCIPAL_ID"

# Step 2: Build the GeoCatalog resource scope
GEOCATALOG_SCOPE="/subscriptions/$SUBSCRIPTION_ID/resourceGroups/$GEOCATALOG_RESOURCE_GROUP/providers/Microsoft.Orbital/geoCatalogs/$GEOCATALOG_NAME"
echo ""
echo "GeoCatalog scope: $GEOCATALOG_SCOPE"

# Step 3: Find the GeoCatalog Reader role definition
echo ""
echo "Looking up GeoCatalog Reader role..."
ROLE_ID=$(az role definition list \
    --name "GeoCatalog Reader" \
    --query "[0].id" \
    --output tsv 2>/dev/null || true)

if [[ -z "$ROLE_ID" ]]; then
    echo "WARNING: 'GeoCatalog Reader' role not found. Trying 'GeoCatalog Data Owner'..."
    ROLE_ID=$(az role definition list \
        --name "GeoCatalog Data Owner" \
        --query "[0].id" \
        --output tsv 2>/dev/null || true)
fi

if [[ -z "$ROLE_ID" ]]; then
    echo "ERROR: Could not find a GeoCatalog role definition."
    echo "Available GeoCatalog roles:"
    az role definition list --query "[?contains(roleName, 'GeoCatalog')].roleName" --output tsv
    exit 1
fi

echo "  Role: $ROLE_ID"

# Step 4: Assign the role
echo ""
echo "Assigning GeoCatalog role to VM managed identity..."
az role assignment create \
    --assignee-object-id "$PRINCIPAL_ID" \
    --assignee-principal-type ServicePrincipal \
    --role "$ROLE_ID" \
    --scope "$GEOCATALOG_SCOPE" \
    --output none

echo ""
echo -e "\033[1;32mManaged identity configured successfully!\033[0m"
echo ""
echo "The VM '$VM_NAME' can now query the MPC Pro GeoCatalog using"
echo "DefaultAzureCredential (which will pick up the system-assigned MI)."
