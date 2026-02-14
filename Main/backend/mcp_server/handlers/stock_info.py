"""Handler for get_stock_info tool."""

import json
import logging
from typing import List

import mcp.types as types
import yfinance as yf

from mcp_server.handlers.base import ToolHandler, ToolContext
from mcp_server.executor import run_in_executor
from mcp_server.cache import TimedCache


logger = logging.getLogger(__name__)

# Cache for Ticker objects (5 min TTL)
_ticker_cache = TimedCache(ttl_seconds=300)


async def get_ticker(symbol: str) -> yf.Ticker:
    """Get Ticker object with caching.

    Args:
        symbol: Stock ticker symbol

    Returns:
        yfinance Ticker object
    """
    cached = _ticker_cache.get(symbol)
    if cached:
        logger.debug(f"Cache hit for {symbol}")
        return cached

    logger.debug(f"Cache miss for {symbol}")
    ticker = await run_in_executor(yf.Ticker, symbol)
    _ticker_cache.set(symbol, ticker)
    return ticker


class GetStockInfoHandler(ToolHandler):
    """Handler for get_stock_info tool."""

    # Keys relevant for stocks
    STOCK_KEYS = [
        'longName', 'symbol', 'currentPrice', 'marketCap', 'trailingPE',
        'forwardPE', 'dividendYield', 'fiftyTwoWeekHigh', 'fiftyTwoWeekLow',
        'averageVolume', 'sector', 'industry', 'longBusinessSummary'
    ]

    # Keys relevant for indices (^GSPC, ^DJI, etc.) and broader instruments
    INDEX_KEYS = [
        'shortName', 'symbol', 'regularMarketPrice', 'regularMarketDayHigh',
        'regularMarketDayLow', 'regularMarketOpen', 'regularMarketVolume',
        'regularMarketPreviousClose', 'regularMarketChange',
        'regularMarketChangePercent', 'fiftyTwoWeekHigh', 'fiftyTwoWeekLow',
        'fiftyDayAverage', 'twoHundredDayAverage'
    ]

    async def execute(self, ctx: ToolContext) -> List[types.TextContent]:
        """Execute get_stock_info tool.

        Args:
            ctx: Tool execution context

        Returns:
            List containing stock information as JSON
        """
        stock = await get_ticker(ctx.ticker)
        info = await run_in_executor(lambda: stock.info)

        # Use index-specific keys for tickers with ^ or . prefix
        is_index = ctx.ticker.startswith('^') or ctx.ticker.startswith('.')
        keys = self.INDEX_KEYS if is_index else self.STOCK_KEYS
        filtered_info = {k: info.get(k) for k in keys if k in info}

        if not filtered_info:
            return [types.TextContent(
                type="text",
                text=f"No information found for ticker {ctx.ticker}"
            )]

        return [types.TextContent(
            type="text",
            text=json.dumps(filtered_info, indent=2)
        )]
