"""TradingView MCP Server with async support and clean architecture."""

import asyncio
import logging
from typing import List

from mcp.server import Server, NotificationOptions
from mcp.server.models import InitializationOptions
from mcp.server.stdio import stdio_server
import mcp.types as types

from mcp_server.handlers.base import ToolHandler, ToolContext
from mcp_server.tradingview.handlers.coin_analysis import GetCoinAnalysisHandler
from mcp_server.tradingview.handlers.top_gainers import GetTopGainersHandler
from mcp_server.tradingview.handlers.top_losers import GetTopLosersHandler
from mcp_server.tradingview.handlers.bollinger_scan import GetBollingerScanHandler
from mcp_server.tradingview.handlers.rating_filter import GetRatingFilterHandler
from mcp_server.tradingview.handlers.consecutive_candles import GetConsecutiveCandlesHandler
from mcp_server.tradingview.handlers.advanced_candle_pattern import GetAdvancedCandlePatternHandler
from mcp_server.tradingview.validation import ValidationError
from mcp_server.errors import ErrorType, ToolError
from mcp_server.executor import get_executor


import os

# Configure logging
logging.basicConfig(
    level=getattr(logging, os.getenv("MCP_LOG_LEVEL", "INFO").upper()),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("tradingview-server")

# Initialize the server
server = Server("tradingview")

# Tool registry mapping tool names to handlers
TOOL_HANDLERS: dict[str, ToolHandler] = {
    "get_coin_analysis": GetCoinAnalysisHandler(),
    "get_top_gainers": GetTopGainersHandler(),
    "get_top_losers": GetTopLosersHandler(),
    "get_bollinger_scan": GetBollingerScanHandler(),
    "get_rating_filter": GetRatingFilterHandler(),
    "get_consecutive_candles": GetConsecutiveCandlesHandler(),
    "get_advanced_candle_pattern": GetAdvancedCandlePatternHandler(),
}


@server.list_tools()
async def handle_list_tools() -> List[types.Tool]:
    """List available TradingView tools."""
    return [
        types.Tool(
            name="get_coin_analysis",
            description="Get complete technical analysis for a cryptocurrency including RSI, MACD, Bollinger Bands, ADX, Stochastic, and Moving Averages. Bollinger Band rating: -3 (very oversold) to +3 (very overbought).",
            inputSchema={
                "type": "object",
                "properties": {
                    "exchange": {
                        "type": "string",
                        "description": "Exchange name (e.g., 'BINANCE', 'KUCOIN', 'BYBIT', 'OKX')."
                    },
                    "symbol": {
                        "type": "string",
                        "description": "Trading pair symbol (e.g., 'BTCUSDT', 'ETHUSDT')."
                    },
                    "timeframe": {
                        "type": "string",
                        "description": "Timeframe (e.g., '1D', '4h', '1h', '15m'). Default: '1D'.",
                        "default": "1D"
                    }
                },
                "required": ["exchange", "symbol"],
            },
        ),
        types.Tool(
            name="get_top_gainers",
            description="Get top performing assets by exchange and timeframe. Returns assets with highest percentage gains.",
            inputSchema={
                "type": "object",
                "properties": {
                    "exchange": {
                        "type": "string",
                        "description": "Exchange name (e.g., 'BINANCE', 'KUCOIN')."
                    },
                    "timeframe": {
                        "type": "string",
                        "description": "Timeframe (e.g., '1D', '4h'). Default: '1D'.",
                        "default": "1D"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of results (1-100). Default: 10.",
                        "default": 10
                    }
                },
                "required": ["exchange"],
            },
        ),
        types.Tool(
            name="get_top_losers",
            description="Get worst performing assets by exchange and timeframe. Returns assets with largest percentage losses.",
            inputSchema={
                "type": "object",
                "properties": {
                    "exchange": {
                        "type": "string",
                        "description": "Exchange name (e.g., 'BINANCE', 'KUCOIN')."
                    },
                    "timeframe": {
                        "type": "string",
                        "description": "Timeframe (e.g., '1D', '4h'). Default: '1D'.",
                        "default": "1D"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of results (1-100). Default: 10.",
                        "default": 10
                    }
                },
                "required": ["exchange"],
            },
        ),
        types.Tool(
            name="get_bollinger_scan",
            description="Find assets with tight Bollinger Bands indicating potential consolidation patterns and upcoming breakouts.",
            inputSchema={
                "type": "object",
                "properties": {
                    "exchange": {
                        "type": "string",
                        "description": "Exchange name (e.g., 'BINANCE', 'KUCOIN')."
                    },
                    "timeframe": {
                        "type": "string",
                        "description": "Timeframe (e.g., '1D', '4h'). Default: '1D'.",
                        "default": "1D"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of results (1-100). Default: 10.",
                        "default": 10
                    }
                },
                "required": ["exchange"],
            },
        ),
        types.Tool(
            name="get_rating_filter",
            description="Filter assets by Bollinger Band rating. Rating scale: -3 (very oversold), -2 (oversold), -1 (slightly oversold), 0 (neutral), +1 (slightly overbought), +2 (overbought), +3 (very overbought).",
            inputSchema={
                "type": "object",
                "properties": {
                    "exchange": {
                        "type": "string",
                        "description": "Exchange name (e.g., 'BINANCE', 'KUCOIN')."
                    },
                    "timeframe": {
                        "type": "string",
                        "description": "Timeframe (e.g., '1D', '4h'). Default: '1D'.",
                        "default": "1D"
                    },
                    "rating": {
                        "type": "integer",
                        "description": "Bollinger Band rating (-3 to +3). Default: 0.",
                        "default": 0
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of results (1-100). Default: 10.",
                        "default": 10
                    }
                },
                "required": ["exchange"],
            },
        ),
        types.Tool(
            name="get_consecutive_candles",
            description="Detect candlestick patterns with consecutive bullish or bearish candles indicating strong momentum.",
            inputSchema={
                "type": "object",
                "properties": {
                    "exchange": {
                        "type": "string",
                        "description": "Exchange name (e.g., 'BINANCE', 'KUCOIN')."
                    },
                    "timeframe": {
                        "type": "string",
                        "description": "Timeframe (e.g., '1D', '4h'). Default: '1D'.",
                        "default": "1D"
                    },
                    "candle_type": {
                        "type": "string",
                        "description": "Type of candles: 'bullish' or 'bearish'. Default: 'bullish'.",
                        "default": "bullish"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of results (1-100). Default: 10.",
                        "default": 10
                    }
                },
                "required": ["exchange"],
            },
        ),
        types.Tool(
            name="get_advanced_candle_pattern",
            description="Get multi-timeframe candlestick pattern analysis for a specific symbol, identifying complex patterns across different timeframes.",
            inputSchema={
                "type": "object",
                "properties": {
                    "exchange": {
                        "type": "string",
                        "description": "Exchange name (e.g., 'BINANCE', 'KUCOIN')."
                    },
                    "symbol": {
                        "type": "string",
                        "description": "Trading pair symbol (e.g., 'BTCUSDT', 'ETHUSDT')."
                    },
                    "timeframe": {
                        "type": "string",
                        "description": "Timeframe (e.g., '1D', '4h'). Default: '1D'.",
                        "default": "1D"
                    }
                },
                "required": ["exchange", "symbol"],
            },
        ),
    ]


@server.call_tool()
async def handle_call_tool(
    name: str, arguments: dict | None
) -> List[types.TextContent | types.ImageContent | types.EmbeddedResource]:
    """Handle tool execution requests with structured error handling."""
    try:
        # Validate arguments
        if not arguments:
            raise ValidationError("Missing arguments")

        # Get handler for this tool
        handler = TOOL_HANDLERS.get(name)
        if not handler:
            raise ValidationError(f"Unknown tool: {name}")

        # Create context and execute
        ctx = ToolContext(
            ticker="",  # Not used for TradingView
            arguments=arguments,
            executor=get_executor()
        )

        logger.info(f"Executing {name} with args: {arguments}")
        return await handler.execute(ctx)

    except ValidationError as e:
        logger.warning(f"Validation error in {name}: {e}")
        return [ToolError(
            error_type=ErrorType.VALIDATION,
            message=str(e),
            details={"tool": name, "arguments": arguments}
        ).to_content()]

    except Exception as e:
        logger.error(
            f"Unexpected error in {name}",
            exc_info=True,
            extra={"tool": name, "arguments": arguments}
        )
        return [ToolError(
            error_type=ErrorType.INTERNAL,
            message="An internal error occurred. Please try again later.",
            details={"tool": name}
        ).to_content()]


async def main():
    """Run the MCP server."""
    logger.info("Starting TradingView MCP server")

    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="tradingview",
                server_version="0.1.0",
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                ),
            ),
        )


if __name__ == "__main__":
    asyncio.run(main())
