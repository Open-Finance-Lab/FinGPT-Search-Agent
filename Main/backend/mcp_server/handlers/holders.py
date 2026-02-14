"""Handler for get_holders tool."""

import asyncio
import json
import logging
from typing import List

import mcp.types as types
import pandas as pd

from mcp_server.handlers.base import ToolHandler, ToolContext
from mcp_server.handlers.stock_info import get_ticker
from mcp_server.executor import run_in_executor


logger = logging.getLogger(__name__)


class GetHoldersHandler(ToolHandler):
    """Handler for get_holders tool."""

    async def execute(self, ctx: ToolContext) -> List[types.TextContent]:
        """Execute get_holders tool.

        Args:
            ctx: Tool execution context

        Returns:
            List containing holder and insider activity data as JSON
        """
        stock = await get_ticker(ctx.ticker)

        # Fetch all holder data in parallel
        (
            major_holders,
            institutional_holders,
            mutualfund_holders,
            insider_transactions,
        ) = await asyncio.gather(
            run_in_executor(lambda: stock.major_holders),
            run_in_executor(lambda: stock.institutional_holders),
            run_in_executor(lambda: stock.mutualfund_holders),
            run_in_executor(lambda: stock.insider_transactions),
        )

        def safe_to_dict(df, orient="records"):
            if df is None or (isinstance(df, pd.DataFrame) and df.empty):
                return []
            return df.to_dict(orient=orient)

        # Cap insider transactions to most recent 20
        if isinstance(insider_transactions, pd.DataFrame) and len(insider_transactions) > 20:
            insider_transactions = insider_transactions.head(20)

        result = {
            "major_holders": safe_to_dict(major_holders),
            "institutional_holders": safe_to_dict(institutional_holders),
            "mutualfund_holders": safe_to_dict(mutualfund_holders),
            "insider_transactions": safe_to_dict(insider_transactions),
        }

        # If everything is empty, return a clear message
        if all(v == [] for v in result.values()):
            return [types.TextContent(
                type="text",
                text=f"No holder data available for {ctx.ticker}. "
                     "Holder information is typically only available for individual stocks."
            )]

        return [types.TextContent(
            type="text",
            text=json.dumps(result, indent=2, default=str)
        )]
