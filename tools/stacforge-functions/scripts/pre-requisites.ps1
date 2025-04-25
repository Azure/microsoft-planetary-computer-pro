# Check and install Azure CLI
if (-not (Get-Command az -ErrorAction SilentlyContinue)) {
    Write-Output "Installing Azure CLI..."
    Invoke-WebRequest -Uri https://aka.ms/installazurecliwindows -OutFile .\AzureCLI.msi
    Start-Process msiexec.exe -ArgumentList '/I AzureCLI.msi /quiet' -Wait
    Remove-Item .\AzureCLI.msi
} else {
    Write-Output "Azure CLI is already installed."
}

# Verify Azure CLI installation
az --version

# Check and install Azure Functions Core Tools
if (-not (Get-Command func -ErrorAction SilentlyContinue)) {
    Write-Output "Installing Azure Functions Core Tools..."
    Invoke-WebRequest -Uri https://aka.ms/InstallAzureFunctionsCoreTools -OutFile .\AzureFunctionsCoreTools.msi
    Start-Process msiexec.exe -ArgumentList '/I AzureFunctionsCoreTools.msi /quiet' -Wait
    Remove-Item .\AzureFunctionsCoreTools.msi
} else {
    Write-Output "Azure Functions Core Tools are already installed."
}

# Verify Azure Functions Core Tools installation
func --version

# Check and install PowerShell 7.4
if (-not ($PSVersionTable.PSVersion -and $PSVersionTable.PSVersion.Major -eq 7 -and $PSVersionTable.PSVersion.Minor -ge 4)) {
    Write-Output "Installing PowerShell 7.4..."
    Invoke-WebRequest -Uri https://github.com/PowerShell/PowerShell/releases/download/v7.4.0/PowerShell-7.4.0-win-x64.msi -OutFile .\PowerShell.msi
    Start-Process msiexec.exe -ArgumentList '/I PowerShell.msi /quiet' -Wait
    Remove-Item .\PowerShell.msi
} else {
    Write-Output "PowerShell 7.4 or later is already installed."
}

# Verify PowerShell installation
pwsh -Command '$PSVersionTable.PSVersion'