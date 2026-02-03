# FinGPT Standardized API Documentation

This API provides an OpenAI-compatible interface to the FinGPT agent, enabling seamless integration with existing tools and automated testing workflows.

## Base Configuration

- **Base URL**: `http://localhost:8000/v1`
- **Authentication**: Currently accepts any non-empty API Key (e.g., `sk-dummy`).
- **Compatibility**: The API follows the [OpenAI Chat Completions API](https://platform.openai.com/docs/api-reference/chat) specification.

---

## Endpoints

### 1. List Models
Retrieves the list of available models.

**Endpoint**: `GET /v1/models`

**Response**:
```json
{
  "object": "list",
  "data": [
    {"id": "FinGPT", "object": "model", ...},
    {"id": "FinGPT-Light", "object": "model", ...}
  ]
}
```

### 2. Chat Completions
Generates a response from the agent. This endpoint supports both **Thinking (Agent)** and **Research (Web Search)** modes.

**Endpoint**: `POST /v1/chat/completions`

#### Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `model` | string | Yes | ID of the model to use (e.g., `FinGPT`). |
| `messages` | array | Yes | A list of messages comprising the conversation so far. |
| `stream` | boolean | No | If `true`, partial message deltas will be sent (SSE). |
| `temperature`| number | No | Sampling temperature (0-1). |
| `user` | string | No | Unique identifier for the end-user. Maps to session ID. |

#### Custom Extensions (`extra_body`)
The API accepts custom parameters to control the agent's behavior. These should be passed in the root of the JSON body (or via `extra_body` in the OpenAI Python client).

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `mode` | string | **Yes** | The operation mode. Options: `"thinking"` or `"research"`. |
| `url` | string | No | A URL to scrape and analyze before generating the response. |

- **`mode="thinking"`**: The agent uses its internal tools and knowledge base. If `url` is provided, it scrapes the page and adds it to the context.
- **`mode="research"`**: The agent performs an active web search to answer the query (RAG / Web Surfer pipeline).

---

## Usage Examples

### Python (using `openai` library)

```python
from openai import OpenAI

client = OpenAI(
    base_url="http://localhost:8000/v1",
    api_key="sk-dummy"
)

# Example 1: Thinking Mode with URL Context
response = client.chat.completions.create(
    model="FinGPT",
    messages=[
        {"role": "user", "content": "Summarize the key financial metrics from this page."}
    ],
    # Custom parameters go here
    extra_body={
        "mode": "thinking",
        "url": "https://finance.yahoo.com/quote/AAPL"
    }
)
print(response.choices[0].message.content)

# Example 2: Research Mode
response = client.chat.completions.create(
    model="FinGPT",
    messages=[
        {"role": "user", "content": "What caused the recent crypto market volatility?"}
    ],
    extra_body={
        "mode": "research"
    }
)
print(response.choices[0].message.content)
```

### cURL

**Thinking Mode:**
```bash
curl http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer sk-dummy" \
  -d '{
    "model": "FinGPT",
    "messages": [{"role": "user", "content": "Analyze this page."}],
    "mode": "thinking",
    "url": "https://example.com"
  }'
```

**Research Mode:**
```bash
curl http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer sk-dummy" \
  -d '{
    "model": "FinGPT",
    "messages": [{"role": "user", "content": "Latest news on NVIDIA?"}],
    "mode": "research"
  }'
```

---

## Context & Statelessness
The API is designed to be **stateless** from the client's perspective, matching industry standards.
- You must send the full conversation history in the `messages` array for every request.
- The server automatically re-hydrates the internal session context based on the provided messages.

---

## MCP Servers

### Yahoo Finance MCP Server

The Yahoo Finance MCP server provides real-time and historical stock market data through the Model Context Protocol.

**Location:** `mcp_server/yahoo_finance_server.py`

**Features:**
- Async/await support for non-blocking operations
- Input validation and security
- TTL caching (5 min default)
- Structured error responses

**Available Tools:**
- `get_stock_info` - Company info, price, market cap, ratios
- `get_stock_financials` - Income statement, balance sheet, cash flow
- `get_stock_news` - Latest news articles
- `get_stock_history` - Historical price data
- `get_stock_analysis` - Analyst recommendations and estimates

**Configuration:**

Edit `mcp_server_config.json`:
```json
{
  "mcpServers": {
    "yahoo-finance": {
      "command": "python",
      "args": ["mcp_server/yahoo_finance_server.py"],
      "disabled": false
    }
  }
}
```

**See:** `mcp_server/README.md` for detailed documentation.
