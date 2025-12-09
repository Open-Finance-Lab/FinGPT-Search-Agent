# Unified Context Management System Documentation

## Overview

The Unified Context Management System provides comprehensive tracking of conversation history, fetched context from multiple sources, and metadata in a structured JSON format. It replaces legacy context handling with a session-based approach that ensures the Large Language Model (LLM) has access to the full conversation context.

## Core Design

The system is built around a few key principles:
1.  **Session-Based Context**: All context is tied to a session ID, ensuring isolation between users and conversations.
2.  **Explicit Context Tracking**: Every piece of information (user message, assistant response, web search result, page content) is explicitly stored with metadata (timestamps, sources).
3.  **JSON-First**: The internal representation is always a valid, structured JSON object, making it easy to debug, export, and analyze.
4.  **No Hidden State**: There is no hidden "compression" or automatic truncation in the storage layer. The full history is preserved in the session.

## Architecture

### Core Components

*   **`UnifiedContextManager`** (`datascraper/unified_context_manager.py`): The singleton class that holds the state. It manages sessions, enforces limits (TTL, max sessions), and provides methods to add/retrieve data.
*   **`ContextIntegration`** (`datascraper/context_integration.py`): A bridge layer between Django views and the Context Manager. It handles request parsing (session ID extraction, mode determination) and formatting.
*   **`API Views`** (`api/views.py`): The endpoints that utilize the context manager to serve chat, research, and agent requests.

### JSON Context Structure

The context for a session is stored in the following structure:

```json
{
  "system_prompt": "System instructions for the LLM...",
  
  "metadata": {
    "session_id": "unique_session_id",
    "timestamp": "2025-12-09T12:00:00+00:00",
    "mode": "normal|thinking|research",
    "current_url": "https://example.com/current-page",
    "user_timezone": "America/New_York",
    "user_time": "2025-12-09T07:00:00",
    "token_count": 1500,
    "message_count": 5
  },

  "fetched_context": {
    "web_search": [
      {
        "source_type": "web_search",
        "content": "Search result content...",
        "url": "https://source.url",
        "timestamp": "2025-12-09T12:05:00+00:00",
        "extracted_data": {
          "title": "Page Title",
          "site_name": "Source Site",
          "published_date": "2025-11-14"
        }
      }
    ],
    "js_scraping": [
      {
        "source_type": "js_scraping",
        "content": "Content scraped from the user's current page...",
        "url": "https://current.page",
        "timestamp": "2025-12-09T12:10:00+00:00"
      }
    ]
  ],

  "conversation_history": [
    {
      "role": "user",
      "content": "User's question",
      "timestamp": "2025-12-09T12:01:00+00:00"
    },
    {
      "role": "assistant",
      "content": "Assistant's response",
      "timestamp": "2025-12-09T12:01:30+00:00",
      "metadata": {
        "model": "gpt-4o-mini",
        "sources_used": [...],
        "tools_used": ["web_search"],
        "response_time_ms": 1250
      }
    }
  ]
}
```

## Usage Examples

### 1. Basic Interaction in an API View

```python
from datascraper.unified_context_manager import get_context_manager, ContextMode

# Get the manager singleton
context_mgr = get_context_manager()

# 1. Update Metadata (Start of request)
context_mgr.update_metadata(
    session_id=session_id,
    mode=ContextMode.THINKING,
    current_url=current_url
)

# 2. Add User Message
context_mgr.add_user_message(session_id, question)

# 3. Get Formatted Messages for LLM
# This converts the internal JSON structure into a list of messages [System, User, Assistant...]
messages = context_mgr.get_formatted_messages_for_api(session_id)

# 4. Call LLM (using datascraper or other client)
response = llm_client.generate(messages)

# 5. Add Assistant Response
context_mgr.add_assistant_message(
    session_id=session_id,
    content=response,
    model="gpt-4o-mini",
    response_time_ms=850
)
```

### 2. Adding Fetched Context (e.g., Web Search)

```python
from datascraper.context_integration import get_context_integration

integration = get_context_integration()

# Add search results (automatically formatted and added to 'fetched_context.web_search')
integration.add_search_results(session_id, [
    {
        "title": "Latest News",
        "snippet": "...",
        "url": "https://news.com",
        "body": "..."
    }
])
```

### 3. Adding Page Content (Scraping)

```python
# Add content from the current page (e.g., via extension)
integration.add_web_content(
    request=request,
    text_content="Main content of the page...",
    current_url="https://example.com",
    source_type="js_scraping"
)
```

## API Endpoints

The following key endpoints in `api/views.py` interact with the system:

*   `GET /chat_response/`: Standard chat (Thinking Mode). Uses `unified_context_manager` to maintain history.
*   `GET /get_adv_response/`: Advanced/Research Mode. Performs web searches and adds them to `fetched_context["web_search"]`.
*   `POST /agent_chat_response/`: Agent interface, similar to chat response but conceptualized for agentic tasks.
*   `POST /add_webtext/`: Ingests text content scraped from the frontend (browser extension) and stores it in `fetched_context["js_scraping"]`.
*   `DELETE /clear/`: Clears the conversation history for the session. Can optionally preserve fetched web content.
*   `GET /get_memory_stats/`: Returns JSON statistics about the current session (token count, message count, etc.).

## Implementation Details

*   **Token Estimation**: A rough estimation (~4 chars/token) is used for basic tracking in `metadata.token_count`.
*   **Session Management**: Sessions are stored in memory. An LRU (Least Recently Used) mechanism ensures that memory usage remains bounded by evicting the oldest sessions when the limit (default 100) is reached. Sessions also have a TTL (Time To Live).
*   **Thread Safety**: The current implementation primarily writes to a synchronized in-memory dictionary. For production scaling with multiple workers, a persistent backing store (Redis/DB) would be required (see Future Enhancements).

## Future Enhancements

1.  **Persistent Storage**: Move session storage from in-memory dict to a database or Redis to support multi-process deployments.
2.  **Context Compression**: Implement summarization or truncation strategies when `token_count` exceeds model limits.
3.  **Analytics**: deeper analysis of conversation patterns.