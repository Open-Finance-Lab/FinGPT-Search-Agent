# R2C Context Management System for FinGPT Search Agent

## Overview

The R2C (Reading to Compressing) Context Management System implements a multi-granularity hierarchical compression algorithm for managing conversation context in the FinGPT Search Agent. This system ensures efficient token usage while preserving important financial context across conversations.

## Key Features

- **Session-based isolation**: Each browser session maintains its own conversation context
- **Automatic compression**: Triggers when context exceeds 20000 tokens
- **Financial-optimized scoring**: Prioritizes financial keywords and patterns
- **Hierarchical compression**: Two-level compression (chunk and sentence level)
- **Backward compatibility**: Works alongside the legacy message_list system
- **Status Monitor**: Provides compression metrics and token usage

## Architecture

### Core Components

1. **R2CContextManager** (`r2c_context_manager.py`)
   - Manages conversation sessions and compression algorithm
   - Handles importance scoring

2. **API Integration** (`views.py`)
   - Helper functions for context preparation
   - Response storage and retrieval
   - Statistics endpoint

3. **Model Integration** (`datascraper.py`)
   - Supports OpenAI, Anthropic, and DeepSeek models

## Information Flow

### 1. Initial Request
```
Browser Extension → Django Backend (views.py)
    ↓
    Request contains:
    - question: User's query
    - models: Selected AI models
    - use_r2c: Enable R2C (default: true)
    - use_rag: Enable RAG mode (optional)
    - current_url: Current webpage URL
```

### 2. Session Management
```
_get_session_id(request)
    ↓
    Creates/retrieves Django session ID
    ↓
    Used as unique key for R2C context storage
```

### 3. Context Preparation
```
_prepare_context_messages(request, question, use_r2c=True)
    ↓
    If R2C enabled:
        → r2c_manager.add_message(session_id, "user", question)
        → r2c_manager.get_context(session_id)
            ↓
            Returns:
            1. System prompt ("You are a helpful financial assistant...")
            2. [Compressed Context] (if compression was triggered)
            3. Recent messages (last 5 uncompressed)
    ↓
    If R2C disabled:
        → Uses legacy message_list (global, less secure)
```

### 4. R2C Compression Process
When token count exceeds threshold (20000 tokens):

```
_compress_context() triggers:
    ↓
    1. Group messages by role continuity → chunks
    ↓
    2. Calculate importance scores:
       - Financial keyword density (weighted by priority)
       - Length-based score (brevity preferred)
       - Recency score (newer = more important)
       - Q&A pattern recognition
    ↓
    3. Hierarchical compression:
       - Chunk-level: Remove least important chunks (ρ = 0.5)
       - Sentence-level: Remove least important sentences
    ↓
    4. Store compressed context separately
    ↓
    5. Keep only last 2 messages uncompressed
```

### 5. API Call Flow
```
Selected endpoint based on mode:
    - Normal: ds.create_response()
    - RAG: ds.create_rag_response()
    - Advanced: ds.create_advanced_response()
    - MCP: ds.create_mcp_response()
    ↓
    All receive the prepared context messages
    ↓
    Make API call to selected model provider
```

### 6. Response Storage
```
After receiving response:
    ↓
    _add_response_to_context(session_id, response, use_r2c)
        ↓
        r2c_manager.add_message(session_id, "assistant", response)
        ↓
        Updates token count (may trigger compression)
```

### 7. Response Return
```
_prepare_response_with_stats(responses, session_id, use_r2c)
    ↓
    Returns JSON with:
    {
        "resp": {model_name: response_text},
        "r2c_stats": {
            "message_count": int,
            "token_count": int,
            "compressed": boolean,
            "compression_count": int,
            "compression_history": [...]
        }
    }
```

## Configuration

### Initialization Parameters
```python
r2c_manager = R2CContextManager(
    max_tokens=20000,        # Token threshold before compression
    compression_ratio=0.5,   # Target compression (50% reduction)
    rho=0.5,                # Chunk vs sentence compression balance
    gamma=1.0,              # Importance allocation power factor
    model="gpt-3.5-turbo"   # Model for tokenizer selection
)
```

### Financial Keywords Configuration
The system uses three tiers of financial keywords for importance scoring:

- **High priority**: price, earnings, revenue, profit, loss, margin, ratio, dividend, yield, market, stock, bond, inflation, gdp, fed, rate, growth
- **Medium priority**: company, business, industry, sector, share, invest, trade, capital, asset, debt, equity
- **Low priority**: report, analysis, forecast, trend, data, information

## API Endpoints

### Chat Endpoints
- `GET /get_chat_response/` - Standard chat response
- `GET /get_mcp_response/` - MCP-enabled response
- `GET /get_adv_response/` - Advanced response with web search
- `POST /input_webtext/` - Add scraped web content to context

### Management Endpoints
- `GET /clear_messages/` - Clear conversation context
- `GET /api/get_r2c_stats/` - Get current session statistics

### Query Parameters
- `question`: User's query (required)
- `models`: Comma-separated model names (required)
- `use_r2c`: Enable R2C context management (default: "true")
- `use_rag`: Enable RAG mode (default: "false")
- `current_url`: Current webpage URL

## Usage Examples

### Basic Chat Request
```javascript
fetch('/get_chat_response/?question=What is the P/E ratio?&models=gpt-4&use_r2c=true')
    .then(response => response.json())
    .then(data => {
        console.log('Response:', data.resp);
        console.log('Token usage:', data.r2c_stats.token_count);
    });
```

### Advanced Request with RAG
```javascript
fetch('/get_adv_response/?question=Analyze AAPL stock&models=gpt-4&use_rag=true&use_r2c=true')
    .then(response => response.json())
    .then(data => {
        console.log('Response:', data.resp);
        console.log('Compressed:', data.r2c_stats.compressed);
    });
```

### Clear Context
```javascript
fetch('/clear_messages/?use_r2c=true')
    .then(response => response.json())
    .then(data => console.log(data.resp));
```

## Compression Algorithm Details

### Importance Score Calculation
```python
importance = (
    0.2 * length_score +      # Shorter messages score higher
    0.4 * keyword_score +     # Financial keyword density
    0.2 * recency_score +     # Position in conversation
    0.2 * pattern_score       # Q&A patterns
)
```

### Token Allocation
- Chunk-level removal: `E_chunk = ρ × E_comp`
- Sentence-level removal: `E_sent = (1-ρ) × E_comp`

Where `E_comp` is the total tokens to remove.

## Benefits

1. **Cost Efficiency**: Reduces API token usage by up to 50%
2. **Context Preservation**: Maintains important financial information
3. **Session Isolation**: Prevents cross-user data leakage
4. **Scalability**: Handles long conversations gracefully
5. **Transparency**: Provides detailed compression statistics

## Security Considerations

- Session-based isolation prevents data leakage between users
- No persistent storage of conversation data
- Automatic cleanup on session expiration
- Compressed context is read-only

## Dependencies

- `tiktoken`: OpenAI's tokenizer library
- `numpy`: Numerical computations
- `Django`: Session management
- Python 3.8+

## Installation

1. Install required packages:
```bash
pip install tiktoken numpy
```

2. Ensure Django sessions are configured in `settings.py`

3. The system initializes automatically when the Django server starts

## Monitoring

Use the `/api/get_r2c_stats/` endpoint to monitor:
- Current token usage
- Compression status
- Message count
- Compression history