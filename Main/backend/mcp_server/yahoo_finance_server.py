"""Yahoo Finance MCP Server with async support and clean architecture."""

import asyncio
import logging
from typing import List

from mcp.server import Server, NotificationOptions
from mcp.server.models import InitializationOptions
from mcp.server.stdio import stdio_server
import mcp.types as types

from mcp_server.handlers.base import ToolHandler, ToolContext
from mcp_server.handlers.stock_info import GetStockInfoHandler
from mcp_server.handlers.stock_financials import GetStockFinancialsHandler
from mcp_server.handlers.stock_news import GetStockNewsHandler
from mcp_server.handlers.stock_history import GetStockHistoryHandler
from mcp_server.handlers.stock_analysis import GetStockAnalysisHandler
from mcp_server.validation import validate_ticker, ValidationError
from mcp_server.errors import ErrorType, ToolError
from mcp_server.executor import get_executor


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("yahoo-finance-server")

# Initialize the server
server = Server("yahoo-finance")

# Tool registry mapping tool names to handlers
TOOL_HANDLERS: dict[str, ToolHandler] = {
    "get_stock_info": GetStockInfoHandler(),
    "get_stock_financials": GetStockFinancialsHandler(),
    "get_stock_news": GetStockNewsHandler(),
    "get_stock_history": GetStockHistoryHandler(),
    "get_stock_analysis": GetStockAnalysisHandler(),
}


@server.list_tools()
async def handle_list_tools() -> List[types.Tool]:
    """List available tools."""
    return [
        types.Tool(
            name="get_stock_info",
            description="Get general information about a stock, including current price, market cap, PE ratio, and dividend yield.",
            inputSchema={
                "type": "object",
                "properties": {
                    "ticker": {
                        "type": "string",
                        "description": "The stock ticker symbol (e.g., 'AAPL', 'MSFT')."
                    }
                },
                "required": ["ticker"],
            },
        ),
        types.Tool(
            name="get_stock_financials",
            description="Get financial statements for a stock, including Income Statement, Balance Sheet, and Cash Flow.",
            inputSchema={
                "type": "object",
                "properties": {
                    "ticker": {
                        "type": "string",
                        "description": "The stock ticker symbol."
                    }
                },
                "required": ["ticker"],
            },
        ),
        types.Tool(
            name="get_stock_news",
            description="Get the latest news articles for a specific stock.",
            inputSchema={
                "type": "object",
                "properties": {
                    "ticker": {
                        "type": "string",
                        "description": "The stock ticker symbol."
                    }
                },
                "required": ["ticker"],
            },
        ),
        types.Tool(
            name="get_stock_history",
            description="Get historical price data for a stock.",
            inputSchema={
                "type": "object",
                "properties": {
                    "ticker": {
                        "type": "string",
                        "description": "The stock ticker symbol."
                    },
                    "period": {
                        "type": "string",
                        "description": "The period to fetch data for (e.g., '1mo', '1y', 'ytd', 'max').",
                        "default": "1mo"
                    },
                    "interval": {
                        "type": "string",
                        "description": "The data interval (e.g., '1d', '1wk', '1mo').",
                        "default": "1d"
                    }
                },
                "required": ["ticker"],
            },
        ),
        types.Tool(
            name="get_stock_analysis",
            description="Get analyst recommendations, price targets, and earnings estimates.",
            inputSchema={
                "type": "object",
                "properties": {
                    "ticker": {
                        "type": "string",
                        "description": "The stock ticker symbol."
                    }
                },
                "required": ["ticker"],
            },
        ),
    ]


@server.call_tool()
async def handle_call_tool(
    name: str, arguments: dict | None
) -> List[types.TextContent | types.ImageContent | types.EmbeddedResource]:
    """Handle tool execution requests with structured error handling."""
    ticker = None

    try:
        # Validate arguments
        if not arguments:
            raise ValidationError("Missing arguments")

        # Validate ticker for all operations
        ticker = validate_ticker(arguments.get("ticker"))

        # Get handler for this tool
        handler = TOOL_HANDLERS.get(name)
        if not handler:
            raise ValidationError(f"Unknown tool: {name}")

        # Create context and execute
        ctx = ToolContext(
            ticker=ticker,
            arguments=arguments,
            executor=get_executor()
        )

        logger.info(f"Executing {name} for {ticker}")
        return await handler.execute(ctx)

    except ValidationError as e:
        logger.warning(f"Validation error in {name}: {e}")
        return [ToolError(
            error_type=ErrorType.VALIDATION,
            message=str(e),
            ticker=ticker
        ).to_content()]

    except KeyError as e:
        logger.warning(f"Key error in {name} for {ticker}: {e}")
        return [ToolError(
            error_type=ErrorType.NOT_FOUND,
            message=f"Ticker {ticker} not found or has no data for requested field",
            ticker=ticker,
            details={"missing_key": str(e)}
        ).to_content()]

    except Exception as e:
        logger.error(
            f"Unexpected error in {name}",
            exc_info=True,
            extra={"ticker": ticker, "tool": name}
        )
        return [ToolError(
            error_type=ErrorType.INTERNAL,
            message="An internal error occurred. Please try again later.",
            ticker=ticker
        ).to_content()]


async def main():
    """Run the MCP server."""
    logger.info("Starting Yahoo Finance MCP server")

    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="yahoo-finance",
                server_version="0.2.0",
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                ),
            ),
        )


if __name__ == "__main__":
    asyncio.run(main())
