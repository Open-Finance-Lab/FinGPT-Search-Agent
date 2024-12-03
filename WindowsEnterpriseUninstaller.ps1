# Function to check if running as Administrator
function Check-Admin {
    if (-not ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole] "Administrator")) {
        Write-Host "This script requires Administrator privileges. Please run as Administrator." -ForegroundColor Red
        exit
    }
}

# Ensure script is run as Administrator
Check-Admin

# Define the extension ID and registry path
$extensionID = "ijpgbijebnejemnamacehfmifhlhmcei"  # Replace with your actual extension ID
$regPath = "HKLM:\SOFTWARE\Policies\Google\Chrome\ExtensionInstallForcelist"

# Check if the registry path exists
if (Test-Path $regPath) {
    # Check if the registry entry for the extension exists
    try {
        $regValue = Get-ItemProperty -Path $regPath -Name "1" -ErrorAction Stop
        if ($regValue -match $extensionID) {
            # Remove the registry entry
            Remove-ItemProperty -Path $regPath -Name "1" -Force
            Write-Host "Extension registry entry removed."
        } else {
            Write-Host "No matching registry entry found for the extension ID."
        }
    } catch {
        Write-Host "No registry entry found for this extension."
    }
} else {
    Write-Host "Registry path for Chrome extensions does not exist."
}

# Stop Chrome process if running
$chromeProcesses = Get-Process -Name chrome -ErrorAction SilentlyContinue
if ($chromeProcesses) {
    Write-Host "Chrome is still running. Closing Chrome..."
    Stop-Process -Name chrome -Force
    Write-Host "Chrome stopped."
} else {
    Write-Host "Chrome was not running."
}

# Check if the extension folder exists (optional cleanup)
$curDir = $PSScriptRoot
$extensionPath = Join-Path $curDir "ChatBot-Fin\Extension-ChatBot-Fin\src"

if (Test-Path $extensionPath) {
    try {
        Remove-Item -Path $extensionPath -Recurse -Force
        Write-Host "Extension files have been deleted from: $extensionPath"
    } catch {
        Write-Host "Failed to delete extension files. Ensure you have permission to modify the folder."
    }
} else {
    Write-Host "Extension folder not found. No files to delete."
}

# Refresh Chrome policies
Write-Host "Refreshing Chrome policies..."
gpupdate /force

Write-Host "Uninstallation completed. Restart Chrome to apply changes."
