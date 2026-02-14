"""Handler for get_options_chain tool."""

import json
import logging
from typing import List

import mcp.types as types

from mcp_server.handlers.base import ToolHandler, ToolContext
from mcp_server.handlers.stock_info import get_ticker
from mcp_server.executor import run_in_executor


logger = logging.getLogger(__name__)


class GetOptionsChainHandler(ToolHandler):
    """Handler for get_options_chain tool.

    Two-step design:
    - Without expiration: returns available expiration dates (so the agent can pick one)
    - With expiration: returns calls and puts for that specific date
    """

    async def execute(self, ctx: ToolContext) -> List[types.TextContent]:
        """Execute get_options_chain tool.

        Args:
            ctx: Tool execution context

        Returns:
            List containing either available expirations or the options chain data
        """
        stock = await get_ticker(ctx.ticker)
        expiration = ctx.arguments.get("expiration")

        # Always fetch available expiration dates
        try:
            expirations = await run_in_executor(lambda: stock.options)
        except Exception:
            return [types.TextContent(
                type="text",
                text=f"No options data available for {ctx.ticker}. "
                     "Options are only available for optionable stocks."
            )]

        if not expirations:
            return [types.TextContent(
                type="text",
                text=f"No options data available for {ctx.ticker}. "
                     "Options are only available for optionable stocks."
            )]

        # If no expiration requested, return the list of available dates
        if not expiration:
            return [types.TextContent(
                type="text",
                text=json.dumps({
                    "ticker": ctx.ticker,
                    "available_expirations": list(expirations),
                    "hint": "Call this tool again with an 'expiration' date to get the full options chain."
                }, indent=2)
            )]

        # Validate the requested expiration exists
        if expiration not in expirations:
            return [types.TextContent(
                type="text",
                text=json.dumps({
                    "error": "invalid_expiration",
                    "message": f"Expiration '{expiration}' not available for {ctx.ticker}.",
                    "available_expirations": list(expirations)
                }, indent=2)
            )]

        # Fetch the option chain for the requested expiration
        chain = await run_in_executor(lambda: stock.option_chain(expiration))

        calls_data = chain.calls.to_dict(orient="records") if not chain.calls.empty else []
        puts_data = chain.puts.to_dict(orient="records") if not chain.puts.empty else []

        result = {
            "ticker": ctx.ticker,
            "expiration": expiration,
            "calls_count": len(calls_data),
            "puts_count": len(puts_data),
            "calls": calls_data,
            "puts": puts_data,
        }

        return [types.TextContent(
            type="text",
            text=json.dumps(result, indent=2, default=str)
        )]
