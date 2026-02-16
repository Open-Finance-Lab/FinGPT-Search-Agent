# Multi-Step Iterative Research — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add a multi-step iterative research engine that decomposes complex financial queries, routes sub-questions to MCP or web search, detects gaps, and synthesizes a comprehensive answer.

**Architecture:** A new `research_engine.py` module orchestrates 4 components: QueryAnalyzer (gpt-5-mini) decomposes queries, ResearchExecutor routes sub-questions to MCP/web, GapDetector (gpt-5-mini) identifies missing data, and Synthesizer (gpt-5.2) produces the final response. Simple queries bypass the engine entirely.

**Tech Stack:** Python 3.12, OpenAI SDK (Chat Completions + Responses API), asyncio, existing MCP client (Yahoo Finance)

**Design doc:** `Docs/plans/2026-02-15-multi-step-research-design.md`

---

### Task 1: Add RESEARCH_CONFIG to models_config.py

**Files:**
- Modify: `Main/backend/datascraper/models_config.py`
- Test: `Main/backend/tests/test_research_config.py`

**Step 1: Write the failing test**

Create `Main/backend/tests/test_research_config.py`:

```python
"""Tests for research configuration."""
import pytest


def test_research_config_exists():
    from datascraper.models_config import RESEARCH_CONFIG
    assert isinstance(RESEARCH_CONFIG, dict)


def test_research_config_has_required_keys():
    from datascraper.models_config import RESEARCH_CONFIG
    required = {"planner_model", "research_model", "max_iterations", "max_sub_questions", "parallel_searches"}
    assert required.issubset(RESEARCH_CONFIG.keys())


def test_research_config_defaults():
    from datascraper.models_config import RESEARCH_CONFIG
    assert RESEARCH_CONFIG["planner_model"] == "gpt-5-mini"
    assert RESEARCH_CONFIG["max_iterations"] == 3
    assert RESEARCH_CONFIG["max_sub_questions"] == 5
    assert RESEARCH_CONFIG["parallel_searches"] is True


def test_get_research_config_returns_copy():
    from datascraper.models_config import get_research_config
    config = get_research_config()
    config["max_iterations"] = 999
    from datascraper.models_config import RESEARCH_CONFIG
    assert RESEARCH_CONFIG["max_iterations"] == 3  # Original unchanged
```

**Step 2: Run test to verify it fails**

Run: `cd Main/backend && uv run python -m pytest tests/test_research_config.py -v`
Expected: FAIL — `ImportError: cannot import name 'RESEARCH_CONFIG'`

**Step 3: Write the implementation**

Add to bottom of `Main/backend/datascraper/models_config.py`:

```python
RESEARCH_CONFIG = {
    "planner_model": "gpt-5-mini",
    "research_model": "gpt-5.2-chat-latest",
    "max_iterations": 3,
    "max_sub_questions": 5,
    "parallel_searches": True,
}


def get_research_config() -> dict:
    """Return a copy of the research configuration (safe to mutate)."""
    return dict(RESEARCH_CONFIG)
```

**Step 4: Run test to verify it passes**

Run: `cd Main/backend && uv run python -m pytest tests/test_research_config.py -v`
Expected: 4 PASSED

**Step 5: Commit**

```bash
git add Main/backend/datascraper/models_config.py Main/backend/tests/test_research_config.py
git commit -m "feat: add RESEARCH_CONFIG to models_config"
```

---

### Task 2: Create research_engine.py — QueryAnalyzer

The QueryAnalyzer takes a user query and returns a structured research plan. It uses gpt-5-mini via Chat Completions (no tools needed) to classify whether the query needs decomposition and, if so, break it into typed sub-questions.

**Files:**
- Create: `Main/backend/datascraper/research_engine.py`
- Test: `Main/backend/tests/test_research_engine.py`

**Step 1: Write the failing tests**

Create `Main/backend/tests/test_research_engine.py`:

