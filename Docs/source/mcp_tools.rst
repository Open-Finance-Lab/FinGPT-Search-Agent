MCP Tools Integration
=====================

FinGPT Search Agent leverages the **Model Context Protocol (MCP)** to provide advanced financial capabilities through specialized tools.

Available MCP Servers
---------------------

1. **SEC-EDGAR Server**
   - **Purpose**: Access official SEC filings (10-K, 10-Q, 8-K).
   - **Features**: Search by ticker, retrieve filing summaries, and extract financial statements.
   - **Automatic Activation**: Triggered when you ask questions about company filings or historical data.

2. **Yahoo Finance Server**
   - **Purpose**: Real-time market data and historical price analysis.
   - **Features**: Get current stock prices, volume, and company profiles.
   - **Automatic Activation**: Used for stock price queries and basic market research.

How to Enable
-------------

MCP tools are enabled by default for compatible models (OpenAI/Anthropic). Ensure your ``.env`` file in ``Main/backend/`` is properly configured:

.. code-block:: bash

   # Required for OpenAI MCP
   OPENAI_API_KEY=your_key_here

   # Optional config for specific tools
   # SEC_EDGAR_API_KEY=... (if required)

Using MCP Tools
---------------

You don't need to manually activate tools. Simply ask questions like:

- *"What were Apple's key risk factors in their latest 10-K?"*
- *"Show me the current price and volume for NVDA."*
- *"Compare the revenue growth of Tesla and Rivian from their last three filings."*

The agent will automatically determine which MCP tool is best suited to answer your query.
