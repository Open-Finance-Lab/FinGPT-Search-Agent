# Requires Windows PowerShell 5.1 or PowerShell 7+
# Usage: Double-click (or Right-Click -> "Run with PowerShell")
#        from the root folder of your FinGPT project.

Write-Host "`n========== FinGPT Installer for Windows =========="

###############################################################################
# 1. Check if Python is installed
###############################################################################
Write-Host "`nChecking if Python is installed..."
$python = Get-Command python -ErrorAction SilentlyContinue

if (-not $python) {
    Write-Host "`nERROR: Python is not installed on this system."
    Write-Host "Please download and install Python 3.9+ from here:"
    Write-Host "  https://www.python.org/downloads/"
    Write-Host "Once installed, please rerun this script."
    exit 1
}

Write-Host "Python found at: $($python.Source)"

###############################################################################
# 2. Check if Django’s default port is already in use
###############################################################################
Write-Host "`nChecking if port 8000 is already in use..."
# Attempt to connect to localhost:8000
try {
    $portCheck = Test-NetConnection -ComputerName 127.0.0.1 -Port 8000 -WarningAction SilentlyContinue
} catch {
    # If Test-NetConnection is unavailable (older Powershell), fallback to netstat
    Write-Host "Test-NetConnection not available; trying netstat fallback..."
    $netstatResult = netstat -ano | Select-String ":8000"
    if ($netstatResult) {
        Write-Host "`nERROR: Port 8000 is in use. Please close whatever is running on 127.0.0.1:8000"
        Write-Host "Then rerun this script."
        exit 1
    } else {
        Write-Host "Port 8000 appears to be free."
    }
}

if ($portCheck.TcpTestSucceeded -eq $true) {
    Write-Host "`nERROR: Port 8000 is in use. Possibly another Django or a different server is running."
    Write-Host "Please stop that process, then rerun this script."
    exit 1
} else {
    Write-Host "Port 8000 appears to be free."
}

###############################################################################
# 3. Create / Activate Virtual Environment
###############################################################################
Write-Host "`nEnsuring a virtual environment is set up..."

# Path to your venv folder - adjust the name/path as desired
$venvPath = Join-Path $PSScriptRoot "FinGPTenv"

if (!(Test-Path $venvPath)) {
    Write-Host "Creating a new virtual environment at: $venvPath"
    python -m venv $venvPath
    if ($LASTEXITCODE -ne 0) {
        Write-Host "ERROR: Could not create virtual environment. Please check your Python installation."
        exit 1
    }
} else {
    Write-Host "Virtual environment folder already exists at $venvPath."
}

Write-Host "Activating the virtual environment..."

# Activate script for Windows
$activateScript = Join-Path $venvPath "Scripts\Activate.ps1"

if (!(Test-Path $activateScript)) {
    Write-Host "ERROR: Could not find the activate.ps1 script in $activateScript"
    exit 1
}

# Temporarily dot-source the activation script in this session
. $activateScript

###############################################################################
# 4. Install Dependencies
###############################################################################
Write-Host "`nUpgrading pip in the virtual environment..."
pip install --upgrade pip

# requirements file
$requirementsFile = Join-Path $PSScriptRoot "requirements_win.txt"
if (!(Test-Path $requirementsFile)) {
    Write-Host "ERROR: requirements_win.txt not found at $requirementsFile"
    exit 1
}

Write-Host "`nInstalling dependencies from requirements_win.txt..."
pip install -r $requirementsFile

Write-Host "All dependencies installed successfully."

###############################################################################
# 5. Attempt to stop any existing Django server (if user had one)
###############################################################################
# This is an optional step; if the user might have started the server manually,
# you can attempt to kill Python processes. But that's a bit aggressive,
# so we do it only if we want to forcibly free port 8000.
# If you'd rather not forcibly kill existing servers, you can skip this.

