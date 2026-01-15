"""Handler for get_stock_history tool."""

import logging
from typing import List

import mcp.types as types

from mcp_server.handlers.base import ToolHandler, ToolContext
from mcp_server.handlers.stock_info import get_ticker
from mcp_server.executor import run_in_executor
from mcp_server.validation import validate_period, validate_interval


logger = logging.getLogger(__name__)


class GetStockHistoryHandler(ToolHandler):
    """Handler for get_stock_history tool."""

    async def execute(self, ctx: ToolContext) -> List[types.TextContent]:
        """Execute get_stock_history tool.

        Args:
            ctx: Tool execution context

        Returns:
            List containing historical price data as JSON
        """
        period = validate_period(ctx.arguments.get("period", "1mo"))
        interval = validate_interval(ctx.arguments.get("interval", "1d"))

        stock = await get_ticker(ctx.ticker)
        history = await run_in_executor(
            lambda: stock.history(period=period, interval=interval)
        )

        if history.empty:
            return [types.TextContent(
                type="text",
                text=f"No historical data found for {ctx.ticker}"
            )]

        # Log warning for large datasets
        if len(history) > 1000:
            logger.warning(f"Large history dataset for {ctx.ticker}: {len(history)} rows")

        return [types.TextContent(
            type="text",
            text=history.to_json(orient="table")
        )]
