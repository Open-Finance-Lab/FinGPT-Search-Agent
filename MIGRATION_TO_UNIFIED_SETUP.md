# Migration Guide: Old Installers to New Unified Setup

This guide helps existing FinGPT users migrate from the old installation system to the new unified monorepo setup.

## What's Changed

### Old System
- Separate complex installer scripts for Windows and Mac
- Manual dependency management
- Multiple steps for backend and frontend setup
- No unified development mode

### New System
- Simplified quick installers that use unified scripts
- Poetry-based dependency management with automatic exports
- Single command installation for everything
- Integrated development mode for both servers
- PowerShell make.ps1 for Windows (no make.exe needed)

## Migration Steps

### 1. Update Your Repository

```bash
git pull origin main
# or your current branch
```

### 2. Clean Old Installation (Optional)

If you want a fresh start:

**Windows:**
```powershell
# Remove old virtual environment
Remove-Item -Recurse -Force FinGPTenv

# Clean Python cache
Get-ChildItem -Path . -Include __pycache__ -Recurse | Remove-Item -Recurse -Force
```

**Mac/Linux:**
```bash
# Remove old virtual environment
rm -rf FinGPTenv

# Clean Python cache
find . -type d -name "__pycache__" -exec rm -rf {} +
```

### 3. Use New Installation

**Windows:**
```powershell
# Quick install
.\Installer_Win.ps1

# Or use make.ps1
.\make.ps1 install
```

**Mac/Linux:**
```bash
# Quick install
./Installer_Mac.sh

# Or use make
make install
```

## Key Differences for Developers

### Dependency Management

**Old way:**
- Edit requirements_win.txt or requirements_mac.txt manually
- Run pip install -r Requirements/requirements_*.txt

**New way:**
```bash
# Add a package
cd Main/backend
poetry add package-name

# Export to requirements files
poetry run export-requirements
```

### Running Development Servers

**Old way:**
- Open multiple terminals
- Start backend: `python manage.py runserver`
- Build frontend: `npm run build:full`

**New way:**
```bash
# Windows
.\make.ps1 dev

# Mac/Linux
make dev
```

### Building Frontend Only

**Old way:**
```bash
cd Main/frontend
npm install
npm run build:full
```

**New way:**
```bash
# Windows
.\make.ps1 build

# Mac/Linux
make build
```

## New Features Available

1. **Unified Commands**: See all available commands with `make help` or `.\make.ps1 help`

2. **Development Mode**: Both servers run together with combined logging

3. **Automatic Dependency Export**: Poetry manages platform-specific dependencies

4. **Clean Command**: `make clean` removes all build artifacts

5. **Update Command**: `make update` updates all dependencies

## Troubleshooting Migration

### "make not found" on Windows
Use `.\make.ps1` instead - it's a PowerShell equivalent that doesn't require installing make.

### Virtual Environment Issues
The new system will detect existing FinGPTenv and use it. If you have issues, remove it and let the installer create a fresh one.

### Poetry Not Found
Install Poetry in your virtual environment:
```bash
pip install poetry
```

### Old Dependencies Conflicting
Run a clean install:
```bash
# Windows
.\make.ps1 clean
.\make.ps1 install

# Mac/Linux
make clean
make install
```

## Benefits of Upgrading

1. **Faster Setup**: One command installs everything
2. **Easier Development**: No need to manage multiple terminals
3. **Better Dependency Management**: Poetry handles conflicts automatically
4. **Cross-Platform Consistency**: Same commands work everywhere
5. **Future-Proof**: Ready for CI/CD and automated deployments

## Need Help?

- Run `make help` or `.\make.ps1 help` for command reference
- Check `MONOREPO_SETUP.md` for detailed documentation
- Review updated installer scripts for platform-specific details