#Write-Host "`nAttempting to close any existing Django server on port 8000..."
# (Uncomment if you want a more aggressive approach):
#Get-Process -Name python -ErrorAction SilentlyContinue | ForEach-Object {
#    $_.CloseMainWindow()
#    Start-Sleep -Seconds 1
#    if (!$_.HasExited) {
#        $_.Kill()
#    }
#}

###############################################################################
# 6. Start Django Back-End (in new PowerShell window)
###############################################################################
Write-Host "`nStarting Django back-end..."

# Path to your Django project folder
$serverPath = Join-Path $PSScriptRoot "ChatBot-Fin\chat_server"

if (!(Test-Path $serverPath)) {
    Write-Host "ERROR: ChatBot-Fin\\chat_server folder not found at $serverPath"
    exit 1
}

# Build a command that:
# 1) changes directory to chat_server,
# 2) activates venv,
# 3) runs server
$serverCommand = "
cd `"$serverPath`"
. `"$venvPath\Scripts\Activate.ps1`"
python manage.py runserver
"

Write-Host "Launching Django server in new PowerShell window..."
Start-Process "powershell.exe" -ArgumentList "-NoExit","-Command $serverCommand" -WindowStyle Normal

###############################################################################
# 7. Uninstall existing FinGPT extension (Best-effort)
###############################################################################
Write-Host "`nAttempting to remove any existing FinGPT extension..."

# If your extension is from the Chrome Web Store, you can supply the extension ID:
# e.g. $extensionID = "abcdefghijklmnop...some_id..."
# If it's a developer/unpacked extension, there's no official "uninstall" from CLI.
$extensionID = "YOUR_STORE_EXTENSION_ID_HERE"  # If store-based

if ($extensionID -ne "YOUR_STORE_EXTENSION_ID_HERE") {
    # Attempt an uninstall command
    # Warning: This might fail silently if extension isn't found or if
    # the extension was installed in developer mode/unpacked
    Write-Host "Using Chrome CLI to uninstall extension ID: $extensionID"

    # Locate Chrome
    $chromePaths = @(
        "C:\Program Files\Google\Chrome\Application\chrome.exe",
        "C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"
    )
    $chromeExe = $chromePaths | Where-Object { Test-Path $_ } | Select-Object -First 1

    if ($chromeExe) {
        Start-Process $chromeExe -ArgumentList "--uninstall-extension=$extensionID","--user-data-dir=$($env:TEMP)\ChromeCleanProfile","--no-first-run" -Wait
    } else {
        Write-Host "Chrome was not found in default locations; skipping uninstall step."
    }
} else {
    Write-Host "No extension ID specified (or dev-mode extension). Skipping direct uninstall."
}

###############################################################################
# 8. Kill Chrome (if open) and Load/Reinstall FinGPT extension
###############################################################################
Write-Host "`nAttempting to close Chrome if running..."
Stop-Process -Name chrome -Force -ErrorAction SilentlyContinue
Write-Host "Chrome closed (or was not running)."

Write-Host "`nLoading FinGPT extension in Chrome..."
$extensionPath = Join-Path $PSScriptRoot "ChatBot-Fin\Extension-ChatBot-Fin\src"
if (!(Test-Path $extensionPath)) {
    Write-Host "ERROR: Extension source folder not found at $extensionPath"
    exit 1
}

# Locate Chrome again
$chromePaths = @(
    "C:\Program Files\Google\Chrome\Application\chrome.exe",
    "C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"
)
$chromeExe = $chromePaths | Where-Object { Test-Path $_ } | Select-Object -First 1

if (-not $chromeExe) {
    Write-Host "ERROR: Google Chrome not found in default locations."
    Write-Host "Please install Chrome or update the paths in this script."
    exit 1
}

Start-Process $chromeExe --load-extension=$extensionPath

Write-Host "`n========== FinGPT Installation Complete =========="
Write-Host "The Django server is running in a separate PowerShell window."
Write-Host "Chrome has been launched with the FinGPT extension loaded."
Write-Host "If you encountered any issues with port 8000 or existing processes,"
Write-Host "please address them and rerun this script."