```python
"""Tests for the multi-step research engine."""
import json
import pytest
from unittest.mock import AsyncMock, patch, MagicMock


# ── QueryAnalyzer tests ──────────────────────────────────────────────

@pytest.mark.asyncio
async def test_query_analyzer_simple_query_bypasses():
    """Simple single-ticker queries should not need decomposition."""
    from datascraper.research_engine import QueryAnalyzer

    # Mock the OpenAI Chat Completions call
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = json.dumps({
        "needs_decomposition": False,
        "sub_questions": []
    })

    with patch("datascraper.research_engine._call_planner", new_callable=AsyncMock, return_value=mock_response):
        analyzer = QueryAnalyzer()
        plan = await analyzer.analyze("What is AAPL stock price?")

    assert plan["needs_decomposition"] is False
    assert plan["sub_questions"] == []


@pytest.mark.asyncio
async def test_query_analyzer_complex_query_decomposes():
    """Multi-part queries should be decomposed into sub-questions."""
    from datascraper.research_engine import QueryAnalyzer

    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = json.dumps({
        "needs_decomposition": True,
        "sub_questions": [
            {"question": "AAPL quarterly revenue Q2-Q4 2025", "type": "numerical"},
            {"question": "MSFT quarterly revenue Q2-Q4 2025", "type": "numerical"},
        ]
    })

    with patch("datascraper.research_engine._call_planner", new_callable=AsyncMock, return_value=mock_response):
        analyzer = QueryAnalyzer()
        plan = await analyzer.analyze("Compare AAPL and MSFT revenue growth over the last 3 quarters")

    assert plan["needs_decomposition"] is True
    assert len(plan["sub_questions"]) == 2
    assert plan["sub_questions"][0]["type"] == "numerical"


@pytest.mark.asyncio
async def test_query_analyzer_caps_sub_questions():
    """Sub-questions should be capped at max_sub_questions."""
    from datascraper.research_engine import QueryAnalyzer

    # Return 8 sub-questions, should be capped to 5
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = json.dumps({
        "needs_decomposition": True,
        "sub_questions": [{"question": f"Q{i}", "type": "qualitative"} for i in range(8)]
    })

    with patch("datascraper.research_engine._call_planner", new_callable=AsyncMock, return_value=mock_response):
        analyzer = QueryAnalyzer(max_sub_questions=5)
        plan = await analyzer.analyze("Very complex query")

    assert len(plan["sub_questions"]) == 5


@pytest.mark.asyncio
async def test_query_analyzer_handles_malformed_json():
    """If the LLM returns invalid JSON, fall back to no-decomposition."""
    from datascraper.research_engine import QueryAnalyzer

    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = "not valid json {{"

    with patch("datascraper.research_engine._call_planner", new_callable=AsyncMock, return_value=mock_response):
        analyzer = QueryAnalyzer()
        plan = await analyzer.analyze("Some query")

    assert plan["needs_decomposition"] is False
```

**Step 2: Run tests to verify they fail**

Run: `cd Main/backend && uv run python -m pytest tests/test_research_engine.py -v -k "query_analyzer"`
Expected: FAIL — `ModuleNotFoundError: No module named 'datascraper.research_engine'`

**Step 3: Write the implementation**

Create `Main/backend/datascraper/research_engine.py`:

```python
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
```

**Step 4: Run tests to verify they pass**

Run: `cd Main/backend && uv run python -m pytest tests/test_research_engine.py -v -k "query_analyzer"`
Expected: 4 PASSED

**Step 5: Commit**

```bash
git add Main/backend/datascraper/research_engine.py Main/backend/tests/test_research_engine.py
git commit -m "feat: add QueryAnalyzer to research engine"
```

---

### Task 3: Add ResearchExecutor to research_engine.py

The ResearchExecutor takes a research plan and executes each sub-question, routing numerical queries to MCP and qualitative ones to web search. Independent sub-questions run concurrently.

**Files:**
- Modify: `Main/backend/datascraper/research_engine.py`
- Modify: `Main/backend/tests/test_research_engine.py`

**Step 1: Write the failing tests**

Append to `Main/backend/tests/test_research_engine.py`:

