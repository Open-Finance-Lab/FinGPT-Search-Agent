Tutorial: Install with Installer Scripts
========================================

This guide shows how to install FinGPT using the new unified installer scripts that handle both backend and frontend setup automatically.

.. note::
   You will need an OpenAI API key for running the agent. Please ask the project leader (FlyM1ss) via Discord /
   WeChat / Email (felixflyingt@gmail.com) for the key. If you have your own key, the installer will create a ``.env`` 
   file at ``Main\backend\.env`` where you can add it.

.. note::
   The new installers require:
   
   - **Python 3.10+** (3.9 no longer supported due to dependencies)
   - **Node.js 18+** for frontend building
   - **Google Chrome** (default browser, others can be configured manually)

Clone Repository
----------------

Clone the repo into an empty directory of your choice. If you don't know how to clone, follow the guide below.

Recommended Cloning Method: GitHub Desktop
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

1. **Download and Install GitHub Desktop**

    - Visit https://desktop.github.com/ to download the latest version for your operating system.
    - Complete the installation.

2. **Open GitHub Desktop and Sign In**

    - Launch GitHub Desktop and sign in with your GitHub account.

3. **Clone the Repository**

    - In GitHub Desktop, click **File** > **Clone repository...**.
    - Select the **URL** tab and paste:
      ``https://github.com/Open-Finance-Lab/FinGPT-Search-Agent``

    - Choose a local path (an empty directory) where you want to store the project files.
    - Click **Clone**.

4. **Switch to the Correct Branch**

    - In GitHub Desktop, confirm that the repository is open.
    - At the top center of the app, there's a dropdown showing the currently active branch.
    - Select the appropriate branch for your needs.

5. **Verify**

    - Your GitHub Desktop window should now display the selected branch as your active branch.

Install the Agent
-----------------

The new installer system provides multiple ways to install FinGPT, from simple one-click to advanced control.

.. _pop-up-installation:

Windows
~~~~~~~

**Option 1: Quick Installer (Recommended)**

1. Navigate to the project's root folder in File Explorer
2. **Right-click** ``Installer_Win.ps1`` and select **"Run with PowerShell"**

The installer will:
  - Check prerequisites (Python 3.10+, Node.js 18+)
  - Run the unified installation system
  - Create a ``.env`` file template
  - Offer to start development mode

If you encounter permission issues::

    powershell.exe -ExecutionPolicy Bypass -File .\Installer_Win.ps1

**Option 2: PowerShell Make Commands**

For more control, use the PowerShell make script::

    # See all available commands
    .\make.ps1 help
    
    # Install everything
    .\make.ps1 install
    
    # Start development servers
    .\make.ps1 dev
    
    # Clean and rebuild
    .\make.ps1 clean
    .\make.ps1 build

**Option 3: Direct Python Scripts**

Run the unified installer directly::

    python scripts\install_all.py
    python scripts\dev_setup.py

Mac
~~~

**Option 1: Quick Installer (Recommended)**

1. Open Terminal and navigate to the project's root folder
2. Make the script executable and run it::

    chmod +x Installer_Mac.sh
    ./Installer_Mac.sh

The installer will:
  - Check prerequisites (Python 3.10+, Node.js 18+)
  - Run the unified installation system
  - Create a ``.env`` file template
  - Offer to start development mode

**Option 2: Make Commands**

If you have ``make`` installed::

    # See all available commands
    make help
    
    # Install everything
    make install
    
    # Start development servers
    make dev
    
    # Clean and rebuild
    make clean
    make build

**Option 3: Direct Python Scripts**

Run the unified installer directly::

    python3 scripts/install_all.py
    python3 scripts/dev_setup.py

Post-Installation Setup
~~~~~~~~~~~~~~~~~~~~~~~

1. **Configure API Key**

   Edit ``Main/backend/.env`` and add your OpenAI API key::
   
       OPENAI_API_KEY=your-actual-api-key-here

2. **Load Browser Extension**

   - Open Chrome and navigate to ``chrome://extensions``
   - Enable **Developer mode** (toggle in top right)
   - Click **Load unpacked**
   - Select ``Main/frontend/dist`` folder
   - The FinGPT icon should appear in your extensions

3. **Start Using FinGPT**

   - Navigate to any supported financial website
   - The FinGPT chat interface should appear automatically
   - Start asking questions!

Development Mode
~~~~~~~~~~~~~~~~

The new system includes a development mode that runs both servers concurrently:

**Windows**::

    .\make.ps1 dev

**Mac/Linux**::

    make dev
    # or
    python3 scripts/dev_setup.py

This will:
- Start the Django backend server on port 8000
- Start the frontend build watcher (if configured)
- Show combined logs from both servers
- Handle graceful shutdown with Ctrl+C

Troubleshooting
~~~~~~~~~~~~~~~

**Installation Issues**

- **"Python not found"**: Install Python 3.10+ from https://www.python.org/downloads/
- **"Node.js not found"**: Install Node.js 18+ from https://nodejs.org/
- **"make not found" (Windows)**: Use ``.\make.ps1`` instead
- **Port 8000 in use**: Close other servers or choose to continue anyway
- **Poetry errors**: Run ``pip install poetry`` in your virtual environment
- **"No module named corsheaders"**: Run ``pip install django-cors-headers``

**Character Encoding Issues (Non-English Systems)**

- **Emoji display errors**: The scripts now use plain text instead of emojis
- **UTF-8 errors**: All scripts automatically set UTF-8 encoding
- **npm build errors on Chinese/Japanese systems**: Fixed with proper encoding

**Extension Issues**

- **Extension doesn't appear**: Ensure you selected the ``dist`` folder, not ``src``
- **Agent doesn't pop up**: Check that the backend server is running
- **API errors**: Verify your API key in ``Main/backend/.env``
- **CORS errors**: Ensure django-cors-headers is installed

**Development Server Issues**

- **Backend ModuleNotFoundError**: The dev script now uses the correct Python from venv
- **Frontend "file not found"**: Uses shell=True on Windows to find npm
- **"Export requirements error"**: Fixed with new export_requirements.py script

**For Developers**

The new monorepo setup includes:

- ``Makefile`` - Unix-style commands
- ``make.ps1`` - Windows PowerShell equivalent  
- ``scripts/install_all.py`` - Unified Python installer
- ``scripts/dev_setup.py`` - Development mode runner
- ``MONOREPO_SETUP.md`` - Detailed documentation

See ``make help`` or ``.\make.ps1 help`` for all available commands.