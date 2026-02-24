"""Handler for get_options_summary tool."""

import asyncio
import json
import logging
import math
from typing import List

import mcp.types as types

from mcp_server.handlers.base import ToolHandler, ToolContext
from mcp_server.handlers.stock_info import get_ticker
from mcp_server.executor import run_in_executor


logger = logging.getLogger(__name__)


def aggregate_chain(chain, expiration: str) -> dict:
    """Aggregate volume and OI from a single option chain into a summary dict."""
    call_vol = int(chain.calls["volume"].sum(skipna=True)) if "volume" in chain.calls.columns else 0
    put_vol = int(chain.puts["volume"].sum(skipna=True)) if "volume" in chain.puts.columns else 0
    call_oi = int(chain.calls["openInterest"].sum(skipna=True)) if "openInterest" in chain.calls.columns else 0
    put_oi = int(chain.puts["openInterest"].sum(skipna=True)) if "openInterest" in chain.puts.columns else 0

    # Handle NaN sums (all-NaN columns sum to 0 with skipna=True, but guard anyway)
    if math.isnan(call_vol):
        call_vol = 0
    if math.isnan(put_vol):
        put_vol = 0
    if math.isnan(call_oi):
        call_oi = 0
    if math.isnan(put_oi):
        put_oi = 0

    total_vol = call_vol + put_vol
    total_oi = call_oi + put_oi
    pc_ratio = round(put_vol / call_vol, 4) if call_vol > 0 else None

    return {
        "expiration": expiration,
        "call_volume": call_vol,
        "put_volume": put_vol,
        "total_volume": total_vol,
        "call_oi": call_oi,
        "put_oi": put_oi,
        "total_oi": total_oi,
        "put_call_ratio": pc_ratio,
    }


class GetOptionsSummaryHandler(ToolHandler):
    """Handler for get_options_summary tool.

    Returns aggregated options volume, open interest, and put/call ratio
    across all (or selected) expiration dates in a single call.
    """

    MAX_EXPIRATIONS = 8  # Cap to avoid excessive API calls

    async def execute(self, ctx: ToolContext) -> List[types.TextContent]:
        stock = await get_ticker(ctx.ticker)

        try:
            expirations = await run_in_executor(lambda: stock.options)
        except Exception:
            return [types.TextContent(
                type="text",
                text=f"No options data available for {ctx.ticker}."
            )]

        if not expirations:
            return [types.TextContent(
                type="text",
                text=f"No options data available for {ctx.ticker}."
            )]

        # Use only the nearest N expirations to keep response time reasonable
        expirations_to_fetch = list(expirations[:self.MAX_EXPIRATIONS])

        # Fetch all chains in parallel
        chains = await asyncio.gather(*(
            run_in_executor(lambda exp=exp: stock.option_chain(exp))
            for exp in expirations_to_fetch
        ))

        per_expiry = []
        totals = {
            "call_volume": 0, "put_volume": 0, "total_volume": 0,
            "call_oi": 0, "put_oi": 0, "total_oi": 0,
        }

        for exp, chain in zip(expirations_to_fetch, chains):
            summary = aggregate_chain(chain, exp)
            per_expiry.append(summary)
            for key in totals:
                totals[key] += summary[key]

        overall_pc = round(totals["put_volume"] / totals["call_volume"], 4) if totals["call_volume"] > 0 else None

        result = {
            "ticker": ctx.ticker,
            "expirations_included": len(expirations_to_fetch),
            "expirations_available": len(expirations),
            "aggregate": {
                **totals,
                "put_call_ratio": overall_pc,
            },
            "by_expiration": per_expiry,
        }

        return [types.TextContent(
            type="text",
            text=json.dumps(result, indent=2, default=str)
        )]