```python
# ── ResearchExecutor tests ────────────────────────────────────────────

@pytest.mark.asyncio
async def test_executor_routes_numerical_to_mcp():
    """Numerical sub-questions should attempt MCP first."""
    from datascraper.research_engine import ResearchExecutor

    plan = {
        "sub_questions": [
            {"question": "AAPL current stock price", "type": "numerical"},
        ]
    }

    with patch("datascraper.research_engine._try_mcp_search", new_callable=AsyncMock, return_value="$152.34") as mcp_mock, \
         patch("datascraper.research_engine._web_search", new_callable=AsyncMock) as web_mock:
        executor = ResearchExecutor(model="gpt-5.2-chat-latest", message_list=[], preferred_urls=[])
        results = await executor.execute(plan)

    assert len(results) == 1
    assert results[0]["answer"] == "$152.34"
    assert results[0]["source"] == "mcp"
    mcp_mock.assert_called_once()
    web_mock.assert_not_called()


@pytest.mark.asyncio
async def test_executor_falls_back_to_web_on_mcp_failure():
    """If MCP fails for numerical, fall back to web search."""
    from datascraper.research_engine import ResearchExecutor

    plan = {
        "sub_questions": [
            {"question": "AAPL quarterly revenue", "type": "numerical"},
        ]
    }

    with patch("datascraper.research_engine._try_mcp_search", new_callable=AsyncMock, return_value=None), \
         patch("datascraper.research_engine._web_search", new_callable=AsyncMock, return_value=("Revenue was $94.9B", [{"url": "https://yahoo.com"}])):
        executor = ResearchExecutor(model="gpt-5.2-chat-latest", message_list=[], preferred_urls=[])
        results = await executor.execute(plan)

    assert results[0]["source"] == "web"
    assert "94.9B" in results[0]["answer"]


@pytest.mark.asyncio
async def test_executor_routes_qualitative_to_web():
    """Qualitative sub-questions go straight to web search."""
    from datascraper.research_engine import ResearchExecutor

    plan = {
        "sub_questions": [
            {"question": "Latest AAPL earnings analysis", "type": "qualitative"},
        ]
    }

    with patch("datascraper.research_engine._try_mcp_search", new_callable=AsyncMock) as mcp_mock, \
         patch("datascraper.research_engine._web_search", new_callable=AsyncMock, return_value=("Analysts say...", [{"url": "https://cnbc.com"}])):
        executor = ResearchExecutor(model="gpt-5.2-chat-latest", message_list=[], preferred_urls=[])
        results = await executor.execute(plan)

    mcp_mock.assert_not_called()
    assert results[0]["source"] == "web"


@pytest.mark.asyncio
async def test_executor_skips_analytical():
    """Analytical sub-questions produce a placeholder (no search)."""
    from datascraper.research_engine import ResearchExecutor

    plan = {
        "sub_questions": [
            {"question": "Compare growth rates", "type": "analytical"},
        ]
    }

    with patch("datascraper.research_engine._try_mcp_search", new_callable=AsyncMock) as mcp_mock, \
         patch("datascraper.research_engine._web_search", new_callable=AsyncMock) as web_mock:
        executor = ResearchExecutor(model="gpt-5.2-chat-latest", message_list=[], preferred_urls=[])
        results = await executor.execute(plan)

    mcp_mock.assert_not_called()
    web_mock.assert_not_called()
    assert results[0]["source"] == "deferred"
```

**Step 2: Run tests to verify they fail**

Run: `cd Main/backend && uv run python -m pytest tests/test_research_engine.py -v -k "executor"`
Expected: FAIL — `ImportError: cannot import name 'ResearchExecutor'`

**Step 3: Write the implementation**

Append to `Main/backend/datascraper/research_engine.py`:

```python
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
```

**Step 4: Run tests to verify they pass**

Run: `cd Main/backend && uv run python -m pytest tests/test_research_engine.py -v -k "executor"`
Expected: 4 PASSED

**Step 5: Commit**

```bash
git add Main/backend/datascraper/research_engine.py Main/backend/tests/test_research_engine.py
git commit -m "feat: add ResearchExecutor with MCP/web routing"
```

