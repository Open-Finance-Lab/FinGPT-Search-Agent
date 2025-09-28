File Structure
=================

This document provides high-level structure and basic details about the project structure.

Top-Level Layout
----------------

.. code-block:: text

    fingpt_rcos/                  # Project root
    ├── Makefile                  # Unix-style build commands
    ├── make.ps1                  # Windows PowerShell equivalent
    ├── pyproject.toml            # Root Poetry configuration
    ├── scripts/                  # Monorepo management
    │   ├── install_all.py        # Unified installer (UTF-8 compatible)
    │   ├── dev_setup.py          # Development runner
    │   ├── export_requirements.py # Requirements export helper
    │   └── fix_dependencies.py   # Dependency troubleshooting
    ├── Main/
    │   ├── backend/
    │   │   ├── django_config/        # Django project settings
    │   │   ├── api/                  # Django app & APIs
    │   │   ├── datascraper/          # RAG & scraping utilities
    │   │   ├── mcp_client/           # MCP integration
    │   │   ├── pyproject.toml        # Backend Poetry config
    │   │   ├── manage_deps.py        # Dependency helper
    │   │   ├── export_requirements.py # Platform-specific export
    │   │   └── .env                  # API keys (git-ignored)
    │   └── frontend/                 # Browser extension
    │       ├── dist/                 # Built extension
    │       ├── node_modules/         # npm packages
    │       └── src/                  # Source code
    ├── mcp-server/                   # MCP server implementation
    │   ├── server.py                 # Main MCP server
    │   └── pyproject.toml            # MCP dependencies
    └── Requirements/                 # Exported dependencies
        ├── requirements_win.txt      # Windows packages
        └── requirements_mac.txt      # macOS packages

Backend (`Main/backend/`)
-------------------------

Django Configuration (`django_config/`)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. note::
   Previously named ``chat_server/``, this directory contains Django project settings.

+--------------+-----------------------------------------------------------+
| **File**     | **Purpose**                                               |
+==============+===========================================================+
| asgi.py      | ASGI entry-point for WebSocket & async support            |
+--------------+-----------------------------------------------------------+
| settings.py  | Central Django configuration (INSTALLED_APPS, CORS, etc.) |
+--------------+-----------------------------------------------------------+
| urls.py      | Global URL dispatcher routing to API endpoints            |
+--------------+-----------------------------------------------------------+
| wsgi.py      | WSGI entry-point for traditional sync servers             |
+--------------+-----------------------------------------------------------+

API Application (`api/`)
~~~~~~~~~~~~~~~~~~~~~~~~

.. note::
   Replaces the legacy ``chat_server_app/`` directory.

+--------------------------------------+----------------------------------------------------------------------------------------+
| **Item**                             | **Purpose**                                                                            |
+======================================+========================================================================================+
| apps.py                              | Django app configuration with fail-fast API key validation:                            |
|                                      | - Checks for valid API keys on server startup                                          |
|                                      | - Raises ``ImproperlyConfigured`` if no keys found                                     |
|                                      | - Prevents server from starting without configuration                                  |
+--------------------------------------+----------------------------------------------------------------------------------------+
| views.py                             | Main API endpoints:                                                                    |
|                                      |                                                                                        |
|                                      | - ``/get_chat_response/`` – Basic chat completion                                      |
|                                      | - ``/get_adv_response/`` – Advanced response with RAG                                  |
|                                      | - ``/get_mcp_response/`` – MCP-enabled agent responses                                 |
|                                      | - ``/add_webtext/`` – Append scraped web content                                       |
|                                      | - ``/clear/`` – Clear conversation history                                             |
|                                      | - ``/get_sources/`` – Get RAG sources                                                  |
|                                      | - ``/log_question/`` – Question telemetry                                              |
|                                      | - ``/folder_path/`` – Upload documents for RAG                                         |
+--------------------------------------+----------------------------------------------------------------------------------------+
| questionLog.csv                      | Per-prompt telemetry log (git-ignored)                                                 |
+--------------------------------------+----------------------------------------------------------------------------------------+
| preferred_urls.txt                   | User-curated source URLs                                                               |
+--------------------------------------+----------------------------------------------------------------------------------------+

Data Processing (`datascraper/`)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

+------------------------+--------------------------------------------------------------------------------------------+
| **Script**             | **Responsibility**                                                                         |
+========================+============================================================================================+
| datascraper.py         | Core module integrating multiple LLMs (OpenAI, DeepSeek, Anthropic)                        |
+------------------------+--------------------------------------------------------------------------------------------+
| models_config.py       | Centralized configuration for all supported AI models                                      |
+------------------------+--------------------------------------------------------------------------------------------+
| cdm_rag.py             | RAG implementation using FAISS for vector similarity search                                |
+------------------------+--------------------------------------------------------------------------------------------+
| create_embeddings.py   | Creates embeddings using OpenAI's text-embedding-3-large model                             |
+------------------------+--------------------------------------------------------------------------------------------+
| embeddings.pkl         | Stored document embeddings (git-ignored)                                                   |
+------------------------+--------------------------------------------------------------------------------------------+
| faiss_index.idx        | FAISS vector index for efficient similarity search (git-ignored)                           |
+------------------------+--------------------------------------------------------------------------------------------+

MCP Integration (`mcp_client/`)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

+------------------------+--------------------------------------------------------------------------------------------+
| **File**               | **Purpose**                                                                                |
+========================+============================================================================================+
| agent.py               | Creates financial agents with MCP server integration                                       |
|                        | - Async context manager for connection handling                                            |
|                        | - Integrates with external MCP servers for tool access                                     |
+------------------------+--------------------------------------------------------------------------------------------+

