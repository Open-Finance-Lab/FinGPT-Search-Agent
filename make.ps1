# FinGPT PowerShell Build Script
# Alternative to Makefile for Windows users without make

param(
    [Parameter(Position=0)]
    [string]$Task = "help"
)

function Show-Help {
    Write-Host "FinGPT Monorepo Management Commands" -ForegroundColor Cyan
    Write-Host "===================================" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "Setup & Installation:" -ForegroundColor Yellow
    Write-Host "  .\make.ps1 install          - Install all dependencies (backend + frontend)"
    Write-Host "  .\make.ps1 install-backend  - Install only backend dependencies"
    Write-Host "  .\make.ps1 install-frontend - Install only frontend dependencies"
    Write-Host ""
    Write-Host "Development:" -ForegroundColor Yellow
    Write-Host "  .\make.ps1 dev             - Start development servers"
    Write-Host "  .\make.ps1 build           - Build frontend for production"
    Write-Host "  .\make.ps1 clean           - Clean build artifacts and caches"
    Write-Host ""
    Write-Host "Dependency Management:" -ForegroundColor Yellow
    Write-Host "  .\make.ps1 update          - Update all dependencies"
    Write-Host "  .\make.ps1 export-reqs     - Export requirements.txt files"
    Write-Host ""
    Write-Host "Code Quality:" -ForegroundColor Yellow
    Write-Host "  .\make.ps1 test            - Run all tests"
    Write-Host ""
}

function Ensure-Venv {
    param(
        [switch]$Quiet
    )

    $venvPath = Join-Path -Path $PSScriptRoot -ChildPath 'FinGPTenv'
    $activateScript = Join-Path -Path $venvPath -ChildPath 'Scripts\Activate.ps1'

    if ($env:VIRTUAL_ENV) {
        if (-not $Quiet) {
            Write-Host "Using active virtual environment: $env:VIRTUAL_ENV" -ForegroundColor Green
        }
        return $env:VIRTUAL_ENV
    }

    if (-not (Test-Path $venvPath)) {
        if (-not $Quiet) {
            Write-Host "🐍 Creating Python virtual environment (FinGPTenv)..." -ForegroundColor Green
        }
        python -m venv $venvPath
        if ($LASTEXITCODE -ne 0) {
            throw "Failed to create virtual environment at $venvPath"
        }
    }

    if (-not (Test-Path $activateScript)) {
        throw "Activation script not found at $activateScript"
    }

    if (-not $Quiet) {
        Write-Host "🐍 Activating FinGPTenv..." -ForegroundColor Green
    }

    . $activateScript

    if (-not $Quiet) {
        Write-Host "OK: Virtual environment active" -ForegroundColor Green
    }

    return $venvPath
}

function Install-All {
    Write-Host "🚀 Installing all dependencies..." -ForegroundColor Green
    Ensure-Venv
    python scripts/install_all.py
}

function Install-Backend {
    Write-Host "🐍 Installing backend dependencies..." -ForegroundColor Green
    Ensure-Venv
    Push-Location Main\backend
    poetry install
    poetry run export-requirements
    Pop-Location
}

function Install-Frontend {
    Write-Host "🎨 Installing frontend dependencies..." -ForegroundColor Green
    Push-Location Main\frontend
    npm install
    Pop-Location
}

function Build-Frontend {
    Write-Host "🔨 Building frontend..." -ForegroundColor Green
    Push-Location Main\frontend
    npm run build:full
    Pop-Location
}

function Start-Dev {
    Write-Host "🚀 Starting development servers..." -ForegroundColor Green
    Ensure-Venv
    python scripts/dev_setup.py
}

function Clean-Build {
    Write-Host "🧹 Cleaning build artifacts..." -ForegroundColor Green
    
    # Remove Python cache
    Get-ChildItem -Path . -Include __pycache__ -Recurse -Directory | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue
    Get-ChildItem -Path . -Include *.pyc,*.pyo -Recurse -File | Remove-Item -Force -ErrorAction SilentlyContinue
    
    # Remove frontend build
    Remove-Item -Path Main\frontend\dist -Recurse -Force -ErrorAction SilentlyContinue
    Remove-Item -Path Main\frontend\node_modules\.cache -Recurse -Force -ErrorAction SilentlyContinue
    
    # Remove Django artifacts
    Remove-Item -Path Main\backend\db.sqlite3 -Force -ErrorAction SilentlyContinue
    Remove-Item -Path Main\backend\django_debug.log -Force -ErrorAction SilentlyContinue
    
    Write-Host "✅ Clean complete!" -ForegroundColor Green
}

function Update-Dependencies {
    Write-Host "📦 Updating all dependencies..." -ForegroundColor Green
    
    Ensure-Venv
    Push-Location Main\backend
    poetry update
    poetry run export-requirements
    Pop-Location
    
    Push-Location Main\frontend
    npm update
    Pop-Location
}

function Export-Requirements {
    Write-Host "📋 Exporting requirements files..." -ForegroundColor Green
    Ensure-Venv
    Push-Location Main\backend
    poetry run export-requirements
    Pop-Location
}

function Run-Tests {
    Write-Host "🧪 Running tests..." -ForegroundColor Green
    
    Ensure-Venv
    Push-Location Main\backend
    python manage.py test
    Pop-Location
    
    Push-Location Main\frontend
    npm test
    Pop-Location
}

function Setup-Venv {
    Write-Host "🐍 Setting up virtual environment..." -ForegroundColor Green
    Ensure-Venv
    Write-Host "Virtual environment is active in this PowerShell session." -ForegroundColor Green
    Write-Host "Activate again later with: FinGPTenv\Scripts\Activate.ps1"
}

function Quick-Start {
    Write-Host "🎯 Quick start setup..." -ForegroundColor Green
    Setup-Venv
    Write-Host ""
    Write-Host "Next steps:" -ForegroundColor Yellow
    Write-Host "1. Keep this PowerShell window open (FinGPTenv is active)."
    Write-Host "   Need a new shell? Activate with: FinGPTenv\Scripts\Activate.ps1"
    Write-Host "2. Run: .\make.ps1 install"
    Write-Host "3. Add your API key to Main\backend\.env"
    Write-Host "4. Run: .\make.ps1 dev"
}

# Main switch statement
switch ($Task) {
    "help" { Show-Help }
    "install" { Install-All }
    "install-backend" { Install-Backend }
    "install-frontend" { Install-Frontend }
    "build" { Build-Frontend }
    "dev" { Start-Dev }
    "clean" { Clean-Build }
    "update" { Update-Dependencies }
    "export-reqs" { Export-Requirements }
    "test" { Run-Tests }
    "venv" { Setup-Venv }
    "quickstart" { Quick-Start }
    default { 
        Write-Host "Unknown task: $Task" -ForegroundColor Red
        Write-Host ""
        Show-Help
    }
}