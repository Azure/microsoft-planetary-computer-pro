# =============================================================================
# Setup Windows Scheduled Task for Publishing Automation
# =============================================================================
# Creates a Windows Scheduled Task on the ArcGIS Server VM that runs the
# publishing automation pipeline at a configurable interval.
#
# Prerequisites:
#   - Run as Administrator on the ArcGIS Server VM
#   - Python dependencies installed (run install-dependencies.ps1 first)
#   - config.yaml configured
#   - VM managed identity configured with GeoCatalog Reader role
#
# Usage:
#   .\setup-vm-task.ps1 -ConfigPath "D:\automation\config.yaml" [-IntervalHours 6]
# =============================================================================

param(
    [Parameter(Mandatory=$true)]
    [string]$ConfigPath,

    [int]$IntervalHours = 6,

    [string]$TaskName = "MPC-Publishing-Automation",

    [string]$PythonPath = ""
)

$ErrorActionPreference = "Stop"

# Auto-detect Python path from ArcGIS Server or ArcGIS Pro if not specified
if (-not $PythonPath) {
    $candidates = @(
        "C:\Program Files\ArcGIS\Server\framework\runtime\ArcGIS\bin\Python\envs\arcgispro-py3\python.exe",
        "C:\Program Files\ArcGIS\Pro\bin\Python\envs\arcgispro-py3\python.exe",
        "C:\Python311\python.exe"
    )
    foreach ($candidate in $candidates) {
        if (Test-Path $candidate) {
            $PythonPath = $candidate
            break
        }
    }
    if (-not $PythonPath) {
        # Fall back to system Python
        $PythonPath = (Get-Command python -ErrorAction SilentlyContinue).Source
        if (-not $PythonPath) {
            Write-Error "Could not find Python. Please specify -PythonPath."
            exit 1
        }
    }
}

Write-Host "Using Python: $PythonPath" -ForegroundColor Cyan

# Determine the path to run.py
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$runScript = Join-Path (Split-Path -Parent (Split-Path -Parent $scriptDir)) "src\run.py"

if (-not (Test-Path $runScript)) {
    Write-Error "Pipeline script not found at: $runScript"
    exit 1
}

if (-not (Test-Path $ConfigPath)) {
    Write-Error "Config file not found at: $ConfigPath"
    exit 1
}

# Create the scheduled task
Write-Host "Creating scheduled task '$TaskName'..." -ForegroundColor Cyan

$action = New-ScheduledTaskAction `
    -Execute $PythonPath `
    -Argument "-m src.run --config `"$ConfigPath`"" `
    -WorkingDirectory (Split-Path -Parent (Split-Path -Parent $scriptDir))

$trigger = New-ScheduledTaskTrigger `
    -Once `
    -At (Get-Date) `
    -RepetitionInterval (New-TimeSpan -Hours $IntervalHours) `
    -RepetitionDuration ([System.TimeSpan]::MaxValue)

$settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -StartWhenAvailable `
    -RunOnlyIfNetworkAvailable `
    -MultipleInstances IgnoreNew

# Use SYSTEM account for managed identity access
$principal = New-ScheduledTaskPrincipal `
    -UserId "SYSTEM" `
    -LogonType ServiceAccount `
    -RunLevel Highest

# Remove existing task if present
if (Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue) {
    Write-Host "Removing existing task '$TaskName'..." -ForegroundColor Yellow
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
}

Register-ScheduledTask `
    -TaskName $TaskName `
    -Action $action `
    -Trigger $trigger `
    -Settings $settings `
    -Principal $principal `
    -Description "MPC Pro Publishing Automation — discovers new imagery and publishes to ArcGIS Enterprise"

Write-Host "`nScheduled task created successfully!" -ForegroundColor Green
Write-Host "  Task Name:  $TaskName"
Write-Host "  Interval:   Every $IntervalHours hours"
Write-Host "  Python:     $PythonPath"
Write-Host "  Config:     $ConfigPath"
Write-Host ""
Write-Host "To run the task immediately:" -ForegroundColor Yellow
Write-Host "  Start-ScheduledTask -TaskName '$TaskName'"
Write-Host ""
Write-Host "To check task status:" -ForegroundColor Yellow
Write-Host "  Get-ScheduledTask -TaskName '$TaskName' | Get-ScheduledTaskInfo"