Dependency Management
~~~~~~~~~~~~~~~~~~~~~

The backend uses **Poetry** for modern Python dependency management with platform-specific support:

+------------------------+--------------------------------------------------------------------------------------------+
| **File/Tool**          | **Purpose**                                                                                |
+========================+============================================================================================+
| pyproject.toml         | Poetry configuration with platform-specific dependencies:                                  |
|                        | - Django 5.1.11 (Windows)                                                                  |
|                        | - Django 4.2.23 (macOS/Linux)                                                              |
|                        | - Package mode disabled (no README.md required)                                            |
+------------------------+--------------------------------------------------------------------------------------------+
| poetry.lock            | Lock file ensuring reproducible builds (git-ignored)                                       |
+------------------------+--------------------------------------------------------------------------------------------+
| manage_deps.py         | Helper script for Poetry operations:                                                       |
|                        | - ``python manage_deps.py install``                                                        |
|                        | - ``python manage_deps.py add <package>``                                                  |
|                        | - ``python manage_deps.py export``                                                         |
+------------------------+--------------------------------------------------------------------------------------------+
| export_requirements.py | Exports platform-specific requirements files from Poetry                                   |
+------------------------+--------------------------------------------------------------------------------------------+

Model Configuration
~~~~~~~~~~~~~~~~~~~

The backend supports multiple AI providers through a centralized configuration:

**Supported Models:**
- OpenAI: GPT-4o Mini (o4-mini), O1 Pro (o1-pro), GPT-5 Chat Latest (gpt-5-chat), GPT-5 Nano (gpt-5-nano)
- DeepSeek: DeepSeek R1 Reasoner (deepseek-reasoner)
- Anthropic: Claude 4 Sonnet (claude-4-sonnet), Claude 3.5 Haiku (claude-haiku-3.5)

**Model Capabilities:**
- Basic chat completion
- RAG (Retrieval-Augmented Generation) support
- MCP (Model Context Protocol) integration
- Advanced reasoning features

Frontend (`Main/frontend/`)
---------------------------

Frontend file structure:

.. code-block:: text

    frontend/
    ├── dist/               # Compiled bundle – Chrome extension files
    ├── src/
    │   ├── main.js         # Extension bootstrapper
    │   ├── manifest.json   # Chrome extension manifest (permissions, icons)
    │   └── modules/        # Feature-specific modules
    │       ├── api.js      # Backend API communication
    │       ├── components/ # UI components (chat, header, popup)
    │       ├── handlers.js # Event handlers
    │       ├── helpers.js  # Utility functions
    │       ├── styles/     # Component-specific CSS
    │       └── ui.js       # UI management
    ├── webpack.config.js   # Webpack bundler configuration
    ├── babel.config.json   # Babel transpiler settings
    └── package.json        # npm dependencies and scripts

Build System
~~~~~~~~~~~~

+---------------------+------------------------------------------------+
| **Tool**            | **Purpose**                                    |
+=====================+================================================+
| Webpack             | Bundles ES modules for browser compatibility   |
+---------------------+------------------------------------------------+
| Babel               | Transpiles modern JavaScript to ES2018         |
+---------------------+------------------------------------------------+
| npm scripts         | Build commands:                                |
|                     | - ``build`` – Standard webpack build           |
|                     | - ``build:full`` – Build with CSS & validation |
|                     | - ``watch`` – Auto-rebuild on changes          |
+---------------------+------------------------------------------------+

Development Workflow
--------------------

Quick Start
~~~~~~~~~~~

1. **Installation:**

   - All platforms: ``python scripts/install_all.py`` (or ``python3`` on Mac/Linux)
   - Windows with make: ``./make.ps1 install``
   - Mac/Linux with make: ``make install``

2. **Development mode:**

   .. code-block:: bash

      # Using make (Mac/Linux)
      make dev

      # Using PowerShell (Windows)
      .\make.ps1 dev

      # Direct Python
      python scripts/dev_setup.py

3. **Load extension:**

   - Navigate to ``chrome://extensions``
   - Enable Developer mode
   - Load unpacked → select ``Main/frontend/dist``

Key Scripts
~~~~~~~~~~~

**Installation & Setup:**

- ``scripts/install_all.py`` – Unified installer with UTF-8 support for all languages
  - Prompts for API key configuration before allowing server start
  - Checks for valid API keys (not placeholders)
  - Only offers to start dev server if keys are configured
- ``scripts/dev_setup.py`` – Runs both backend and frontend in development mode
  - Verifies API keys are configured before starting
  - Shows which API keys are available
  - Refuses to start without at least one valid key
- ``scripts/fix_dependencies.py`` – Troubleshoots missing dependencies

**Dependency Management:**

- ``make install`` – Install all dependencies
- ``make update`` – Update all packages
- ``make export-reqs`` – Export platform-specific requirements

**Development:**

- ``make dev`` – Start development servers
- ``make build`` – Build frontend for production
- ``make clean`` – Clean build artifacts

Environment Variables
~~~~~~~~~~~~~~~~~~~~~

Create ``Main/backend/.env`` with:

.. code-block:: text

    OPENAI_API_KEY=your-api-key-here
    ANTHROPIC_API_KEY=your-anthropic-key-here
    DEEPSEEK_API_KEY=your-deepseek-key-here

.. note::
   The API key was standardized from ``API_KEY7`` to ``OPENAI_API_KEY`` for consistency.