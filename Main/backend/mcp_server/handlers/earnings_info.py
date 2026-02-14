"""Handler for get_earnings_info tool."""

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


def _safe_df_to_dict(df) -> dict:
    """Convert a DataFrame to dict, handling None and empty cases."""
    if df is None or (isinstance(df, pd.DataFrame) and df.empty):
        return {}
    if isinstance(df, pd.DataFrame):
        return df.to_dict()
    # Some yfinance properties return dicts directly
    if isinstance(df, dict):
        return df
    return {}


class GetEarningsInfoHandler(ToolHandler):
    """Handler for get_earnings_info tool."""

    async def execute(self, ctx: ToolContext) -> List[types.TextContent]:
        """Execute get_earnings_info tool.

        Args:
            ctx: Tool execution context

        Returns:
            List containing earnings dates, estimates, and growth data as JSON
        """
        stock = await get_ticker(ctx.ticker)

        # Fetch all earnings-related data in parallel
        (
            calendar,
            earnings_dates,
            earnings_estimate,
            revenue_estimate,
            eps_trend,
            growth_estimates,
        ) = await asyncio.gather(
            run_in_executor(lambda: stock.calendar),
            run_in_executor(lambda: stock.earnings_dates),
            run_in_executor(lambda: stock.earnings_estimate),
            run_in_executor(lambda: stock.revenue_estimate),
            run_in_executor(lambda: stock.eps_trend),
            run_in_executor(lambda: stock.growth_estimates),
        )

        # Cap earnings_dates to most recent 8 to avoid bloat
        if isinstance(earnings_dates, pd.DataFrame) and len(earnings_dates) > 8:
            earnings_dates = earnings_dates.head(8)

        result = {
            "calendar": _safe_df_to_dict(calendar),
            "earnings_dates": _safe_df_to_dict(earnings_dates),
            "earnings_estimate": _safe_df_to_dict(earnings_estimate),
            "revenue_estimate": _safe_df_to_dict(revenue_estimate),
            "eps_trend": _safe_df_to_dict(eps_trend),
            "growth_estimates": _safe_df_to_dict(growth_estimates),
        }

        # If everything is empty, return a clear message
        if all(v == {} for v in result.values()):
            return [types.TextContent(
                type="text",
                text=f"No earnings data available for {ctx.ticker}. "
                     "Earnings data is typically only available for individual stocks."
            )]

        return [types.TextContent(
            type="text",
            text=json.dumps(result, indent=2, default=str)
        )]
