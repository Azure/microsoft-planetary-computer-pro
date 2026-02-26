# =============================================================================
# Configure ArcGIS Notebook Server for Managed Identity Access
# =============================================================================
# Configures the ArcGIS Notebook Server VM so that notebooks running in
# Docker containers can access Azure Managed Identity credentials.
#
# Two approaches are supported:
#   1. IMDS passthrough — route the Azure IMDS endpoint (169.254.169.254)
#      from within Docker containers to the host VM (preferred)
#   2. Service principal — set environment variables in the Docker config
#      for a service principal with GeoCatalog Reader access
#
# Prerequisites:
#   - Run as Administrator on the ArcGIS Notebook Server VM
#   - VM has a system-assigned managed identity with GeoCatalog Reader role
#     (run setup-managed-identity.sh first)
#
# Usage:
#   .\configure-notebook-server.ps1 -Method IMDS
#   .\configure-notebook-server.ps1 -Method ServicePrincipal -ClientId <id> -ClientSecret <secret> -TenantId <tenant>
# =============================================================================

param(
    [Parameter(Mandatory=$true)]
    [ValidateSet("IMDS", "ServicePrincipal")]
    [string]$Method,

    # Required for ServicePrincipal method
    [string]$ClientId = "",
    [string]$ClientSecret = "",
    [string]$TenantId = ""
)

$ErrorActionPreference = "Stop"

Write-Host "========================================"
Write-Host "  ArcGIS Notebook Server Configuration"
Write-Host "========================================"
Write-Host "  Method: $Method"
Write-Host ""

if ($Method -eq "IMDS") {
    Write-Host "Configuring IMDS passthrough for Docker containers..." -ForegroundColor Cyan
    Write-Host ""
    Write-Host "This method allows containers to access the Azure Instance Metadata" -ForegroundColor Gray
    Write-Host "Service (IMDS) endpoint at 169.254.169.254, which enables" -ForegroundColor Gray
    Write-Host "DefaultAzureCredential to use the VM's managed identity." -ForegroundColor Gray
    Write-Host ""

    # The Docker daemon configuration needs to allow the IMDS route
    $dockerConfigPath = "C:\ProgramData\Docker\config\daemon.json"

    if (Test-Path $dockerConfigPath) {
        $dockerConfig = Get-Content $dockerConfigPath | ConvertFrom-Json
    } else {
        $dockerConfig = @{}
    }

    Write-Host "Current Docker daemon config: $dockerConfigPath" -ForegroundColor Gray

    Write-Host ""
    Write-Host "IMPORTANT: ArcGIS Notebook Server Docker containers must be configured" -ForegroundColor Yellow
    Write-Host "to allow access to the host network's IMDS endpoint." -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Manual steps required:" -ForegroundColor Yellow
    Write-Host "  1. Ensure the Docker network configuration allows containers to" -ForegroundColor White
    Write-Host "     reach the link-local address 169.254.169.254" -ForegroundColor White
    Write-Host ""
    Write-Host "  2. If using Mirantis Container Runtime, add a route in the" -ForegroundColor White
    Write-Host "     container's network namespace:" -ForegroundColor White
    Write-Host '     route add 169.254.169.254 mask 255.255.255.255 <host_gateway>' -ForegroundColor White
    Write-Host ""
    Write-Host "  3. Alternatively, configure the ArcGIS Notebook Server Docker" -ForegroundColor White
    Write-Host "     runtime to pass the --add-host flag:" -ForegroundColor White
    Write-Host '     --add-host=metadata.azure.com:169.254.169.254' -ForegroundColor White
    Write-Host ""
    Write-Host "  4. Verify from within a notebook:" -ForegroundColor White
    Write-Host '     from azure.identity import ManagedIdentityCredential' -ForegroundColor White
    Write-Host '     cred = ManagedIdentityCredential()' -ForegroundColor White
    Write-Host '     token = cred.get_token("https://geocatalog.spatio.azure.com/.default")' -ForegroundColor White
    Write-Host '     print("Token acquired" if token else "Failed")' -ForegroundColor White
    Write-Host ""
    Write-Host "Note: The exact configuration depends on your Docker runtime." -ForegroundColor Gray
    Write-Host "Consult the ArcGIS Notebook Server documentation and your" -ForegroundColor Gray
    Write-Host "Docker runtime (Mirantis or Docker Engine) documentation." -ForegroundColor Gray

} elseif ($Method -eq "ServicePrincipal") {
    if (-not $ClientId -or -not $ClientSecret -or -not $TenantId) {
        Write-Error "ServicePrincipal method requires -ClientId, -ClientSecret, and -TenantId"
        exit 1
    }

    Write-Host "Configuring service principal credentials for Notebook Server..." -ForegroundColor Cyan
    Write-Host ""
    Write-Host "This method sets environment variables in the Docker container" -ForegroundColor Gray
    Write-Host "configuration so DefaultAzureCredential uses a service principal." -ForegroundColor Gray
    Write-Host ""

    # Set system environment variables that will be available to Docker containers
    Write-Host "Setting system environment variables..." -ForegroundColor Cyan
    [System.Environment]::SetEnvironmentVariable("AZURE_CLIENT_ID", $ClientId, "Machine")
    [System.Environment]::SetEnvironmentVariable("AZURE_CLIENT_SECRET", $ClientSecret, "Machine")
    [System.Environment]::SetEnvironmentVariable("AZURE_TENANT_ID", $TenantId, "Machine")

    Write-Host "  AZURE_CLIENT_ID set" -ForegroundColor Green
    Write-Host "  AZURE_CLIENT_SECRET set" -ForegroundColor Green
    Write-Host "  AZURE_TENANT_ID set" -ForegroundColor Green

    Write-Host ""
    Write-Host "IMPORTANT: You may need to configure ArcGIS Notebook Server to" -ForegroundColor Yellow
    Write-Host "pass these environment variables into the Docker containers." -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Check the Notebook Server's Docker configuration to ensure" -ForegroundColor White
    Write-Host "AZURE_CLIENT_ID, AZURE_CLIENT_SECRET, and AZURE_TENANT_ID" -ForegroundColor White
    Write-Host "are forwarded to the notebook runtime containers." -ForegroundColor White
    Write-Host ""
    Write-Host "After configuration, restart the ArcGIS Notebook Server service:" -ForegroundColor Yellow
    Write-Host '  Restart-Service "ArcGIS Notebook Server"' -ForegroundColor White
}

Write-Host ""
Write-Host "Configuration guidance complete." -ForegroundColor Green
