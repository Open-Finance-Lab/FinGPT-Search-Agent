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


# ── Helper wrappers for MCP and web search ────────────────────────────

async def _try_mcp_search(
    question: str,
    message_list: list[dict],
    model: str,
    user_timezone: str = None,
    user_time: str = None,
) -> Optional[str]:
    """Attempt to answer a sub-question via MCP tools. Returns text or None."""
    try:
        from datascraper.datascraper import _try_mcp_for_numerical_query
        # _try_mcp_for_numerical_query is sync and calls asyncio.run internally
        loop = asyncio.get_running_loop()
        result = await loop.run_in_executor(
            None,
            lambda: _try_mcp_for_numerical_query(
                user_input=question,
                message_list=message_list,
                model=model,
                user_timezone=user_timezone,
                user_time=user_time,
            ),
        )
        return result
    except Exception as exc:
        logger.warning(f"[RESEARCH] MCP search failed for '{question[:60]}': {exc}")
        return None


async def _web_search(
    question: str,
    message_list: list[dict],
    model: str,
    preferred_urls: list[str] = None,
    user_timezone: str = None,
    user_time: str = None,
) -> tuple[str, list[dict]]:
    """Run a single web search via OpenAI Responses API. Returns (text, sources)."""
    from datascraper.openai_search import create_responses_api_search_async

    text, sources = await create_responses_api_search_async(
        user_query=question,
        message_history=message_list,
        model=model,
        preferred_links=preferred_urls,
        stream=False,
        user_timezone=user_timezone,
        user_time=user_time,
    )
    return text, sources


# ── 2. Research Executor ──────────────────────────────────────────────


class ResearchExecutor:
    """Execute sub-questions by routing to MCP or web search."""

    def __init__(
        self,
        model: str,
        message_list: list[dict],
        preferred_urls: list[str] = None,
        user_timezone: str = None,
        user_time: str = None,
        parallel: bool = True,
    ):
        self.model = model
        self.message_list = message_list
        self.preferred_urls = preferred_urls or []
        self.user_timezone = user_timezone
        self.user_time = user_time
        self.parallel = parallel

    async def _execute_one(self, sq: dict) -> dict[str, Any]:
        """Execute a single sub-question and return a result dict."""
        question = sq["question"]
        sq_type = sq["type"]

        if sq_type == "analytical":
            return {
                "question": question,
                "type": sq_type,
                "answer": "(to be synthesized from other results)",
                "sources": [],
                "source": "deferred",
            }

        # Numerical: try MCP first
        if sq_type == "numerical":
            mcp_result = await _try_mcp_search(
                question=question,
                message_list=self.message_list,
                model=self.model,
                user_timezone=self.user_timezone,
                user_time=self.user_time,
            )
            if mcp_result is not None:
                return {
                    "question": question,
                    "type": sq_type,
                    "answer": mcp_result,
                    "sources": [],
                    "source": "mcp",
                }

        # Qualitative OR numerical-fallback: web search
        text, sources = await _web_search(
            question=question,
            message_list=self.message_list,
            model=self.model,
            preferred_urls=self.preferred_urls,
            user_timezone=self.user_timezone,
            user_time=self.user_time,
        )
        return {
            "question": question,
            "type": sq_type,
            "answer": text,
            "sources": sources,
            "source": "web",
        }

    async def execute(self, plan: dict) -> list[dict[str, Any]]:
        """Execute all sub-questions. Returns list of result dicts."""
        subs = plan.get("sub_questions", [])
        if not subs:
            return []

        if self.parallel:
            tasks = [self._execute_one(sq) for sq in subs]
            return list(await asyncio.gather(*tasks, return_exceptions=False))
        else:
            return [await self._execute_one(sq) for sq in subs]


# ── 3. Gap Detector ───────────────────────────────────────────────────

