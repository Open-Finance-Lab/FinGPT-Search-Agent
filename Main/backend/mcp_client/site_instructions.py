"""Registry of site-specific instructions for the FinGPT search agent."""

SITE_INSTRUCTIONS = {
    "finance.yahoo.com": (
        "ACTIVE CONTEXT: Yahoo Finance\n"
        "1. ALWAYS prefer Yahoo Finance MCP tools (get_stock_info, get_stock_history, etc.) for numerical data.\n"
        "2. For news and analyst opinions on this page, use scrape_url.\n"
        "3. Do NOT use TradingView tools unless explicitly asked for technical indicators like RSI/MACD.\n"
        "4. If the Yahoo Finance MCP tools fail, try the TradingView MCP tools but make sure to explicitly tell the user that you are now using TradingView tools."
    ),
    "tradingview.com": (
        "USER IS ON TRADINGVIEW.COM. THIS IS THE AUTHORITATIVE CONTEXT.\n"
        "1. ALWAYS prioritize TradingView MCP tools for ANY stock or crypto data including prices, ratios, and technicals.\n"
        "2. Do NOT use Yahoo Finance tools unless TradingView explicitly returns an 'error' or 'unsupported' message for the ticker.\n"
        "3. TradingView handles basic market info (OHLCV, PE, Market Cap) via its technical markers.\n"
        "4. If the TradingView MCP tools fail, try the Yahoo Finance MCP tools but make sure to explicitly tell the user that you are now using Yahoo Finance tools."
    ),
    "sec.gov": (
        "ACTIVE CONTEXT: SEC EDGAR\n"
        "1. ALWAYS use SEC-EDGAR MCP tools (search_filings, get_filing_content) for any filing requests.\n"
        "2. Do NOT use URL scraping for official filings; the MCP tools are more reliable."
    )
}

def get_site_specific_instructions(domain: str) -> str:
    """Return tailored instructions for the given domain."""
    # Handle subdomains (e.g., ca.finance.yahoo.com -> finance.yahoo.com)
    for site, instructions in SITE_INSTRUCTIONS.items():
        if domain.endswith(site):
            return instructions
    return ""
