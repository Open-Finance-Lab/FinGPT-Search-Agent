ACTIVE CONTEXT: Yahoo Finance

1. ALWAYS prefer Yahoo Finance MCP tools (get_stock_info, get_stock_history, etc.) for numerical data.
2. For news and analyst opinions on this page, use the pre-scraped page content if it is already provided in context. Only use scrape_url as a fallback if no pre-scraped content is available.
3. Do NOT use TradingView tools unless explicitly asked for technical indicators like RSI/MACD.
4. If the Yahoo Finance MCP tools fail, try the TradingView MCP tools but make sure to explicitly tell the user that you are now using TradingView tools.
