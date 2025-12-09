# Unified Context Management System Documentation

## Overview

The Unified Context Management System is a complete refactoring of FinGPT's conversation and context handling. It provides comprehensive tracking of all conversation history, fetched context from multiple sources, and metadata in an elegant JSON structure.

## Key Improvements

### 1. Full Conversation History
- **Before**: Limited message buffer, context could be lost
- **After**: Complete conversation history maintained throughout session
- **Benefit**: LLM has access to entire conversation context for better continuity

### 2. Elegant JSON Structure
- **Before**: Mixed message prefixes and fragmented context
- **After**: Clean, hierarchical JSON with clear separation of concerns
- **Benefit**: Easy to debug, export, and analyze conversation flow

### 3. Multi-Source Context Integration
- **Before**: Scattered context handling across different modules
- **After**: Unified handling of web search, Playwright, and JS scraping
- **Benefit**: All context sources tracked and attributed properly

## Architecture

### Core Components

```
┌─────────────────────────────────────────────────┐
│           UnifiedContextManager                  │
│  • Session management                           │
│  • Context storage                              │
│  • JSON export/import                           │
└─────────────────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────┐
│           ContextIntegration                     │
│  • API bridge layer                             │
│  • Backward compatibility                        │
│  • Request handling                              │
└─────────────────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────┐
│         UnifiedDataScraper                       │
│  • LLM API calls                                │
│  • Response generation                           │
│  • Context formatting                            │
└─────────────────────────────────────────────────┘
```

### JSON Context Structure

```json
{
  "system_prompt": "System instructions for the LLM",

  "metadata": {
    "session_id": "unique_session_id",
    "timestamp": "2025-11-15T15:30:00Z",
    "mode": "research|thinking|normal",
    "current_url": "https://current.page",
    "user_timezone": "America/New_York",
    "user_time": "2025-11-15T10:30:00",
    "token_count": 4500,
    "message_count": 12
  },

  "fetched_context": {
    "web_search": [
      {
        "source_type": "web_search",
        "content": "Search result content",
        "url": "https://source.url",
        "timestamp": "2025-11-15T15:25:00Z",
        "extracted_data": {
          "title": "Page Title",
          "site_name": "Source Site",
          "published_date": "2025-11-14"
        }
      }
    ],
    "playwright": [
      {
        "source_type": "playwright",
        "content": "Scraped page content",
        "url": "https://scraped.page",
        "timestamp": "2025-11-15T15:26:00Z",
        "extracted_data": {
          "action": "click_and_wait"
        }
      }
    ],
    "js_scraping": [
      {
        "source_type": "js_scraping",
        "content": "JS extracted content",
        "url": "https://current.page",
        "timestamp": "2025-11-15T15:24:00Z"
      }
    ]
  },

  "conversation_history": [
    {
      "role": "user",
      "content": "User's question",
      "timestamp": "2025-11-15T15:20:00Z"
    },
    {
      "role": "assistant",
      "content": "Assistant's response",
      "timestamp": "2025-11-15T15:20:30Z",
      "metadata": {
        "model": "gpt-4o-mini",
        "sources_used": [...],
        "tools_used": ["web_search", "playwright"],
        "response_time_ms": 1250
      }
    }
  ]
}
```

## Usage Examples

### 1. Simple Chat Response

```python
from datascraper.context_integration import prepare_context_messages, add_response_to_context

# Prepare context with full history
messages, session_id = prepare_context_messages(
    request=request,
    question="What is Apple's stock price?",
    current_url="https://finance.yahoo.com/quote/AAPL"
)

# Generate response (has access to full conversation history)
response = create_response(messages, model="gpt-4o-mini")

# Add response to context for future messages
add_response_to_context(
    session_id=session_id,
    response=response,
    model="gpt-4o-mini",
    response_time_ms=850
)
```

### 2. Web Search with Context

```python
# Add search results to context
integration.add_search_results(session_id, [
    {
        "title": "Latest Apple News",
        "snippet": "Apple reports Q4 earnings...",
        "url": "https://news.source",
        "body": "Full article content..."
    }
])

# Generate response with search context
response = create_web_search_response(
    session_id=session_id,
    model="gpt-4o-mini"
)
```

### 3. Playwright Integration

```python
# Add Playwright scraped content
integration.add_playwright_content(
    session_id=session_id,
    content="Dynamic page content",
    url="https://dynamic.site",
    action="scroll_and_extract"
)

# Content is now part of context for future responses
```

## API Endpoints

### Refactored Endpoints

- `GET /chat_response/` - Normal chat with domain-restricted Playwright
- `GET /get_adv_response/` - Advanced mode with web search
- `POST /agent_chat_response/` - Agent mode with optional tools
- `POST /input_webtext/` - Add JS scraped content
- `DELETE /clear_messages/` - Clear conversation/context
- `GET /get_context_stats/` - Get session statistics
- `GET /export_context/` - Export full context as JSON

### Response Format

```json
{
  "resp": {
    "model_name": "Response text..."
  },
  "context_stats": {
    "session_id": "session_123",
    "mode": "research",
    "message_count": 10,
    "token_count": 3500,
    "fetched_context": {
      "web_search": 2,
      "playwright": 1,
      "js_scraping": 3
    }
  }
}
```

## Migration Guide

### For API Views

Replace old context preparation:

```python
# OLD
messages = _prepare_context_messages(request, question)
_add_response_to_context(response)

# NEW
from datascraper.context_integration import (
    prepare_context_messages,
    add_response_to_context
)

messages, session_id = prepare_context_messages(
    request, question, endpoint="your_endpoint"
)
add_response_to_context(session_id, response, model, sources)
```

### For DataScraper Functions

Use new unified scraper:

```python
# OLD
response = create_response(user_input, message_list, model)

# NEW
from datascraper.datascraper_refactored import get_unified_scraper

scraper = get_unified_scraper()
response = scraper.create_response(session_id, model)
```

## Benefits

### 1. Complete Context Preservation
- Every message in the conversation is preserved
- All fetched content is tracked with source attribution
- Metadata provides temporal and environmental context

### 2. Better LLM Performance
- Models have access to full conversation history
- Context from multiple sources enhances response quality
- Proper attribution enables fact-checking

### 3. Debugging and Analysis
- Export full context as JSON for debugging
- Track token usage and response times
- Analyze conversation flow and context sources

### 4. Scalability
- Session-based isolation prevents cross-contamination
- Efficient token counting and management
- Clean separation of concerns

## Testing

Run the comprehensive test suite:

```bash
cd Main/backend
python3 test_unified_context.py
```

Tests validate:
- Context creation and management
- Message history tracking
- Fetched content integration
- JSON structure compliance
- Export/import functionality
- Backward compatibility

## Implementation Files

- `datascraper/unified_context_manager.py` - Core context manager
- `datascraper/context_integration.py` - API integration layer
- `datascraper/datascraper_refactored.py` - Refactored response generation
- `api/views_refactored.py` - Refactored API endpoints
- `test_unified_context.py` - Comprehensive test suite

## Future Enhancements

1. **Persistent Storage**: Add database backing for context persistence
2. **Compression**: Implement intelligent compression for long conversations
3. **Analytics**: Add conversation analytics and insights
4. **Streaming**: Full streaming support for all response types
5. **Multi-Modal**: Support for image and file context

## Conclusion

The Unified Context Management System provides a solid foundation for FinGPT's conversation handling. It eliminates edge cases through good design, maintains full conversation history, and provides an elegant JSON structure that makes the system easy to understand, debug, and extend.

Following Linus's philosophy: "Good taste" has been applied to eliminate special cases and create a clean, pragmatic solution that serves users effectively.