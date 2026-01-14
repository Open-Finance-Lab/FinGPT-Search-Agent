"""Handler for get_stock_financials tool."""

import json
import logging
from typing import List

import mcp.types as types

from mcp_server.handlers.base import ToolHandler, ToolContext
from mcp_server.handlers.stock_info import get_ticker
from mcp_server.executor import run_in_executor


logger = logging.getLogger(__name__)


class GetStockFinancialsHandler(ToolHandler):
    """Handler for get_stock_financials tool."""

    async def execute(self, ctx: ToolContext) -> List[types.TextContent]:
        """Execute get_stock_financials tool.

        Args:
            ctx: Tool execution context

        Returns:
            List containing financial statements as JSON
        """
        stock = await get_ticker(ctx.ticker)

        # Get all financial statements in parallel
        income_stmt = await run_in_executor(lambda: stock.income_stmt)
        balance_sheet = await run_in_executor(lambda: stock.balance_sheet)
        cashflow = await run_in_executor(lambda: stock.cashflow)

        financials = {
            "income_statement": income_stmt.to_dict() if not income_stmt.empty else {},
            "balance_sheet": balance_sheet.to_dict() if not balance_sheet.empty else {},
            "cash_flow": cashflow.to_dict() if not cashflow.empty else {}
        }

        return [types.TextContent(
            type="text",
            text=json.dumps(financials, indent=2, default=str)
        )]
