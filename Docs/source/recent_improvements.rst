Recent Improvements
===================

This document outlines the recent improvements made to the FinGPT project infrastructure.

API Key Standardization
-----------------------

**Previous**: The system used ``API_KEY7`` as the environment variable name.

**Current**: Standardized to ``OPENAI_API_KEY`` for consistency with industry conventions.

**Files Updated**:

- ``Installer_Win.ps1``
- ``scripts/install_all.py``
- ``Docs/source/installer_agent_install.rst``
- ``MONOREPO_SETUP.md``

Unicode and Language Support
----------------------------

**Issue**: Scripts failed on non-English systems (Chinese, Japanese, etc.) due to character encoding issues.

**Solution**: 

- Removed all emoji characters from output
- Added UTF-8 encoding throughout all scripts
- Set proper environment variables for subprocess calls
- Added ``chcp 65001`` for Windows console UTF-8 support

**Affected Scripts**:

- ``scripts/install_all.py``
- ``scripts/dev_setup.py``
- ``Installer_Win.ps1``
- ``Installer_Mac.sh``

Django Version Alignment
------------------------

**Issue**: Version mismatch between pyproject.toml and requirements files.

**Solution**: Updated requirements files to match pyproject.toml:

- Windows: Django 5.1.11
- Mac/Linux: Django 4.2.23

Poetry Integration Improvements
-------------------------------

**Issue**: Poetry installation failed due to missing README.md reference.

**Solution**: 

- Set ``package-mode = false`` in backend's pyproject.toml
- Updated Poetry install commands to use ``--no-root``
- Created dedicated ``export_requirements.py`` script

Development Server Enhancements
-------------------------------

**Issue**: Backend failed with "ModuleNotFoundError: No module named corsheaders" when run via dev_setup.py.

**Solution**:

- Script now uses ``sys.executable`` to ensure correct Python interpreter
- Added automatic dependency checking and installation
- Improved error detection and reporting
- Added debug output showing Python version and virtual environment

**New Features**:

- Automatic django-cors-headers installation
- Better subprocess error handling
- Clear indication of which Python is being used

Export Requirements Fix
-----------------------

**Issue**: "Warning: 'export-requirements' is an entry point defined in pyproject.toml"

**Solution**:

- Created standalone ``export_requirements.py`` script
- Updated ``manage_deps.py`` to call the script directly
- Properly exports platform-specific requirements

Monorepo Documentation
----------------------

**New Documentation**:

- Updated ``project_structure.rst`` with current backend structure
- Added details about MCP integration
- Documented all new Poetry-related files
- Added model configuration section
- Updated development workflow instructions

Helper Scripts
--------------

**New Scripts Added**:

1. ``scripts/fix_dependencies.py`` - Quickly install missing dependencies
2. ``Main/backend/export_requirements.py`` - Export platform-specific requirements
3. Updated ``make.ps1`` with better error handling

Backend Structure Updates
-------------------------

**Documented Changes**:

- ``django_config/`` - Renamed from ``chat_server/``
- ``api/`` - Replaced ``chat_server_app/``
- ``mcp_client/`` - New MCP integration module
- ``models_config.py`` - Centralized AI model configuration
- Support for multiple AI providers (OpenAI, DeepSeek, Anthropic)

These improvements make the project more robust, easier to install across different systems, and better documented for future development.