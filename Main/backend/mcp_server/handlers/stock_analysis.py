"""Handler for get_stock_analysis tool."""

import json
import logging
from typing import List

import mcp.types as types

from mcp_server.handlers.base import ToolHandler, ToolContext
from mcp_server.handlers.stock_info import get_ticker
from mcp_server.executor import run_in_executor


logger = logging.getLogger(__name__)


class GetStockAnalysisHandler(ToolHandler):
    """Handler for get_stock_analysis tool."""

    async def execute(self, ctx: ToolContext) -> List[types.TextContent]:
        """Execute get_stock_analysis tool.

        Args:
            ctx: Tool execution context

        Returns:
            List containing analyst recommendations and estimates as JSON
        """
        stock = await get_ticker(ctx.ticker)

        # Get all analysis data
        recommendations = await run_in_executor(lambda: stock.recommendations)
        recommendations_summary = await run_in_executor(lambda: stock.recommendations_summary)
        upgrades_downgrades = await run_in_executor(lambda: stock.upgrades_downgrades)

        analysis = {
            "recommendations": recommendations.to_dict() if recommendations is not None and not recommendations.empty else {},
            "recommendations_summary": recommendations_summary.to_dict() if recommendations_summary is not None and not recommendations_summary.empty else {},
            "upgrades_downgrades": upgrades_downgrades.to_dict() if upgrades_downgrades is not None and not upgrades_downgrades.empty else {}
        }

        return [types.TextContent(
            type="text",
            text=json.dumps(analysis, indent=2, default=str)
        )]
