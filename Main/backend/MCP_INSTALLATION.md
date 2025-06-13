# MCP Package Installation Guide

## The Problem

The `mcp[cli]` package has special characters (brackets) that cause issues with `pip install -r requirements.txt` on macOS/Linux. While the package needs to be written as `mcp[cli]` in requirements files, it requires shell escaping when installing directly.

## Solutions

### Option 1: Use Poetry (Recommended)

Poetry handles the `mcp[cli]` dependency correctly:

```bash
cd Main/backend
poetry install
```

This will install all dependencies including `mcp[cli]` without any issues.

### Option 2: Manual Installation After Requirements

If using pip with requirements files:

```bash
# First, install from requirements (without mcp[cli])
pip install -r Requirements/requirements_mac.txt

# Then, manually install mcp[cli] with proper escaping
pip install 'mcp[cli]'
```

### Option 3: Update Installer Scripts

The installer scripts can handle this automatically. They already install from requirements.txt and could add an additional step:

**For Mac (Installer_Mac.sh):**
```bash
# After installing from requirements
pip install 'mcp[cli]'
```

**For Windows (Installer_Win.ps1):**
```powershell
# After installing from requirements
pip install mcp[cli]
```

Note: Windows PowerShell doesn't require escaping for brackets.

## Poetry Export Consideration

When Poetry exports to requirements.txt, it writes `mcp[cli]` without quotes, which can cause the same issue. The export script may need to handle this specially or document the manual installation step.