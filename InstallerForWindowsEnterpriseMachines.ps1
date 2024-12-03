# Function to check if pip is installed
function Check-PipInstalled {
    try {
        pip --version | Out-Null
        return $true
    } catch {
        return $false
    }
}

# Check if pip is installed
if (-not (Check-PipInstalled)) {
    Write-Host "pip is not installed. Please install Python and ensure pip is available." -ForegroundColor Red
    exit
}

# List of packages to install
$packages = @(
    "python-dotenv",
    "django",
    "django-cors-headers",
    "bs4",
    "django-request",
    "openai==0.28",
    "google",
    "transformers",
    "torch",
    "accelerate",
    "tensorflow"
)

# Loop through each package and install it
foreach ($package in $packages) {
    Write-Host "Installing $package..."
    pip install $package
}

Write-Host "All packages have been installed."

Stop-Process -Name chrome -Force
#Chrome stopped
Write-Host "Chrome stopped"

$curDir=$PSScriptRoot
$extensionPath= Join-Path $curDir "ChatBot-Fin\Extension-ChatBot-Fin\src"

# Define the extension ID and the path to the unpacked extension
$extensionID = "ijpgbijebnejemnamacehfmifhlhmcei"  # Replace with your actual extension ID

# Define the registry path for Chrome Extensions
$regPath = "HKLM:\SOFTWARE\Policies\Google\Chrome\ExtensionInstallForcelist"

# Check if the registry path exists
if (-not (Test-Path $regPath)) {
    # Create the registry path if it doesn't exist
    New-Item -Path $regPath -Force
}

# Define the registry entry for the unpacked extension (using file path instead of CRX or update URL)
$regValue = "$extensionID;$extensionPath"

# Add the registry entry with a unique name (e.g., "1" for the first entry)
Set-ItemProperty -Path $regPath -Name "1" -Value $regValue -Force

Write-Host "Unpacked Chrome extension installed permanently"
