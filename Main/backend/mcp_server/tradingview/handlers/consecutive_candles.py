"""Handler for get_consecutive_candles tool."""

import json
import logging
from typing import List

import mcp.types as types

from mcp_server.handlers.base import ToolContext
from mcp_server.tradingview.handlers.base import TradingViewBaseHandler
from mcp_server.tradingview.validation import (
    validate_exchange,
    validate_timeframe,
    validate_limit
)


logger = logging.getLogger(__name__)


class GetConsecutiveCandlesHandler(TradingViewBaseHandler):
    """Handler for get_consecutive_candles tool.

    Detects candlestick patterns (consecutive bullish/bearish candles).
    """

    async def execute(self, ctx: ToolContext) -> List[types.TextContent]:
        """Execute get_consecutive_candles tool.

        Args:
            ctx: Tool execution context with arguments:
                - exchange: Exchange name (e.g., 'BINANCE', 'KUCOIN')
                - timeframe: Timeframe (e.g., '1D', '4h')
                - candle_type: 'bullish' or 'bearish' (default: 'bullish')
                - limit: Maximum number of results (default: 10)

        Returns:
            List containing assets with consecutive candles as JSON
        """
        try:
            # Validate inputs
            exchange = validate_exchange(ctx.arguments.get("exchange"), market_type='crypto')
            timeframe = validate_timeframe(ctx.arguments.get("timeframe", "1D"))
            candle_type = ctx.arguments.get("candle_type", "bullish").lower()
            limit = validate_limit(ctx.arguments.get("limit", 10), max_limit=100)

            # Validate candle_type
            if candle_type not in ['bullish', 'bearish']:
                candle_type = 'bullish'

            # Check cache
            cache_key = self._get_cache_key(
                exchange=exchange,
                timeframe=timeframe,
                candle_type=candle_type,
                limit=limit
            )

            cached = self._cache.get(cache_key)
            if cached:
                logger.info(f"Cache hit for consecutive_candles:{exchange}:{timeframe}:{candle_type}")
                return [types.TextContent(type="text", text=cached)]

            logger.info(f"Cache miss for consecutive_candles:{exchange}:{timeframe}:{candle_type}")

            # Call TradingView MCP
            response = await self._call_tradingview(
                tool_name="get_consecutive_candles",
                params={
                    "exchange": exchange,
                    "timeframe": timeframe,
                    "candle_type": candle_type,
                    "limit": limit
                }
            )

            # Filter to relevant fields
            filtered = self._filter_numerical_fields(response)

            # Get data list
            data = filtered.get('data', [])

            # Enforce numerical types for each item
            if isinstance(data, list):
                data = [self._enforce_numerical_types(item) if isinstance(item, dict) else item
                        for item in data]

            # Log if large response
            self._log_large_response(data, threshold=50)

            # Format response
            result = {
                "exchange": exchange,
                "timeframe": timeframe,
                "candle_type": candle_type,
                "count": len(data),
                "patterns": data
            }

            # Serialize and cache
            result_json = json.dumps(result, indent=2)
            self._cache.set(cache_key, result_json)

            return [types.TextContent(type="text", text=result_json)]

        except Exception as e:
            logger.error(f"Error in get_consecutive_candles: {e}", exc_info=True)
            error_msg = {
                "error": "consecutive_candles_error",
                "message": str(e),
                "exchange": ctx.arguments.get("exchange"),
                "timeframe": ctx.arguments.get("timeframe")
            }
            return [types.TextContent(
                type="text",
                text=json.dumps(error_msg, indent=2)
            )]
