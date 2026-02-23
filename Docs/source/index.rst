FinGPT Search Agent
===================

**FinGPT Search Agent** is a powerful browser extension that combines financial information retrieval with advanced AI capabilities. It provides real-time access to financial data, documents, and insights through an intuitive chat interface.

.. toctree::
   :maxdepth: 3
   :caption: Contents:

   introduction
   updates
   install_agent_with_installer
   manual_install
   start_agent_mac
   start_agent_win
   usage/index
   api_reference
   mcp_tools
   project_structure
   case_studies
   code_of_conduct

.. note::
   This documentation covers version 0.10.1 of FinGPT Search Agent.
   
   **New in 0.10.1:**
   
   - **MCP Tool Integration**: Built-in support for SEC-EDGAR and Yahoo Finance tools.
   - **Performance Improvements**: Unified context manager for faster response times.
   - **Modern Workflow**: Fully migrated to ``uv`` and ``bun`` for optimized development.

Features
--------

- **Multi-Model Support**: Choose between OpenAI (GPT-4, GPT-3.5), DeepSeek, and Anthropic (Claude) models
- **MCP Support**: Model Context Protocol integration for enhanced agent capabilities
- **Browser Extension**: Seamless integration with major financial websites
- **Real-time Web Scraping**: Extract and analyze content from financial websites

Quick Start (Docker)
--------------------

The simplest way to get started is using Docker:

1. Clone the repository and navigate to the project root.
2. Copy ``Main/backend/.env.example`` to ``Main/backend/.env`` and add your API keys.
3. Start the application:

   .. code-block:: bash

      docker compose up --build

4. Load the extension in your browser from the ``Main/frontend/dist`` directory.
5. Navigate to any supported financial website and start chatting!

Manual Installation
-------------------

For developers who wish to run or modify the agent outside of Docker, please refer to:

* :doc:`manual_install`: Detailed steps for manual backend setup using ``uv``.
* :doc:`project_structure`: Overview of the codebase and frontend build process.