---

### Task 4: Add GapDetector and Synthesizer to research_engine.py

**Files:**
- Modify: `Main/backend/datascraper/research_engine.py`
- Modify: `Main/backend/tests/test_research_engine.py`

**Step 1: Write the failing tests**

Append to `Main/backend/tests/test_research_engine.py`:

```python
# ── GapDetector tests ─────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_gap_detector_complete():
    """When all data is present, gap detector returns complete=True."""
    from datascraper.research_engine import GapDetector

    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = json.dumps({
        "complete": True,
        "gaps": [],
        "follow_up_queries": []
    })

    with patch("datascraper.research_engine._call_planner", new_callable=AsyncMock, return_value=mock_response):
        detector = GapDetector()
        result = await detector.detect(
            original_query="What is AAPL price?",
            plan={"sub_questions": [{"question": "AAPL price", "type": "numerical"}]},
            results=[{"question": "AAPL price", "answer": "$152.34", "source": "mcp"}],
        )

    assert result["complete"] is True
    assert result["follow_up_queries"] == []


@pytest.mark.asyncio
async def test_gap_detector_finds_gaps():
    """When data is missing, gap detector returns follow-up queries."""
    from datascraper.research_engine import GapDetector

    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = json.dumps({
        "complete": False,
        "gaps": ["Missing MSFT Q3 revenue"],
        "follow_up_queries": [
            {"question": "MSFT Q3 2025 revenue", "type": "qualitative"}
        ]
    })

    with patch("datascraper.research_engine._call_planner", new_callable=AsyncMock, return_value=mock_response):
        detector = GapDetector()
        result = await detector.detect(
            original_query="Compare AAPL and MSFT revenue",
            plan={"sub_questions": []},
            results=[{"question": "AAPL revenue", "answer": "$94.9B"}],
        )

    assert result["complete"] is False
    assert len(result["follow_up_queries"]) == 1


# ── Synthesizer tests ─────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_synthesizer_combines_results():
    """Synthesizer should produce a final response from collected results."""
    from datascraper.research_engine import Synthesizer

    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = "AAPL revenue was $94.9B, MSFT was $64.7B. AAPL grew 8% vs MSFT 12%."

    with patch("datascraper.research_engine._call_synthesis", new_callable=AsyncMock, return_value=mock_response):
        synth = Synthesizer(model="gpt-5.2-chat-latest")
        text = await synth.synthesize(
            original_query="Compare AAPL and MSFT revenue",
            results=[
                {"question": "AAPL revenue", "answer": "$94.9B", "sources": []},
                {"question": "MSFT revenue", "answer": "$64.7B", "sources": []},
            ],
        )

    assert "AAPL" in text
    assert "MSFT" in text
```

**Step 2: Run tests to verify they fail**

Run: `cd Main/backend && uv run python -m pytest tests/test_research_engine.py -v -k "gap_detector or synthesizer"`
Expected: FAIL — `ImportError`

**Step 3: Write the implementation**

Append to `Main/backend/datascraper/research_engine.py`:

```python
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
```

**Step 4: Run tests to verify they pass**

Run: `cd Main/backend && uv run python -m pytest tests/test_research_engine.py -v`
Expected: ALL PASSED (8 tests total)

**Step 5: Commit**

```bash
git add Main/backend/datascraper/research_engine.py Main/backend/tests/test_research_engine.py
git commit -m "feat: add GapDetector and Synthesizer to research engine"
```

---

### Task 5: Add the orchestration loop — `run_iterative_research()`

This is the main entry point that ties all components together: analyze → execute → detect gaps → loop → synthesize.

**Files:**
- Modify: `Main/backend/datascraper/research_engine.py`
- Modify: `Main/backend/tests/test_research_engine.py`

**Step 1: Write the failing tests**

Append to `Main/backend/tests/test_research_engine.py`:

