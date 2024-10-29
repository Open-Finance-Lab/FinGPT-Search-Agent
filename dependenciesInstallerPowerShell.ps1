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
$extensionPath= Join-Path $curDir "ChatBot-Fin/Extension-ChatBot-Fin/src"

#load extension
Write-Host $extensionPath
chrome --load-extension=$extensionPath
Write-Host "FinGPT extension loaded onto Chrome"
