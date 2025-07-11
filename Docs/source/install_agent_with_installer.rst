Tutorial: Install with Unified Installer
========================================

This guide shows how to install FinGPT using the unified installer that works across MacOS and Windows.

.. note::
   You will need at least one API Key from OpenAI, Anthropic or DeepSeek for running the agent. Please ask the project
   leader (FlyM1ss) via Discord / WeChat / Email (felixflyingt@gmail.com) for the key(s). If you have your own key, the
   installer will create a ``.env`` file at ``Main\backend\.env`` where you can add it.
   Note, that the MCP function currently only supports OpenAI models, meaning you will need OpenAI API Keys for
   running the MCP function.

.. note::
   The installers require:
   
   - **Python 3.10+** (3.9 no longer supported due to dependencies)
   - **Node.js 18+** for frontend building
   - **Google Chrome** (default browser, others can be configured manually)

.. note::
   The search agent currently does NOT support **Brave** browser on this browser's default settings.

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

The unified installer works across all platforms (Windows, macOS, Linux) and handles all system languages properly.

.. _unified-installation:

Option 1: Using Make (macOS/Linux)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

If you have ``make`` installed::

    # Install everything
    make install
    
    # Start development mode
    make dev
    
    # See all available commands
    make help

Option 2: Using PowerShell Make (Windows)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Windows users can use the PowerShell equivalent::

    # Install everything
    .\make.ps1 install
    
    # Start development mode
    .\make.ps1 dev
    
    # See all available commands
    .\make.ps1 help

Option 3: Direct Python Installation (All Platforms)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Run the unified installer directly:

**Windows**::

    python scripts\install_all.py
    
**macOS/Linux**::

    python3 scripts/install_all.py

The installer will:

1. Check prerequisites (Python, Node.js)
2. Create a virtual environment (``FinGPTenv``)
3. Install all backend dependencies using Poetry or pip
4. Install all frontend dependencies using npm
5. Build the frontend extension
6. Create a ``.env`` template file
7. **Prompt you to configure API keys before proceeding**
8. Only offer to start the dev server after API keys are configured

Post-Installation Setup
~~~~~~~~~~~~~~~~~~~~~~~

1. **Configure API Key**

   Edit ``Main/backend/.env`` and add your OpenAI API key::
   
       OPENAI_API_KEY=your-actual-api-key-here

   Add your other API keys as needed in the same file and format.

2. **Load Browser Extension**

   - Open Chrome and navigate to ``chrome://extensions``
   - Enable **Developer mode** (toggle in top right)
   - Click **Load unpacked**
   - Select ``Main/frontend/dist`` folder
   - The FinGPT icon should appear in your extensions

3. **Start Using FinGPT**

   - Make sure the FinGPT back-end server is running. You should see the line ``Quit the server with CTRL-BREAK.`` as
     the last line inside the terminal you are running the server from. If it isn't, inside your terminal, cd to the
     root folder of the project and run ``python scripts/dev_setup.py`` or ``python3 scripts/dev_setup.py`` if the former
     doesn't work.

   - Navigate to any supported financial website

   - The FinGPT chat interface should appear automatically

   - Start asking questions!

Development Mode
~~~~~~~~~~~~~~~~

The development mode runs both backend and frontend with hot-reloading:

**Windows**::

    # Using PowerShell make
    .\make.ps1 dev
    
    # Or directly
    python scripts\dev_setup.py

**macOS/Linux**::

    # Using make
    make dev
    
    # Or directly
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
- **Agent doesn't pop up**: Check that your browser and the website are both supported
- **API errors**: Verify your API key in ``Main/backend/.env``
- **CORS errors**: Ensure django-cors-headers is installed

**Development Server Issues**

- **Backend ModuleNotFoundError**: The dev script now uses the correct Python from venv
- **Frontend "file not found"**: Uses shell=True on Windows to find npm
- **"Export requirements error"**: Fixed with new export_requirements.py script

**For Developers**

The monorepo setup includes:

- ``Makefile`` - Unix-style commands
- ``make.ps1`` - Windows PowerShell equivalent  
- ``scripts/install_all.py`` - Unified Python installer (UTF-8 compatible)
- ``scripts/dev_setup.py`` - Development mode runner
- ``MONOREPO_SETUP.md`` - Detailed documentation

See ``make help`` or ``.\make.ps1 help`` for all available commands.