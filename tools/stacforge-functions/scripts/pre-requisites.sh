#!/bin/bash

set -e

# Check and install Azure CLI
if ! command -v az &> /dev/null; then
    echo "Installing Azure CLI..."
    curl -sL https://aka.ms/InstallAzureCLIDeb | sudo bash
else
    echo "Azure CLI is already installed."
fi

# Verify Azure CLI installation
az --version

# Check and install Azure Functions Core Tools
if ! command -v func &> /dev/null; then
    echo "Installing Azure Functions Core Tools..."
    curl -sL https://packages.microsoft.com/keys/microsoft.asc | gpg --dearmor > microsoft.gpg
    sudo mv microsoft.gpg /etc/apt/trusted.gpg.d/microsoft.gpg
    sudo sh -c 'echo "deb [arch=amd64] https://packages.microsoft.com/repos/azure-cli/ $(lsb_release -cs) main" > /etc/apt/sources.list.d/azure-cli.list'
    sudo apt-get update
    sudo apt-get install azure-functions-core-tools-4
else
    echo "Azure Functions Core Tools are already installed."
fi

# Verify Azure Functions Core Tools installation
func --version

# Check and install PowerShell 7.4
if ! command -v pwsh &> /dev/null || [[ $(pwsh -Command '$PSVersionTable.PSVersion.Major') -lt 7 ]] || [[ $(pwsh -Command '$PSVersionTable.PSVersion.Minor') -lt 4 ]]; then
    echo "Installing PowerShell 7.4..."
    wget https://github.com/PowerShell/PowerShell/releases/download/v7.4.0/powershell-7.4.0-linux-x64.tar.gz
    mkdir ~/powershell
    tar -xvf ./powershell-7.4.0-linux-x64.tar.gz -C ~/powershell
    sudo ln -s ~/powershell/pwsh /usr/bin/pwsh
else
    echo "PowerShell 7.4 or later is already installed."
fi

# Verify PowerShell installation
pwsh -Command '$PSVersionTable.PSVersion'

echo "All prerequisites installed successfully."