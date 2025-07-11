.. FinGPT Search Agent documentation master file, created by
   sphinx-quickstart on Sun Mar  9 21:31:47 2025.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

FinGPT Search Agent
===================

**FinGPT Search Agent** is a powerful browser extension that combines financial information retrieval with advanced AI capabilities. It provides real-time access to financial data, documents, and insights through an intuitive chat interface.

.. note::
   This documentation covers version 0.5.1 of FinGPT Search Agent.

Features
--------

- **Multi-Model Support**: Choose between OpenAI (GPT-4, GPT-3.5), DeepSeek, and Anthropic (Claude) models
- **RAG Integration**: Retrieval-Augmented Generation for accurate, source-backed responses
- **MCP Support**: Model Context Protocol integration for enhanced agent capabilities
- **Browser Extension**: Seamless integration with major financial websites
- **Local Document Processing**: Upload and analyze your own financial documents
- **Real-time Web Scraping**: Extract and analyze content from financial websites

Quick Start
-----------

1. Install using the unified installer: ``python scripts/install_all.py``
2. Configure your API keys in ``Main/backend/.env``
3. Start the development server: ``make dev`` or ``python scripts/dev_setup.py``
4. Load the extension in your browser from ``Main/frontend/dist``
5. Navigate to any supported financial website and start chatting!


.. toctree::
   :maxdepth: 2
   :caption: Contents:

   introduction
   install_agent_with_installer
   manual_install
   start_agent_mac
   start_agent_win
   usage/index
   project_structure
