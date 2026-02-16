"""
Multi-step iterative research engine.

Orchestrates query decomposition, sub-question routing, gap detection,
and response synthesis for complex financial queries.

Design doc: Docs/plans/2026-02-15-multi-step-research-design.md
"""

import json
import logging
import asyncio
from typing import Any, Optional

from openai import AsyncOpenAI
from dotenv import load_dotenv
from pathlib import Path

from .models_config import get_research_config

backend_dir = Path(__file__).resolve().parent.parent
load_dotenv(backend_dir / ".env")

logger = logging.getLogger(__name__)

# ── Shared planner client (cheap model, no tools) ────────────────────

import os

_OPENAI_KEY = os.getenv("OPENAI_API_KEY")
_planner_client: Optional[AsyncOpenAI] = AsyncOpenAI(api_key=_OPENAI_KEY) if _OPENAI_KEY else None


async def _call_planner(messages: list[dict], model: str | None = None):
    """Call the planner model (Chat Completions, no tools)."""
    if _planner_client is None:
        raise RuntimeError("OPENAI_API_KEY not set; research engine unavailable.")
    cfg = get_research_config()
    return await _planner_client.chat.completions.create(
        model=model or cfg["planner_model"],
        messages=messages,
        temperature=0.0,
        response_format={"type": "json_object"},
    )


# ── 1. Query Analyzer ────────────────────────────────────────────────

_ANALYZER_SYSTEM = """\
You are a financial research planner. Given a user's financial question, decide whether it needs to be broken into sub-questions for thorough research.

Rules:
- If the query asks about a SINGLE data point for ONE ticker (e.g., "What is AAPL price?"), set needs_decomposition=false.
- If the query compares multiple tickers, asks for data across time periods, or requires combining multiple data types, set needs_decomposition=true and list sub-questions.
- Each sub-question must have a "type": one of "numerical" (prices, ratios, revenue, volumes — answerable by Yahoo Finance API), "qualitative" (news, sentiment, analysis, forecasts — needs web search), or "analytical" (comparison, calculation — no search needed, derived from other answers).
- Maximum {max_sub} sub-questions. Prioritize the most important ones.

Respond ONLY with JSON:
{{"needs_decomposition": bool, "sub_questions": [{{"question": "...", "type": "numerical|qualitative|analytical"}}]}}
"""


class QueryAnalyzer:
    """Decompose complex financial queries into typed sub-questions."""

    def __init__(self, max_sub_questions: int | None = None):
        cfg = get_research_config()
        self.max_sub = max_sub_questions or cfg["max_sub_questions"]

    async def analyze(self, query: str, time_context: str = "") -> dict[str, Any]:
        """Return a research plan for the given query."""
        system = _ANALYZER_SYSTEM.format(max_sub=self.max_sub)
        user_msg = query
        if time_context:
            user_msg = f"{time_context}\n\nQuery: {query}"

        try:
            response = await _call_planner([
                {"role": "system", "content": system},
                {"role": "user", "content": user_msg},
            ])
            raw = response.choices[0].message.content
            plan = json.loads(raw)

            # Validate & cap
            if not isinstance(plan.get("needs_decomposition"), bool):
                plan["needs_decomposition"] = False
            subs = plan.get("sub_questions", [])
            if not isinstance(subs, list):
                subs = []
            # Validate each sub-question has required fields
            valid_types = {"numerical", "qualitative", "analytical"}
            validated = []
            for sq in subs[: self.max_sub]:
                if isinstance(sq, dict) and "question" in sq:
                    sq_type = sq.get("type", "qualitative")
                    if sq_type not in valid_types:
                        sq_type = "qualitative"
                    validated.append({"question": sq["question"], "type": sq_type})
            plan["sub_questions"] = validated
            return plan

        except (json.JSONDecodeError, KeyError, TypeError) as exc:
            logger.warning(f"[RESEARCH] Query analyzer returned invalid JSON: {exc}")
            return {"needs_decomposition": False, "sub_questions": []}
        except Exception as exc:
            logger.error(f"[RESEARCH] Query analyzer failed: {exc}")
            return {"needs_decomposition": False, "sub_questions": []}
