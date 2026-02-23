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
   This documentation covers version 0.13.1 of FinGPT Search Agent.
   
   **New in 0.13.1:**
   
   - **API Now Supported**: FinGPT API may now be used. For details, please check the API Doc

   **New in 0.13.0:**

   - **Deep Research Mode**: Multi-step research engine with query decomposition, parallel execution, gap detection, and synthesis.
   - **OpenAI-Compatible API**: RESTful ``/v1/chat/completions`` endpoint for programmatic access.
   - **TradingView MCP**: Real-time technical analysis and screener data via Model Context Protocol.
   - **Gemini Integration**: Google Gemini models supported as foundation model providers.

Features
--------

- **Multi-Model Support**: Choose between OpenAI, Google Gemini, DeepSeek, Anthropic (Claude), and custom fine-tuned models
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
