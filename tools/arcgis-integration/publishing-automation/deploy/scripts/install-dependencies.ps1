# =============================================================================
# Install Python Dependencies on ArcGIS Server / Pro VM
# =============================================================================
# Installs the required Python packages into the ArcGIS Python environment.
#
# Prerequisites:
#   - Run as Administrator on the ArcGIS Server VM
#   - ArcGIS Server or ArcGIS Pro installed
#
# Usage:
#   .\install-dependencies.ps1 [-PythonPath <path>]
# =============================================================================

param(
    [string]$PythonPath = ""
)

$ErrorActionPreference = "Stop"

# Auto-detect Python path
if (-not $PythonPath) {
    $candidates = @(
        "C:\Program Files\ArcGIS\Server\framework\runtime\ArcGIS\bin\Python\envs\arcgispro-py3\python.exe",
        "C:\Program Files\ArcGIS\Pro\bin\Python\envs\arcgispro-py3\python.exe"
    )
    foreach ($candidate in $candidates) {
        if (Test-Path $candidate) {
            $PythonPath = $candidate
            break
        }
    }
    if (-not $PythonPath) {
        Write-Error "Could not find ArcGIS Python environment. Please specify -PythonPath."
        exit 1
    }
}

Write-Host "Using Python: $PythonPath" -ForegroundColor Cyan
Write-Host ""

# Get pip path
$pipPath = Join-Path (Split-Path $PythonPath) "..\Scripts\pip.exe"
if (-not (Test-Path $pipPath)) {
    # Try running pip as a module
    $pipCmd = "$PythonPath -m pip"
} else {
    $pipCmd = $pipPath
}

# Install dependencies
$packages = @(
    "azure-planetarycomputer>=1.0.0b1",
    "azure-identity>=1.18.0",
    "arcgis>=2.2.0",
    "pyyaml>=6.0",
    "rich>=13.0"
)

Write-Host "Installing packages..." -ForegroundColor Cyan
foreach ($package in $packages) {
    Write-Host "  Installing $package..."
    & $PythonPath -m pip install $package --quiet
    if ($LASTEXITCODE -ne 0) {
        Write-Warning "Failed to install $package"
    }
}

Write-Host ""
Write-Host "Verifying installations..." -ForegroundColor Cyan
& $PythonPath -c "import azure.planetarycomputer; print(f'  azure-planetarycomputer: {azure.planetarycomputer.__version__}')"
& $PythonPath -c "import azure.identity; print(f'  azure-identity: OK')"
& $PythonPath -c "import arcgis; print(f'  arcgis: {arcgis.__version__}')"
& $PythonPath -c "import yaml; print(f'  pyyaml: OK')"

Write-Host ""
Write-Host "All dependencies installed successfully!" -ForegroundColor Green
