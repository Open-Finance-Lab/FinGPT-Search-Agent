"""Registry of site-specific instructions for the FinGPT search agent."""

SITE_INSTRUCTIONS = {
    "finance.yahoo.com": (
        "ACTIVE CONTEXT: Yahoo Finance\n"
        "1. ALWAYS prefer Yahoo Finance MCP tools (get_stock_info, get_stock_history, etc.) for numerical data.\n"
        "2. For news and analyst opinions on this page, use scrape_url.\n"
        "3. Do NOT use TradingView tools unless explicitly asked for technical indicators like RSI/MACD."
    ),
    "tradingview.com": (
        "ACTIVE CONTEXT: TradingView\n"
        "1. ALWAYS prefer TradingView MCP tools (get_coin_analysis, get_top_gainers) for technical analysis and market screening.\n"
        "2. Use TradingView for crypto data as it has better exchange coverage.\n"
        "3. Do NOT use Yahoo Finance tools unless the requested data (e.g., financials) is unavailable on TradingView."
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
