# Yahoo Finance MCP Server

A high-performance Model Context Protocol (MCP) server for accessing Yahoo Finance stock data with async support, caching, and clean architecture.

## Features

- **Async/Await Support**: Non-blocking I/O with ThreadPoolExecutor
- **Input Validation**: Strict validation of all inputs to prevent injection attacks
- **TTL Caching**: 5-minute cache for ticker data to reduce API calls
- **Structured Errors**: JSON error responses with error types and details
- **Clean Architecture**: Handler-based design following SOLID principles

## Available Tools

### 1. get_stock_info
Get general information about a stock.

**Input:**
```json
{
  "ticker": "AAPL"
}
```

**Output:**
```json
{
  "longName": "Apple Inc.",
  "symbol": "AAPL",
  "currentPrice": 150.0,
  "marketCap": 2500000000000,
  "trailingPE": 25.5,
  "dividendYield": 0.0055,
  "sector": "Technology",
  "industry": "Consumer Electronics"
}
```

### 2. get_stock_financials
Get financial statements (Income Statement, Balance Sheet, Cash Flow).

**Input:**
```json
{
  "ticker": "AAPL"
}
```

### 3. get_stock_news
Get latest news articles for a stock.

**Input:**
```json
{
  "ticker": "AAPL"
}
```

### 4. get_stock_history
Get historical price data.

**Input:**
```json
{
  "ticker": "AAPL",
  "period": "1mo",
  "interval": "1d"
}
```

**Valid periods:** 1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, 10y, ytd, max

**Valid intervals:** 1m, 2m, 5m, 15m, 30m, 60m, 90m, 1h, 1d, 5d, 1wk, 1mo, 3mo

### 5. get_stock_analysis
Get analyst recommendations and price targets.

**Input:**
```json
{
  "ticker": "AAPL"
}
```

## Architecture

```
mcp_server/
├── yahoo_finance_server.py   # Main server + dispatcher
├── handlers/                  # Tool handlers
│   ├── base.py               # ToolHandler ABC + ToolContext
│   ├── stock_info.py         # get_stock_info handler
│   ├── stock_financials.py   # get_stock_financials handler
│   ├── stock_news.py         # get_stock_news handler
│   ├── stock_history.py      # get_stock_history handler
│   └── stock_analysis.py     # get_stock_analysis handler
├── validation.py              # Input validators
├── errors.py                  # Error types + ToolError
├── cache.py                   # TTL cache
└── executor.py                # Async executor utility
```

## Error Handling

All errors return structured JSON:

```json
{
  "error": "validation_error",
  "message": "Invalid ticker format: INVALID",
  "ticker": "INVALID"
}
```

**Error Types:**
- `validation_error`: Invalid input (bad ticker, period, interval)
- `not_found`: Ticker not found or no data available
- `rate_limit`: Rate limit exceeded
- `network_error`: Network/API issue
- `internal_error`: Unexpected server error

## Performance

- **Concurrent Requests**: Handles 10+ concurrent requests without blocking
- **Cache Hit Rate**: >70% for common tickers (AAPL, MSFT, etc.)
- **Response Time**: <500ms for cached data, <2s for fresh API calls

## Development

### Running the Server

```bash
cd Main/backend
python -m mcp_server.yahoo_finance_server
```

### Adding a New Tool

1. Create handler in `handlers/your_tool.py`:
```python
from mcp_server.handlers.base import ToolHandler, ToolContext

class YourToolHandler(ToolHandler):
    async def execute(self, ctx: ToolContext):
        # Your implementation
        pass
```

2. Register in `yahoo_finance_server.py`:
```python
TOOL_HANDLERS["your_tool"] = YourToolHandler()
```

3. Add tool definition in `handle_list_tools()`.

## Configuration

### Cache TTL
Default: 300 seconds (5 minutes)

Modify in `handlers/stock_info.py`:
```python
_ticker_cache = TimedCache(ttl_seconds=600)  # 10 minutes
```

### Thread Pool Size
Default: 4 workers

Modify in `executor.py`:
```python
_executor = ThreadPoolExecutor(max_workers=8)
```

## License

Part of FinGPT project. See main repository for license details.
