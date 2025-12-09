
.. admonition:: When to use this section
   :class: note

   Please make sure the search agent is successfully installed
   and running before testing out any of the examples below!

.. note::
   As a reminder, the search agent currently does NOT work on **Brave** browser.
Tutorial: Advanced Usages

.. admonition:: When to use this section
   :class: note

   Please make sure the search agent is successfully installed
   and running before testing out any of the examples below!

.. note::
   As a reminder, the search agent currently does NOT work on **Brave** browser.

Multi-Model Support
-------------------

FinGPT Search Agent supports multiple AI model providers, allowing you to choose the best model for your needs.

Available Models
~~~~~~~~~~~~~~~~

**Supported Models:**
- FinGPT-Light (gpt-5-mini)
- FinGPT (gpt-5.1-chat-latest)
- Buffet-Agent (Custom Model)

Switching Models
~~~~~~~~~~~~~~~~

1. Click the **Settings** button in the agent popup
2. Select your preferred model from the dropdown
3. The agent will use the selected model for all subsequent queries

.. note::
   Different models have different capabilities:
   
   - **FinGPT-Light**: Fast and efficient light-weight model
   - **FinGPT**: State-of-the-art financial model
   - **Buffet-Agent**: Specialized financial reasoning

MCP (Model Context Protocol) Integration
----------------------------------------

MCP enables advanced agent capabilities through tool integration.

Enabling MCP
~~~~~~~~~~~~

1. Ensure you have an OpenAI API key configured
2. Select an MCP-compatible model (currently OpenAI models only)
3. The agent will automatically use MCP tools when beneficial

MCP Features
~~~~~~~~~~~~

- **Enhanced Search**: More sophisticated web searching
- **Tool Usage**: Access to specialized financial tools
- **Multi-step Reasoning**: Complex query resolution

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
- Searches current page + preferred URLs + web search
- More comprehensive responses
- Best for research and analysis

Effective Prompting
~~~~~~~~~~~~~~~~~~~

For best results:

1. **Be Specific**: "What was Apple's Q3 2024 revenue?" vs "Tell me about Apple"
2. **Request Sources**: Add "with sources" to get citations
3. **Compare Data**: "Compare Tesla's P/E ratio to industry average"
4. **Time-bound Queries**: Include dates for historical data

Example Queries
~~~~~~~~~~~~~~~

**Financial Analysis:**

.. code-block:: text

   Analyze Tesla's debt-to-equity ratio over the last 3 years 
   and compare it to other EV manufacturers. Include sources.

**Market Research:**

.. code-block:: text

   What are the key risk factors mentioned in Apple's latest 10-K 
   filing? Summarize in bullet points.

**Technical Analysis:**

.. code-block:: text

   Based on the current chart, identify support and resistance 
   levels for NVDA stock.

Monitoring Agent Activity
-------------------------

Real-time Logs
~~~~~~~~~~~~~~

Monitor the agent's search and scraping activity:

1. Keep your terminal/PowerShell window visible
2. Watch for:
   
   - URLs being scraped
   - Search queries executed
   - Model API calls
   - Error messages

Debug Mode
~~~~~~~~~~

For troubleshooting:

For troubleshooting:

.. code-block:: bash

   # Set debug environment variable
   export DJANGO_DEBUG=True
   
   # Then start the server
   python manage.py runserver

Performance Optimization
------------------------

Tips for Faster Responses
~~~~~~~~~~~~~~~~~~~~~~~~~

1. **Use Basic Ask** for simple, page-specific queries
2. **Limit Preferred URLs** to essential sources
3. **Choose Appropriate Models**:
   
   - FinGPT-Light for quick responses
   - FinGPT for complex analysis
   - Buffet-Agent for specialized reasoning

Managing Context Length
~~~~~~~~~~~~~~~~~~~~~~~

For long conversations:

1. Use the **Clear** button to reset conversation while keeping web content
2. Break complex queries into smaller parts
3. Summarize previous findings before continuing

Smart Context Management
~~~~~~~~~~~~~~~~~~~~~~~~

FinGPT includes intelligent context management:

**How it works:**

- **Session-Based**: The agent maintains the full conversation history for the current session.
- **No Hidden Compression**: All context is preserved until the session expires or is manually cleared.
- **Session Isolation**: Each browser tab/session maintains its own isolated context.

.. note::
   Each browser tab maintains its own conversation context. Refreshing the page starts a new session.

Troubleshooting Advanced Features
---------------------------------

Common Issues
~~~~~~~~~~~~~

**MCP features not working:**

- Confirm OpenAI API key is valid
- Check you're using an MCP-compatible model
- Monitor terminal for MCP-related errors

**Slow responses with Advanced Ask:**

- Reduce number of preferred URLs
- Check internet connection
- Consider using a faster model
