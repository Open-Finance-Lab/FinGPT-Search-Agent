
.. admonition:: When to use this section
   :class: note

   Please make sure the search agent is successfully installed
   and running before testing out any of the examples below!

.. note::
   As a reminder, the search agent currently does NOT work on **Brave** browser.

Multi-Model Support
-------------------

FinGPT Search Agent supports multiple foundation models.

Available Models
~~~~~~~~~~~~~~~~

**Supported Models:**
- **FinGPT-Light**: Fast and efficient light-weight model.
- **FinGPT**: State-of-the-art financial model.
- **Buffet-Agent**: The minds of Warren Buffet, in the palm of your hands.

Switching Models
~~~~~~~~~~~~~~~~

1. Click the **Settings** button in the agent popup.
2. Select your preferred model from the dropdown.
3. The agent will use the selected model for all subsequent queries.

MCP (Model Context Protocol) Integration
----------------------------------------

MCP enables advanced agent capabilities through tool integration.

MCP Features
~~~~~~~~~~~~

- **Yahoo Finance MCP**: Directly fetches real-time information via the ``yfinance API``.
- **SEC-EDGAR MCP**: Enables the agent to directly access SEC filings like 10-K, 10-Q, 8-K, etc and even extract data from them.

Custom URL Preferences
----------------------

Configure preferred financial websites for the agent to search.

Setting Preferred URLs
~~~~~~~~~~~~~~~~~~~~~~

1. Open **Settings**
2. Navigate to **Preferred Links**
3. Add URLs of trusted financial sources
4. Save your preferences

The agent will prioritize these sources when using **Advanced Ask**.

Example preferred URLs:

- ``https://www.sec.gov/edgar``
- ``https://investor.apple.com``
- ``https://www.federalreserve.gov``

Advanced Query Techniques
-------------------------

Query Modes
~~~~~~~~~~~

**Basic Ask:**
- Searches only the current webpage
- Faster responses
- Best for page-specific questions

**Advanced Ask:**
- Mainly searches the open domain
- More comprehensive responses
- Best for research and analysis

Effective Prompting
~~~~~~~~~~~~~~~~~~~

For best results:

1. **Be Specific**: "What was Apple's Q3 2024 revenue?" vs "Tell me about Apple"
2. **Request Sources**: Add "with sources" to get citations
3. **Compare Data**: "Compare Tesla's P/E ratio to industry average"
4. **Time-bound Queries**: Include dates for historical data

Monitoring Agent Activity
-------------------------

Real-time Logs
~~~~~~~~~~~~~~

If you are running the agent locally, monitor the agent's search and scraping activity:

1. Inside your terminal and / or browser Dev Tool (console), watch for:
   
   - MCP status
   - URLs being scraped
   - Search queries executed
   - Model API calls
   - Citations if using advanced ask
   - Error messages

Debug Mode
~~~~~~~~~~

For troubleshooting:

.. code-block:: bash

   # Set debug environment variable
   export DJANGO_DEBUG=True
   
   # Then restart the backend server via docker, uv or python

Performance Optimization
------------------------

Smart Context Management
~~~~~~~~~~~~~~~~~~~~~~~~

FinGPT includes production-grade memory powered by **Mem0**:

**How it works:**

- **Session-Based**: The agent maintains the full conversation history for the current session.
- **Smart Compression**: When the context exceeds **100,000 tokens**, the agent automatically extracts key facts, entities, and research findings into long-term memory.
- **Fact Preservation**: Critical financial data, URLs, and research objectives are preserved while redundant boilerplate is discarded.
- **Session Isolation**: Each browser tab/session maintains its own isolated context.

.. note::
   Each browser tab maintains its own conversation context. Refreshing the page starts a new session unless a custom session ID is used.

Troubleshooting Advanced Features
---------------------------------

Common Issues
~~~~~~~~~~~~~

**MCP features not working:**

- Confirm OpenAI API key is valid
- Check you're using an MCP-compatible model
- Monitor terminal for MCP-related errors. If errors directly from the MCPs exist, contact Felix via Discord or WeChat.

**Slow responses with Advanced Ask:**

- Reduce number of preferred URLs
- Check internet connection
- Well it is simply just slow because it's usually searches at least 10 different sources, so it takes a while to scrape and process all of them.