```python
# ── Full orchestration tests ──────────────────────────────────────────

@pytest.mark.asyncio
async def test_run_iterative_simple_query_bypasses():
    """Simple queries should bypass the research engine entirely."""
    from datascraper.research_engine import run_iterative_research

    analyzer_response = MagicMock()
    analyzer_response.choices = [MagicMock()]
    analyzer_response.choices[0].message.content = json.dumps({
        "needs_decomposition": False, "sub_questions": []
    })

    with patch("datascraper.research_engine._call_planner", new_callable=AsyncMock, return_value=analyzer_response):
        result = await run_iterative_research(
            user_input="What is AAPL price?",
            message_list=[],
            model="gpt-5.2-chat-latest",
        )

    # Should return None to signal "use existing single-search path"
    assert result is None


@pytest.mark.asyncio
async def test_run_iterative_full_loop():
    """Complex query runs full loop: analyze → execute → gap detect → synthesize."""
    from datascraper.research_engine import run_iterative_research

    # 1. Analyzer returns decomposition
    analyzer_resp = MagicMock()
    analyzer_resp.choices = [MagicMock()]
    analyzer_resp.choices[0].message.content = json.dumps({
        "needs_decomposition": True,
        "sub_questions": [
            {"question": "AAPL price", "type": "numerical"},
            {"question": "MSFT price", "type": "numerical"},
        ]
    })

    # 2. Gap detector says complete
    gap_resp = MagicMock()
    gap_resp.choices = [MagicMock()]
    gap_resp.choices[0].message.content = json.dumps({
        "complete": True, "gaps": [], "follow_up_queries": []
    })

    # 3. Synthesizer returns final answer
    synth_resp = MagicMock()
    synth_resp.choices = [MagicMock()]
    synth_resp.choices[0].message.content = "AAPL is $150, MSFT is $420."

    planner_calls = [analyzer_resp, gap_resp]
    planner_call_idx = {"i": 0}

    async def mock_planner(*args, **kwargs):
        idx = planner_call_idx["i"]
        planner_call_idx["i"] += 1
        return planner_calls[idx]

    with patch("datascraper.research_engine._call_planner", side_effect=mock_planner), \
         patch("datascraper.research_engine._try_mcp_search", new_callable=AsyncMock, side_effect=["$150", "$420"]), \
         patch("datascraper.research_engine._call_synthesis", new_callable=AsyncMock, return_value=synth_resp):
        result = await run_iterative_research(
            user_input="Compare AAPL and MSFT prices",
            message_list=[],
            model="gpt-5.2-chat-latest",
        )

    assert result is not None
    text, sources, metadata = result
    assert "AAPL" in text
    assert metadata["iterations_used"] == 1
    assert metadata["sub_questions_count"] == 2
```

**Step 2: Run tests to verify they fail**

Run: `cd Main/backend && uv run python -m pytest tests/test_research_engine.py -v -k "run_iterative"`
Expected: FAIL — `ImportError: cannot import name 'run_iterative_research'`

**Step 3: Write the implementation**

Append to `Main/backend/datascraper/research_engine.py`:

