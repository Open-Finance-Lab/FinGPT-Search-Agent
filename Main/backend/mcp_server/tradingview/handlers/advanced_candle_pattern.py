"""Handler for get_advanced_candle_pattern tool."""

import json
import logging
from typing import List

import mcp.types as types

from mcp_server.handlers.base import ToolContext
from mcp_server.tradingview.handlers.base import TradingViewBaseHandler
from mcp_server.tradingview.validation import (
    validate_exchange,
    validate_timeframe,
    validate_crypto_symbol
)


logger = logging.getLogger(__name__)


class GetAdvancedCandlePatternHandler(TradingViewBaseHandler):
    """Handler for get_advanced_candle_pattern tool.

    Multi-timeframe candlestick pattern analysis.
    """

    async def execute(self, ctx: ToolContext) -> List[types.TextContent]:
        """Execute get_advanced_candle_pattern tool.

        Args:
            ctx: Tool execution context with arguments:
                - exchange: Exchange name (e.g., 'BINANCE', 'KUCOIN')
                - symbol: Trading pair symbol (e.g., 'BTCUSDT')
                - timeframe: Timeframe (e.g., '1D', '4h')

        Returns:
            List containing multi-timeframe pattern analysis as JSON
        """
        try:
            # Validate inputs
            exchange = validate_exchange(ctx.arguments.get("exchange"), market_type='crypto')
            symbol = validate_crypto_symbol(ctx.arguments.get("symbol"))
            timeframe = validate_timeframe(ctx.arguments.get("timeframe", "1D"))

            # Check cache
            cache_key = self._get_cache_key(
                exchange=exchange,
                symbol=symbol,
                timeframe=timeframe
            )

            cached = self._cache.get(cache_key)
            if cached:
                logger.info(f"Cache hit for advanced_candle_pattern:{exchange}:{symbol}:{timeframe}")
                return [types.TextContent(type="text", text=cached)]

            logger.info(f"Cache miss for advanced_candle_pattern:{exchange}:{symbol}:{timeframe}")

            # Call TradingView MCP
            response = await self._call_tradingview(
                tool_name="get_advanced_candle_pattern",
                params={
                    "exchange": exchange,
                    "symbol": symbol,
                    "timeframe": timeframe
                }
            )

            # Filter to relevant fields
            filtered = self._filter_numerical_fields(response)

            # Enforce numerical types
            if 'data' in filtered and filtered['data']:
                analysis = filtered['data']
                if isinstance(analysis, dict):
                    analysis = self._enforce_numerical_types(analysis)
                    filtered['data'] = analysis

            # Format response
            result = {
                "exchange": exchange,
                "symbol": symbol,
                "timeframe": timeframe,
                "patterns": filtered.get('data', {})
            }

            # Serialize and cache
            result_json = json.dumps(result, indent=2)
            self._cache.set(cache_key, result_json)

            return [types.TextContent(type="text", text=result_json)]

        except Exception as e:
            logger.error(f"Error in get_advanced_candle_pattern: {e}", exc_info=True)
            error_msg = {
                "error": "advanced_pattern_error",
                "message": str(e),
                "exchange": ctx.arguments.get("exchange"),
                "symbol": ctx.arguments.get("symbol"),
                "timeframe": ctx.arguments.get("timeframe")
            }
            return [types.TextContent(
                type="text",
                text=json.dumps(error_msg, indent=2)
            )]
