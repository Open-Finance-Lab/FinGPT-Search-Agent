"""`report_claim` agent tool for Layer 1 Validate.

Registers a numerical ratio claim the agent has emitted into a response,
so that the user can later trigger deterministic validation against XBRL
ground truth via the /api/axioms/validate/ endpoint.

Implemented as a native `agents.function_tool` (not an MCP server) because
it needs direct access to Django cache and session context — spinning up a
new stdio MCP server just to write to cache would be pure overhead.
"""

from __future__ import annotations

import json
import logging
from typing import List

from agents import function_tool

from axioms.registry import add_claim

logger = logging.getLogger(__name__)

SUPPORTED_RATIOS = ("accounting_equation", "gross_margin", "current_ratio")


def get_axiom_tools(session_id: str) -> List:
    """Return a list of agent tools bound to the given session_id.

    The session_id is captured in the closure so each MCP call routes
    the claim to the correct user's registry entry without threading
    context through every tool invocation.
    """

    @function_tool
    def report_claim(
        ratio: str,
        ticker: str,
        period: str,
        claimed_value: float,
        formula_inputs: str,
    ) -> str:
        """Record a numerical ratio claim you have made in your response so the
        user can verify it against SEC XBRL ground truth.

        Call this EXACTLY ONCE for every supported ratio you present to the user:
          - accounting_equation  (A = L + E balance-sheet identity)
          - gross_margin         (percentage, e.g., 44.13 for 44.13%)
          - current_ratio        (dimensionless, e.g., 0.9880)

        Args:
            ratio: One of "accounting_equation", "gross_margin", "current_ratio".
            ticker: Stock ticker symbol (e.g., "AAPL", "MSFT", "TSLA").
            period: Fiscal period end date as ISO string (YYYY-MM-DD).
                    E.g., "2023-09-30" for Apple FY2023, "2023-06-30" for MSFT FY2023,
                    "2023-12-31" for Tesla FY2023.
            claimed_value: The numerical value you reported. For gross_margin,
                           pass the percentage (e.g., 44.13, not 0.4413). For
                           accounting_equation, pass the Total Assets figure.
            formula_inputs: JSON string of the inputs you used. Keys vary by ratio:
                            accounting_equation: {"assets": N, "liabilities": N, "equity": N}
                            gross_margin:        {"revenue": N, "cogs": N}
                            current_ratio:       {"current_assets": N, "current_liabilities": N}
        """
        if ratio not in SUPPORTED_RATIOS:
            return (
                f"ERROR: '{ratio}' is not a supported ratio. "
                f"Supported: {', '.join(SUPPORTED_RATIOS)}."
            )
        try:
            inputs = json.loads(formula_inputs) if formula_inputs else {}
            if not isinstance(inputs, dict):
                raise ValueError("formula_inputs must be a JSON object")
        except (json.JSONDecodeError, ValueError) as exc:
            return f"ERROR: could not parse formula_inputs as JSON object: {exc}"

        claim = {
            "ratio": ratio,
            "ticker": ticker.upper(),
            "period": period,
            "claimed_value": float(claimed_value),
            "formula_inputs": inputs,
        }
        try:
            add_claim(session_id, claim)
        except Exception as exc:
            logger.exception("Failed to record axiom claim")
            return f"ERROR: failed to record claim: {exc}"

        return (
            f"Claim recorded: {ratio} for {ticker.upper()} @ {period} = "
            f"{claimed_value}. User may click Validate to verify against SEC filing."
        )

    return [report_claim]