```python
# ── 5. Orchestration loop ─────────────────────────────────────────────


async def run_iterative_research(
    user_input: str,
    message_list: list[dict],
    model: str,
    preferred_urls: list[str] = None,
    user_timezone: str = None,
    user_time: str = None,
    time_context: str = "",
) -> Optional[tuple[str, list[dict], dict]]:
    """
    Run the full iterative research loop.

    Returns:
        None if the query is simple (caller should use existing single-search path).
        Otherwise: (synthesized_text, all_sources, metadata_dict)
    """
    cfg = get_research_config()

    # Step 1: Analyze query
    logger.info(f"[RESEARCH] Analyzing query: {user_input[:80]}...")
    analyzer = QueryAnalyzer()
    plan = await analyzer.analyze(user_input, time_context=time_context)

    if not plan["needs_decomposition"]:
        logger.info("[RESEARCH] Simple query — bypassing research engine")
        return None

    logger.info(f"[RESEARCH] Decomposed into {len(plan['sub_questions'])} sub-questions")

    # Step 2-3: Execute + gap detection loop
    executor = ResearchExecutor(
        model=model,
        message_list=message_list,
        preferred_urls=preferred_urls,
        user_timezone=user_timezone,
        user_time=user_time,
        parallel=cfg["parallel_searches"],
    )

    all_results: list[dict] = []
    all_sources: list[dict] = []
    current_plan = plan
    iterations_used = 0

    for iteration in range(1, cfg["max_iterations"] + 1):
        iterations_used = iteration
        logger.info(f"[RESEARCH] Iteration {iteration}/{cfg['max_iterations']}")

        # Execute sub-questions
        results = await executor.execute(current_plan)
        all_results.extend(results)

        # Collect sources
        for r in results:
            all_sources.extend(r.get("sources", []))

        # Gap detection (skip on last iteration — we synthesize regardless)
        if iteration < cfg["max_iterations"]:
            detector = GapDetector()
            gap_result = await detector.detect(
                original_query=user_input,
                plan=plan,  # original plan for context
                results=all_results,
            )

            if gap_result["complete"]:
                logger.info(f"[RESEARCH] Research complete after {iteration} iteration(s)")
                break

            follow_ups = gap_result.get("follow_up_queries", [])
            if not follow_ups:
                logger.info("[RESEARCH] No follow-up queries suggested, completing")
                break

            logger.info(f"[RESEARCH] Gaps found, {len(follow_ups)} follow-up queries")
            current_plan = {"sub_questions": follow_ups}

    # Step 4: Synthesize
    logger.info(f"[RESEARCH] Synthesizing from {len(all_results)} results")
    synthesizer = Synthesizer(model=model)
    final_text = await synthesizer.synthesize(
        original_query=user_input,
        results=all_results,
        time_context=time_context,
    )

    # Deduplicate sources
    seen_urls: set[str] = set()
    deduped_sources = []
    for src in all_sources:
        url = src.get("url")
        if url and url not in seen_urls:
            seen_urls.add(url)
            deduped_sources.append(src)

    metadata = {
        "iterations_used": iterations_used,
        "sub_questions_count": len(plan["sub_questions"]),
        "total_results": len(all_results),
        "mcp_hits": sum(1 for r in all_results if r.get("source") == "mcp"),
        "web_hits": sum(1 for r in all_results if r.get("source") == "web"),
    }

    return final_text, deduped_sources, metadata
```

**Step 4: Run tests to verify they pass**

Run: `cd Main/backend && uv run python -m pytest tests/test_research_engine.py -v`
Expected: ALL PASSED (10 tests total)

**Step 5: Commit**

```bash
git add Main/backend/datascraper/research_engine.py Main/backend/tests/test_research_engine.py
git commit -m "feat: add orchestration loop (run_iterative_research)"
```

---

### Task 6: Integrate research engine into datascraper.py

Hook `run_iterative_research()` into the existing `create_advanced_response()` function. Simple queries bypass the engine (zero overhead). Complex queries get the full iterative treatment.

**Files:**
- Modify: `Main/backend/datascraper/datascraper.py`

**Step 1: Add the integration**

In `create_advanced_response()` (around line 680, after the MCP-first block), add the research engine call **before** the single web search:

```python
    # --- Iterative research for complex queries (non-streaming) ---
    if not stream:
        try:
            from datascraper.research_engine import run_iterative_research
            from datascraper.market_time import build_market_time_context

            time_ctx = build_market_time_context(user_timezone, user_time) or ""

            research_result = asyncio.run(run_iterative_research(
                user_input=user_input,
                message_list=message_list,
                model=actual_model,
                preferred_urls=preferred_urls,
                user_timezone=user_timezone,
                user_time=user_time,
                time_context=time_ctx,
            ))

            if research_result is not None:
                final_text, sources, meta = research_result
                logging.info(
                    f"[RESEARCH ENGINE] Completed: {meta['iterations_used']} iterations, "
                    f"{meta['sub_questions_count']} sub-questions, "
                    f"{meta['mcp_hits']} MCP / {meta['web_hits']} web"
                )
                qt.set_data_source("iterative_research")
                qt.flag("iterative_research", **meta)
                qt.complete(final_text)
                return final_text, sources
            # If None, query was simple — fall through to single web search
        except Exception as exc:
            logging.warning(f"[RESEARCH ENGINE] Failed, falling back to single search: {exc}")
```

