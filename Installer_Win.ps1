# FinGPT Quick Installer for Windows
# Simplified installer that uses the new monorepo setup
# Usage: Right-Click -> "Run with PowerShell" from the root folder

# Set UTF-8 encoding for proper language support
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8

#-------------------#
# Helper Functions  #
#-------------------#
Function PressAnyKeyToExit ([int]$exitCode = 0) {
    Write-Host "`nPress any key to exit..."
    [void][System.Console]::ReadKey($true)
    exit $exitCode
}

Write-Host "`n========== FinGPT Quick Installer for Windows ==========" -ForegroundColor Cyan
Write-Host "This installer will set up FinGPT using the unified build system.`n" -ForegroundColor Gray

###############################################################################
# 1. Check Prerequisites
###############################################################################
Write-Host "Checking prerequisites..." -ForegroundColor Yellow

# Check Python
$python = Get-Command python -ErrorAction SilentlyContinue
if (-not $python) {
    Write-Host "ERROR: Python is not installed." -ForegroundColor Red
    Write-Host "   Please install Python 3.10+ from https://www.python.org/downloads/"
    PressAnyKeyToExit 1
}
Write-Host "OK: Python found: $($python.Source)" -ForegroundColor Green

# Check Node.js
$node = Get-Command node -ErrorAction SilentlyContinue
if (-not $node) {
    Write-Host "ERROR: Node.js is not installed." -ForegroundColor Red
    Write-Host "   Please install Node.js 18+ from https://nodejs.org/"
    PressAnyKeyToExit 1
}
$nodeVersion = & node --version 2>&1
Write-Host "OK: Node.js found: $nodeVersion" -ForegroundColor Green

# Check port 8000
$portInUse = $false
try {
    $tcpConnection = New-Object System.Net.Sockets.TcpClient
    $tcpConnection.Connect("127.0.0.1", 8000)
    $portInUse = $true
    $tcpConnection.Close()
} catch {
    # Port is free
}

if ($portInUse) {
    Write-Host "WARNING: Port 8000 is in use. Please close any running servers." -ForegroundColor Yellow
    $continue = Read-Host "Continue anyway? (y/n)"
    if ($continue -ne 'y') {
        PressAnyKeyToExit 1
    }
}

###############################################################################
# 2. Run Unified Installer
###############################################################################
Write-Host "`nRunning unified installer..." -ForegroundColor Yellow

# Check if we have the new setup
$makeScript = Join-Path $PSScriptRoot "make.ps1"
$installScript = Join-Path $PSScriptRoot "scripts\install_all.py"

if (Test-Path $makeScript) {
    # Use PowerShell make script
    Write-Host "Using PowerShell build system..." -ForegroundColor Gray
    & $makeScript install
} elseif (Test-Path $installScript) {
    # Use Python installer directly
    Write-Host "Using Python installer..." -ForegroundColor Gray
    # Set environment variables for UTF-8
    $env:PYTHONIOENCODING = "utf-8"
    $env:PYTHONUTF8 = "1"
    python $installScript
} else {
    Write-Host "ERROR: New installer scripts not found!" -ForegroundColor Red
    Write-Host "   Please ensure you have the latest version from Git." -ForegroundColor Gray
    PressAnyKeyToExit 1
}

###############################################################################
# 3. Create .env file if needed
###############################################################################
$envPath = Join-Path $PSScriptRoot "Main\backend\.env"
if (!(Test-Path $envPath)) {
    Write-Host "`nCreating .env file..." -ForegroundColor Yellow
    @"
# FinGPT Environment Configuration
# Add your OpenAI API key below:
OPENAI_API_KEY=your-api-key-here

# Optional: Add other API keys
# ANTHROPIC_API_KEY=your-anthropic-key-here
"@ | Out-File -FilePath $envPath -Encoding UTF8
    
    Write-Host "WARNING: Please edit $envPath and add your OpenAI API key!" -ForegroundColor Yellow
}

###############################################################################
# 4. Quick Start Options
###############################################################################
Write-Host "`nInstallation complete!" -ForegroundColor Green
Write-Host "`nQuick start options:" -ForegroundColor Cyan

Write-Host "`n1. Start Development Mode (recommended):" -ForegroundColor Yellow
Write-Host "   .\make.ps1 dev" -ForegroundColor White
Write-Host "   This will start both backend and frontend servers"

Write-Host "`n2. Manual Start:" -ForegroundColor Yellow
Write-Host "   # Terminal 1 - Backend:" -ForegroundColor Gray
Write-Host "   cd Main\backend" -ForegroundColor White
Write-Host "   python manage.py runserver" -ForegroundColor White
Write-Host "   # Terminal 2 - Frontend (optional):" -ForegroundColor Gray
Write-Host "   cd Main\frontend" -ForegroundColor White
Write-Host "   npm run watch" -ForegroundColor White

Write-Host "`n3. Load Extension in Chrome:" -ForegroundColor Yellow
Write-Host "   - Open chrome://extensions" -ForegroundColor White
Write-Host "   - Enable Developer mode" -ForegroundColor White
Write-Host "   - Click 'Load unpacked'" -ForegroundColor White
Write-Host "   - Select: Main\frontend\dist" -ForegroundColor White

Write-Host "`nFor more options, run: .\make.ps1 help" -ForegroundColor Gray

# Optional: Auto-start development mode
Write-Host "`n" -NoNewline
$autoStart = Read-Host "Start development servers now? (y/n)"
if ($autoStart -eq 'y') {
    Write-Host "`nStarting development mode..." -ForegroundColor Green
    & $makeScript dev
}

PressAnyKeyToExit 0