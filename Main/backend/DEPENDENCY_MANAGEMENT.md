# Backend Dependency Management with Poetry

This document explains how to manage Python dependencies for the FinGPT backend using Poetry.

## Overview

The backend now uses Poetry for dependency management, which provides:
- Automatic dependency resolution
- Lock files for reproducible builds
- Platform-specific dependency handling
- Easy package updates and management

## Prerequisites

1. Install Poetry (if not already installed):
   ```bash
   pip install poetry
   ```

2. Ensure you're in the backend directory:
   ```bash
   cd Main/backend
   ```

## Common Tasks

### Installing Dependencies

To install all dependencies in your virtual environment:
```bash
# From Main/backend directory
poetry install
```

Or use the helper script:
```bash
python manage_deps.py install
```

### Adding a New Package

To add a new dependency:
```bash
poetry add package-name

# Or with the helper script:
python manage_deps.py add package-name
```

### Removing a Package

To remove a dependency:
```bash
poetry remove package-name

# Or with the helper script:
python manage_deps.py remove package-name
```

### Updating Packages

To update all packages to their latest compatible versions:
```bash
poetry update

# Or with the helper script:
python manage_deps.py update
```

### Exporting Requirements Files

To generate platform-specific requirements files (requirements_win.txt and requirements_mac.txt):
```bash
poetry run export-requirements

# Or with the helper script:
python manage_deps.py export
```

This will create/update:
- `Requirements/requirements_win.txt` - For Windows
- `Requirements/requirements_mac.txt` - For macOS

## Platform-Specific Dependencies

The `pyproject.toml` file handles platform-specific dependencies using markers:

```toml
# Different Django versions for different platforms
Django = [
    {version = "5.0.11", markers = "sys_platform == 'win32'"},
    {version = "4.2.18", markers = "sys_platform == 'darwin'"},
]

# Mac-only dependency
mammoth = {version = "*", markers = "sys_platform == 'darwin'"}
```

## Integration with Installers

The Windows (`Installer_Win.ps1`) and Mac (`Installer_Mac.sh`) installer scripts automatically:
1. Check if Poetry is available
2. Export updated requirements files if Poetry is detected
3. Install dependencies from the appropriate requirements file

## Virtual Environment

Poetry respects the existing `FinGPTenv` virtual environment. To activate it:
```bash
# Windows
FinGPTenv\Scripts\activate

# macOS/Linux
source FinGPTenv/bin/activate
```

## Troubleshooting

1. **Poetry not found**: Install it with `pip install poetry`
2. **Export script fails**: Ensure you're in the backend directory with pyproject.toml
3. **Dependencies conflict**: Run `poetry lock --no-update` to resolve

## For Developers

When adding new dependencies:
1. Add them using `poetry add <package>`
2. Run `poetry run export-requirements` to update requirements files
3. Commit both `pyproject.toml`, `poetry.lock`, and updated requirements files