_GAP_DETECTOR_SYSTEM = """\
You are evaluating whether a set of research results fully answers the original financial query.

Original query: {query}

Research plan sub-questions:
{plan_summary}

Results collected so far:
{results_summary}

Evaluate:
1. Does the collected data fully answer the original query?
2. What specific data points are missing?
3. Suggest targeted follow-up queries (max 3) to fill gaps.

Respond ONLY with JSON:
{{"complete": bool, "gaps": ["description of gap 1", ...], "follow_up_queries": [{{"question": "...", "type": "numerical|qualitative"}}]}}
"""


class GapDetector:
    """Evaluate research completeness and suggest follow-up queries."""

    async def detect(
        self,
        original_query: str,
        plan: dict,
        results: list[dict],
    ) -> dict[str, Any]:
        """Return gap analysis with optional follow-up queries."""
        plan_summary = "\n".join(
            f"- {sq['question']} ({sq.get('type', '?')})"
            for sq in plan.get("sub_questions", [])
        ) or "(none)"

        results_summary = "\n".join(
            f"- Q: {r['question']}\n  A: {r.get('answer', '(no answer)')[:300]}"
            for r in results
        ) or "(no results yet)"

        prompt = _GAP_DETECTOR_SYSTEM.format(
            query=original_query,
            plan_summary=plan_summary,
            results_summary=results_summary,
        )

        try:
            response = await _call_planner([
                {"role": "system", "content": prompt},
                {"role": "user", "content": "Evaluate completeness."},
            ])
            raw = response.choices[0].message.content
            result = json.loads(raw)

            # Validate
            if not isinstance(result.get("complete"), bool):
                result["complete"] = True
            result.setdefault("gaps", [])
            follow_ups = result.get("follow_up_queries", [])
            if not isinstance(follow_ups, list):
                follow_ups = []
            # Cap follow-ups at 3
            result["follow_up_queries"] = follow_ups[:3]
            return result

        except (json.JSONDecodeError, KeyError, TypeError) as exc:
            logger.warning(f"[RESEARCH] Gap detector returned invalid JSON: {exc}")
            return {"complete": True, "gaps": [], "follow_up_queries": []}
        except Exception as exc:
            logger.error(f"[RESEARCH] Gap detector failed: {exc}")
            return {"complete": True, "gaps": [], "follow_up_queries": []}


# ── 4. Synthesizer ────────────────────────────────────────────────────

_SYNTHESIS_SYSTEM = """\
You are a financial research synthesizer. Combine the research findings below into a comprehensive, well-organized answer to the user's original question.

Rules:
- Integrate information from all research results.
- Preserve all citations and source attributions.
- For numerical data, use exact values from the research results. Never re-derive or approximate.
- Use LaTeX: $ for inline math, $$ for display equations.
- Remove redundancies but keep all distinct data points.
- If some data points could not be found, acknowledge this rather than guessing.
"""


async def _call_synthesis(messages: list[dict], model: str):
    """Call the synthesis model (Chat Completions, no tools)."""
    if _planner_client is None:
        raise RuntimeError("OPENAI_API_KEY not set; research engine unavailable.")
    return await _planner_client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=0.2,
    )


class Synthesizer:
    """Combine research findings into a final response."""

    def __init__(self, model: str | None = None):
        cfg = get_research_config()
        self.model = model or cfg["research_model"]

    async def synthesize(
        self,
        original_query: str,
        results: list[dict],
        time_context: str = "",
    ) -> str:
        """Return a synthesized response combining all research findings."""
        findings = []
        for r in results:
            if r.get("source") == "deferred":
                continue
            entry = f"### Sub-question: {r['question']}\n{r.get('answer', '(no data)')}"
            if r.get("sources"):
                urls = ", ".join(s.get("url", "") for s in r["sources"] if s.get("url"))
                if urls:
                    entry += f"\nSources: {urls}"
            findings.append(entry)

        user_msg = f"Original question: {original_query}\n\n"
        if time_context:
            user_msg += f"{time_context}\n\n"
        user_msg += "Research findings:\n\n" + "\n\n".join(findings)

        response = await _call_synthesis(
            messages=[
                {"role": "system", "content": _SYNTHESIS_SYSTEM},
                {"role": "user", "content": user_msg},
            ],
            model=self.model,
        )
        return response.choices[0].message.content