This goes after the MCP-first block (line ~680) and before `actual_model, preferred_urls = _prepare_advanced_search_inputs(...)` (line ~682). Note: `_prepare_advanced_search_inputs` needs to be called **before** the research engine since it resolves the actual model. Adjust the insertion point to be after model preparation.

**Exact insertion point**: After line 682 (`actual_model, preferred_urls = _prepare_advanced_search_inputs(model, preferred_links)`) and before the `try: if stream:` block (line ~684).

**Step 2: Verify syntax**

Run: `cd Main/backend && uv run python -c "import ast; ast.parse(open('datascraper/datascraper.py').read()); print('OK')"`
Expected: `OK`

**Step 3: Run existing tests to verify no regression**

Run: `cd Main/backend && uv run python -m pytest tests/ -v --timeout=30`
Expected: All existing tests still pass

**Step 4: Commit**

```bash
git add Main/backend/datascraper/datascraper.py
git commit -m "feat: integrate research engine into create_advanced_response"
```

---

### Task 7: Add streaming support (research status events)

For the streaming path, send "Researching..." status events while the research engine works, then stream the final answer.

**Files:**
- Modify: `Main/backend/datascraper/datascraper.py`

**Step 1: Add research engine to streaming path**

In `create_advanced_response_streaming()` (around line 778), after the MCP-first streaming check, add:

```python
    # --- Iterative research for complex queries (streaming path) ---
    try:
        from datascraper.research_engine import run_iterative_research
        from datascraper.market_time import build_market_time_context

        time_ctx = build_market_time_context(user_timezone, user_time) or ""
        actual_model_stream, preferred_urls_stream = _prepare_advanced_search_inputs(model, preferred_links)

        research_result = asyncio.run(run_iterative_research(
            user_input=user_input,
            message_list=message_list,
            model=actual_model_stream,
            preferred_urls=preferred_urls_stream,
            user_timezone=user_timezone,
            user_time=user_time,
            time_context=time_ctx,
        ))

        if research_result is not None:
            final_text, sources, meta = research_result
            logging.info(f"[RESEARCH ENGINE STREAM] Completed: {meta}")
            state: Dict[str, Any] = {
                "final_output": final_text,
                "used_urls": [s.get("url") for s in sources if s.get("url")],
                "used_sources": sources,
            }

            async def _research_stream() -> AsyncIterator[tuple[str, list[str]]]:
                yield final_text, sources

            return _research_stream(), state
    except Exception as exc:
        logging.warning(f"[RESEARCH ENGINE STREAM] Failed, falling back: {exc}")
```

Insert this after the MCP-first streaming check and before the normal `_prepare_advanced_search_inputs` call for the single-search path.

**Step 2: Verify syntax**

Run: `cd Main/backend && uv run python -c "import ast; ast.parse(open('datascraper/datascraper.py').read()); print('OK')"`
Expected: `OK`

**Step 3: Commit**

```bash
git add Main/backend/datascraper/datascraper.py
git commit -m "feat: add research engine to streaming path"
```

---

### Task 8: Verify all tests pass and syntax check all files

**Step 1: Syntax check all modified files**

```bash
cd Main/backend && uv run python -c "
import ast
files = [
    'datascraper/models_config.py',
    'datascraper/research_engine.py',
    'datascraper/datascraper.py',
]
for f in files:
    ast.parse(open(f).read())
    print(f'OK: {f}')
print('All files pass syntax check')
"
```

**Step 2: Run full test suite**

```bash
cd Main/backend && uv run python -m pytest tests/ -v --timeout=60
```

**Step 3: Run Django system checks**

```bash
cd Main/backend && uv run python manage.py check
```

**Step 4: Final commit if any cleanup needed**

```bash
git add -A && git status
```
