# Define the extension ID and update URL
$extensionID = "YOUR_EXTENSION_ID"  # Replace with your actual extension ID
$updateURL = "https://clients2.google.com/service/update2/crx"

# Define the registry path for Chrome Extensions
$regPath = "HKLM:\SOFTWARE\Policies\Google\Chrome\ExtensionInstallForcelist"

# Check if the registry path exists
if (-not (Test-Path $regPath)) {
    # Create the registry path
    New-Item -Path $regPath -Force
}

# Define the registry entry for the extension
$regValue = "$extensionID;$updateURL"

# Add the registry entry
Set-ItemProperty -Path $regPath -Name "1" -Value $regValue -Force
Write-Host "Chrome extension installed permanently"
