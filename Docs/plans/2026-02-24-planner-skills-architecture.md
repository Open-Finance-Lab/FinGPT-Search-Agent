# Planner + Skills Architecture Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add a planning layer that constrains the FinGPT search agent's tools and behavior per-query, eliminating the "51 tools for every query" problem.

**Architecture:** A code-heuristic Planner analyzes each query (intent + pre-scraped content + domain) and selects a Skill. Each Skill defines a static workflow: allowed tools, max turns, and focused instructions. The Skill Executor creates a constrained agent via the existing OpenAI Agents SDK, passing only the tools and turn limit the plan specifies. Unmatched queries fall back to the current full-autonomy behavior.

**Tech Stack:** Python 3.12, OpenAI Agents SDK (`agents` library), Django, existing MCP infrastructure

**Branch:** `feat/planner-skills` (from `fingpt_backend_dev`)

---

## Verified Architecture Facts

These were confirmed by reading the actual source code:

| Claim | Verified | Source |
|-------|----------|--------|
| `create_fin_agent` collects ALL tools unconditionally | Yes | `agent.py:120-191` — extends url_tools, playwright_tools, calculator_tools, then all MCP tools |
| `FunctionTool` has `.name` attribute | Yes | Tested: `FunctionTool.name` returns function name |
| Pre-scraped content uses `[CURRENT PAGE CONTENT...]` prefix | Yes | `unified_context_manager.py:316` |
| Pre-scraped content lands in `extracted_system_prompt` | Yes | `datascraper.py:1158-1164` — SYSTEM_PREFIX extraction |
| `Runner.run`/`run_streamed` accept `max_turns` | Yes | `datascraper.py:1238,1245` |
| 4 MCP servers: filesystem, sec-edgar, yahoo-finance, tradingview | Yes | `mcp_server_config.json` |
| Yahoo Finance: 9 tools, TradingView: 7 tools | Yes | `yahoo_finance_server.py:40-49`, `tradingview/server.py:38-46` |
| Direct tools: 6 (2 url + 3 playwright + 1 calculator) | Yes | `url_tools.py:281-283`, `playwright_tools.py:283-285`, `calculator_tool.py:122-124` |
| `PromptBuilder.build()` = core.md + site_skill + user_context + time + system_prompt | Yes | `prompt_builder.py:32-74` |
| Agent insertion point: `datascraper.py:1193` (before `create_fin_agent`) | Yes | Lines 1154-1200 in `_stream()` |

## File Structure

```
Main/backend/
  planner/
    __init__.py
    plan.py              # ExecutionPlan dataclass
    planner.py           # Planner class — heuristic skill selection
    skills/
      __init__.py
      base.py            # BaseSkill ABC
      registry.py        # SkillRegistry — lookup + registration
      summarize_page.py  # Zero-tool, single-turn summarization
      stock_fundamentals.py
      options_analysis.py
      financial_statements.py
      technical_analysis.py
      web_research.py    # Fallback — current behavior
  tests/
    test_planner.py      # Planner heuristics tests
    test_skills.py       # Skill config + registry tests
    test_agent_tool_filtering.py  # create_fin_agent allowed_tools tests
```

---

## Task 1: ExecutionPlan dataclass + BaseSkill ABC

**Files:**
- Create: `Main/backend/planner/__init__.py`
- Create: `Main/backend/planner/plan.py`
- Create: `Main/backend/planner/skills/__init__.py`
- Create: `Main/backend/planner/skills/base.py`
- Test: `Main/backend/tests/test_skills.py`

**Step 1: Write the failing test**

```python
# tests/test_skills.py
import pytest
from planner.plan import ExecutionPlan
from planner.skills.base import BaseSkill


class TestExecutionPlan:
    def test_creation_with_defaults(self):
        plan = ExecutionPlan(skill_name="test")
        assert plan.skill_name == "test"
        assert plan.tools_allowed is None  # None = all tools
        assert plan.max_turns == 10
        assert plan.instructions is None

    def test_zero_tool_plan(self):
        plan = ExecutionPlan(
            skill_name="summarize_page",
            tools_allowed=[],
            max_turns=1,
            instructions="Summarize this content.",
        )
        assert plan.tools_allowed == []
        assert plan.max_turns == 1

    def test_filtered_tool_plan(self):
        plan = ExecutionPlan(
            skill_name="stock_fundamentals",
            tools_allowed=["get_stock_info", "get_stock_history", "calculate"],
            max_turns=3,
        )
        assert len(plan.tools_allowed) == 3
        assert "get_stock_info" in plan.tools_allowed


class TestBaseSkill:
    def test_cannot_instantiate_directly(self):
        with pytest.raises(TypeError):
            BaseSkill()

    def test_concrete_skill_must_implement_methods(self):
        class IncompleteSkill(BaseSkill):
            pass

        with pytest.raises(TypeError):
            IncompleteSkill()
```

**Step 2: Run test to verify it fails**

Run: `cd Main/backend && python3 -m pytest tests/test_skills.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'planner'`

**Step 3: Write minimal implementation**

```python
# planner/__init__.py
```

```python
# planner/plan.py
from dataclasses import dataclass, field
from typing import Optional, List


@dataclass
class ExecutionPlan:
    """Structured execution plan output by the Planner."""
    skill_name: str
    tools_allowed: Optional[List[str]] = None      # None = all tools (fallback)
    max_turns: int = 10
    instructions: Optional[str] = None             # If set, replaces PromptBuilder output
```

```python
# planner/skills/__init__.py
```

```python
# planner/skills/base.py
from abc import ABC, abstractmethod
from typing import Optional, List


class BaseSkill(ABC):
    """Abstract base for all skills."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique skill identifier."""
        ...

    @property
    @abstractmethod
    def tools_allowed(self) -> Optional[List[str]]:
        """Tool names this skill may use. None = all, [] = none."""
        ...

    @property
    @abstractmethod
    def max_turns(self) -> int:
        """Maximum agent turns for this skill."""
        ...

    @abstractmethod
    def matches(self, query: str, *, has_prescraped: bool, domain: str | None) -> float:
        """
        Return a confidence score 0.0-1.0 that this skill handles the query.
        0.0 = definitely not, 1.0 = perfect match.
        """
        ...

    def build_instructions(self, *, pre_scraped_content: str | None = None) -> str | None:
        """
        Return custom instructions, or None to use the default PromptBuilder.
        Override in skills that need a focused prompt (e.g. SummarizePageSkill).
        """
        return None
```

**Step 4: Run test to verify it passes**

Run: `cd Main/backend && python3 -m pytest tests/test_skills.py -v`
Expected: PASS (5 tests)

**Step 5: Commit**

```bash
git add Main/backend/planner/ Main/backend/tests/test_skills.py
git commit -m "feat(planner): add ExecutionPlan dataclass and BaseSkill ABC"
```

---

## Task 2: SummarizePageSkill

**Files:**
- Create: `Main/backend/planner/skills/summarize_page.py`
- Modify: `Main/backend/tests/test_skills.py`

**Step 1: Write the failing test**

Append to `tests/test_skills.py`:

```python
from planner.skills.summarize_page import SummarizePageSkill


class TestSummarizePageSkill:
    def setup_method(self):
        self.skill = SummarizePageSkill()

    def test_name(self):
        assert self.skill.name == "summarize_page"

    def test_no_tools(self):
        assert self.skill.tools_allowed == []

    def test_single_turn(self):
        assert self.skill.max_turns == 1

    def test_matches_summarize_with_prescraped(self):
        score = self.skill.matches("summarize this page", has_prescraped=True, domain=None)
        assert score >= 0.8

    def test_matches_explain_with_prescraped(self):
        score = self.skill.matches("what does this article say?", has_prescraped=True, domain=None)
        assert score >= 0.7

    def test_no_match_without_prescraped(self):
        score = self.skill.matches("summarize this page", has_prescraped=False, domain=None)
        assert score == 0.0

    def test_no_match_stock_query(self):
        score = self.skill.matches("what is AAPL stock price?", has_prescraped=True, domain=None)
        assert score < 0.5

    def test_build_instructions_includes_content(self):
        content = "Page about earnings report..."
        instructions = self.skill.build_instructions(pre_scraped_content=content)
        assert content in instructions
        assert "summarize" in instructions.lower() or "content" in instructions.lower()

    def test_build_instructions_none_without_content(self):
        instructions = self.skill.build_instructions(pre_scraped_content=None)
        assert instructions is None
```

**Step 2: Run test to verify it fails**

Run: `cd Main/backend && python3 -m pytest tests/test_skills.py::TestSummarizePageSkill -v`
Expected: FAIL with `ModuleNotFoundError`

**Step 3: Write minimal implementation**

```python
# planner/skills/summarize_page.py
import re
from typing import Optional, List
from .base import BaseSkill

# Patterns that indicate the user wants to understand the current page content
_SUMMARIZE_PATTERNS = [
    r"\bsummar",          # summarize, summary
    r"\bexplain\b",
    r"\bwhat does (this|the) (page|article|post|report|story)",
    r"\bwhat('s| is) (this|the) (page|article) about",
    r"\btl;?dr\b",
    r"\bkey (points|takeaways|highlights)\b",
    r"\bbreak(ing)? (this |it )?down\b",
    r"\bgive me (a |the )?(gist|overview|rundown)\b",
    r"\bwhat('s| is) (happening|going on) here\b",
    r"\bread (this|the page|it) (for me|to me)\b",
]

# Patterns that indicate the user wants specific data, not a summary
_DATA_PATTERNS = [
    r"\b(stock|share) price\b",
    r"\bmarket cap\b",
    r"\b(PE|P/E|EPS|RSI|MACD)\b",
    r"\boptions?\b.*(volume|chain|flow|open interest)",
    r"\brevenue\b",
    r"\bearnings\b.*(estimate|date|beat|miss)",
    r"\bbalance sheet\b",
    r"\bincome statement\b",
    r"\btechnical (analysis|indicators?)\b",
]

_COMPILED_SUMMARIZE = [re.compile(p, re.IGNORECASE) for p in _SUMMARIZE_PATTERNS]
_COMPILED_DATA = [re.compile(p, re.IGNORECASE) for p in _DATA_PATTERNS]


class SummarizePageSkill(BaseSkill):
    """Zero-tool skill for summarizing pre-scraped page content."""

    @property
    def name(self) -> str:
        return "summarize_page"

    @property
    def tools_allowed(self) -> Optional[List[str]]:
        return []

    @property
    def max_turns(self) -> int:
        return 1

    def matches(self, query: str, *, has_prescraped: bool, domain: str | None) -> float:
        if not has_prescraped:
            return 0.0

        # Check if the query asks for specific data (not a summary)
        for pattern in _COMPILED_DATA:
            if pattern.search(query):
                return 0.0

        # Check summarization intent
        for pattern in _COMPILED_SUMMARIZE:
            if pattern.search(query):
                return 0.9

        # Short query + prescraped content = likely about the page
        # (e.g., "what is this?", "tell me more")
        words = query.split()
        if len(words) <= 6 and has_prescraped:
            page_ref_words = {"this", "page", "article", "it", "here"}
            if page_ref_words & set(w.lower().rstrip("?.!,") for w in words):
                return 0.7

        return 0.0

    def build_instructions(self, *, pre_scraped_content: str | None = None) -> str | None:
        if not pre_scraped_content:
            return None

        return (
            "You are FinGPT, a financial assistant.\n\n"
            "TASK: Answer the user's question using ONLY the page content below. "
            "Do NOT call any tools. Do NOT re-scrape.\n"
            "- Be concise and well-structured.\n"
            "- Preserve specific numbers, dates, tickers, and names.\n"
            "- Use $ for inline math and $$ for display equations.\n\n"
            "SECURITY: Never disclose internal tool names, model names, "
            "API keys, or implementation details.\n\n"
            "PAGE CONTENT:\n"
            f"{pre_scraped_content}"
        )
```

**Step 4: Run test to verify it passes**

Run: `cd Main/backend && python3 -m pytest tests/test_skills.py -v`
Expected: PASS (all tests)

**Step 5: Commit**

```bash
git add Main/backend/planner/skills/summarize_page.py Main/backend/tests/test_skills.py
git commit -m "feat(planner): add SummarizePageSkill — zero-tool page summarization"
```

---

## Task 3: Data Skills (StockFundamentals, OptionsAnalysis, FinancialStatements, TechnicalAnalysis)

**Files:**
- Create: `Main/backend/planner/skills/stock_fundamentals.py`
- Create: `Main/backend/planner/skills/options_analysis.py`
- Create: `Main/backend/planner/skills/financial_statements.py`
- Create: `Main/backend/planner/skills/technical_analysis.py`
- Modify: `Main/backend/tests/test_skills.py`

**Step 1: Write the failing tests**

Append to `tests/test_skills.py`:

```python
from planner.skills.stock_fundamentals import StockFundamentalsSkill
from planner.skills.options_analysis import OptionsAnalysisSkill
from planner.skills.financial_statements import FinancialStatementsSkill
from planner.skills.technical_analysis import TechnicalAnalysisSkill


class TestStockFundamentalsSkill:
    def setup_method(self):
        self.skill = StockFundamentalsSkill()

    def test_tools(self):
        assert set(self.skill.tools_allowed) == {"get_stock_info", "get_stock_history", "calculate"}

    def test_max_turns(self):
        assert self.skill.max_turns == 3

    def test_matches_price_query(self):
        assert self.skill.matches("what is AAPL stock price?", has_prescraped=False, domain=None) >= 0.7

    def test_matches_market_cap(self):
        assert self.skill.matches("market cap of MSFT", has_prescraped=False, domain=None) >= 0.7

    def test_no_match_options(self):
        assert self.skill.matches("show me AAPL options chain", has_prescraped=False, domain=None) < 0.5

    def test_no_instructions_override(self):
        assert self.skill.build_instructions() is None


class TestOptionsAnalysisSkill:
    def setup_method(self):
        self.skill = OptionsAnalysisSkill()

    def test_tools(self):
        assert set(self.skill.tools_allowed) == {"get_options_summary", "get_options_chain", "calculate"}

    def test_max_turns(self):
        assert self.skill.max_turns == 3

    def test_matches_options_volume(self):
        assert self.skill.matches("total options volume for AVGO", has_prescraped=False, domain=None) >= 0.7

    def test_matches_put_call_ratio(self):
        assert self.skill.matches("put call ratio for TSLA", has_prescraped=False, domain=None) >= 0.7


class TestFinancialStatementsSkill:
    def setup_method(self):
        self.skill = FinancialStatementsSkill()

    def test_tools(self):
        assert set(self.skill.tools_allowed) == {"get_stock_financials", "get_earnings_info", "calculate"}

    def test_max_turns(self):
        assert self.skill.max_turns == 3

    def test_matches_revenue(self):
        assert self.skill.matches("what was AAPL revenue last quarter?", has_prescraped=False, domain=None) >= 0.7

    def test_matches_earnings(self):
        assert self.skill.matches("when are MSFT earnings?", has_prescraped=False, domain=None) >= 0.7


class TestTechnicalAnalysisSkill:
    def setup_method(self):
        self.skill = TechnicalAnalysisSkill()

    def test_tools_include_tradingview(self):
        tools = self.skill.tools_allowed
        assert "get_coin_analysis" in tools
        assert "calculate" in tools

    def test_max_turns(self):
        assert self.skill.max_turns == 3

    def test_matches_rsi(self):
        assert self.skill.matches("what is the RSI for AAPL?", has_prescraped=False, domain=None) >= 0.7

    def test_matches_macd(self):
        assert self.skill.matches("show MACD for BTC", has_prescraped=False, domain=None) >= 0.7
```

**Step 2: Run test to verify it fails**

Run: `cd Main/backend && python3 -m pytest tests/test_skills.py -k "TestStock or TestOptions or TestFinancial or TestTechnical" -v`
Expected: FAIL with `ModuleNotFoundError`

**Step 3: Write implementations**

```python
# planner/skills/stock_fundamentals.py
import re
from typing import Optional, List
from .base import BaseSkill

_PATTERNS = [
    r"\b(stock|share) price\b",
    r"\bmarket cap(italization)?\b",
    r"\b(PE|P/E) ratio\b",
    r"\bdividend (yield|rate)\b",
    r"\b52[- ]?week (high|low|range)\b",
    r"\bhow (is|are) .{1,20} (doing|trading|performing)\b",
    r"\bcurrent (price|value|quote)\b",
    r"\bprice (of|for)\b",
    r"\bquote (for|of)\b",
    r"\bvolume\b(?!.*option)",  # volume but not "options volume"
    r"\bbeta\b",
    r"\bshares outstanding\b",
    r"\bfloat\b.*\bshares\b",
    r"\b(day|intraday) (range|high|low)\b",
    r"\bpre[- ]?market\b",
    r"\bafter[- ]?hours?\b",
]
_COMPILED = [re.compile(p, re.IGNORECASE) for p in _PATTERNS]


class StockFundamentalsSkill(BaseSkill):
    @property
    def name(self) -> str:
        return "stock_fundamentals"

    @property
    def tools_allowed(self) -> Optional[List[str]]:
        return ["get_stock_info", "get_stock_history", "calculate"]

    @property
    def max_turns(self) -> int:
        return 3

    def matches(self, query: str, *, has_prescraped: bool, domain: str | None) -> float:
        for p in _COMPILED:
            if p.search(query):
                return 0.8
        return 0.0
```

```python
# planner/skills/options_analysis.py
import re
from typing import Optional, List
from .base import BaseSkill

_PATTERNS = [
    r"\boptions?\b.*(volume|chain|flow|data|activity|summary)",
    r"\b(put|call)[/ ](call|put)\b",
    r"\bopen interest\b",
    r"\b(options?|puts?|calls?)\b.*(expir|strike|premium)",
    r"\bimplied volatility\b",
    r"\biv\b.*\b(rank|percentile)\b",
    r"\boptions? (for|on|of)\b",
    r"\b(total|aggregate) (options?|puts?|calls?) (volume|oi)\b",
]
_COMPILED = [re.compile(p, re.IGNORECASE) for p in _PATTERNS]


class OptionsAnalysisSkill(BaseSkill):
    @property
    def name(self) -> str:
        return "options_analysis"

    @property
    def tools_allowed(self) -> Optional[List[str]]:
        return ["get_options_summary", "get_options_chain", "calculate"]

    @property
    def max_turns(self) -> int:
        return 3

    def matches(self, query: str, *, has_prescraped: bool, domain: str | None) -> float:
        for p in _COMPILED:
            if p.search(query):
                return 0.8
        return 0.0
```

```python
# planner/skills/financial_statements.py
import re
from typing import Optional, List
from .base import BaseSkill

_PATTERNS = [
    r"\brevenue\b",
    r"\b(net )?income\b",
    r"\bearnings\b",
    r"\b(income|balance|cash flow) statement\b",
    r"\bbalance sheet\b",
    r"\bEPS\b",
    r"\bEBITDA\b",
    r"\bprofit margin\b",
    r"\boperating (income|expenses?|margin)\b",
    r"\bgross (profit|margin)\b",
    r"\bfree cash flow\b",
    r"\bdebt[- ]to[- ]equity\b",
    r"\b(quarterly|annual) (results|report|financials)\b",
    r"\b(next|upcoming|when).{0,15}earnings\b",
    r"\bgrowth (rate|estimate|projection)\b",
]
_COMPILED = [re.compile(p, re.IGNORECASE) for p in _PATTERNS]


class FinancialStatementsSkill(BaseSkill):
    @property
    def name(self) -> str:
        return "financial_statements"

    @property
    def tools_allowed(self) -> Optional[List[str]]:
        return ["get_stock_financials", "get_earnings_info", "calculate"]

    @property
    def max_turns(self) -> int:
        return 3

    def matches(self, query: str, *, has_prescraped: bool, domain: str | None) -> float:
        for p in _COMPILED:
            if p.search(query):
                return 0.8
        return 0.0
```

```python
# planner/skills/technical_analysis.py
import re
from typing import Optional, List
from .base import BaseSkill

_PATTERNS = [
    r"\bRSI\b",
    r"\bMACD\b",
    r"\b(bollinger|bb) band",
    r"\bmoving average\b",
    r"\b(SMA|EMA)\b",
    r"\bADX\b",
    r"\bstochastic\b",
    r"\btechnical (analysis|indicator)",
    r"\b(support|resistance) (level|line|zone)\b",
    r"\b(overbought|oversold)\b",
    r"\b(golden|death) cross\b",
    r"\bcandlestick pattern\b",
    r"\bcandle pattern\b",
    r"\b(top |biggest )?(gainers?|losers?)\b",
]
_COMPILED = [re.compile(p, re.IGNORECASE) for p in _PATTERNS]


class TechnicalAnalysisSkill(BaseSkill):
    @property
    def name(self) -> str:
        return "technical_analysis"

    @property
    def tools_allowed(self) -> Optional[List[str]]:
        return [
            "get_coin_analysis",
            "get_top_gainers",
            "get_top_losers",
            "get_bollinger_scan",
            "get_rating_filter",
            "get_consecutive_candles",
            "get_advanced_candle_pattern",
            "calculate",
        ]

    @property
    def max_turns(self) -> int:
        return 3

    def matches(self, query: str, *, has_prescraped: bool, domain: str | None) -> float:
        for p in _COMPILED:
            if p.search(query):
                return 0.8
        return 0.0
```

**Step 4: Run test to verify it passes**

Run: `cd Main/backend && python3 -m pytest tests/test_skills.py -v`
Expected: PASS (all tests)

**Step 5: Commit**

```bash
git add Main/backend/planner/skills/stock_fundamentals.py \
        Main/backend/planner/skills/options_analysis.py \
        Main/backend/planner/skills/financial_statements.py \
        Main/backend/planner/skills/technical_analysis.py \
        Main/backend/tests/test_skills.py
git commit -m "feat(planner): add data skills — fundamentals, options, financials, technical"
```

---

## Task 4: WebResearchSkill (fallback) + SkillRegistry

**Files:**
- Create: `Main/backend/planner/skills/web_research.py`
- Create: `Main/backend/planner/skills/registry.py`
- Modify: `Main/backend/tests/test_skills.py`

**Step 1: Write the failing test**

Append to `tests/test_skills.py`:

```python
from planner.skills.web_research import WebResearchSkill
from planner.skills.registry import SkillRegistry


class TestWebResearchSkill:
    def setup_method(self):
        self.skill = WebResearchSkill()

    def test_all_tools(self):
        assert self.skill.tools_allowed is None  # None = all tools

    def test_max_turns(self):
        assert self.skill.max_turns == 10

    def test_always_matches_at_baseline(self):
        """Fallback skill always returns a low but nonzero score."""
        score = self.skill.matches("random query", has_prescraped=False, domain=None)
        assert 0.0 < score <= 0.2


class TestSkillRegistry:
    def setup_method(self):
        self.registry = SkillRegistry()

    def test_all_skills_registered(self):
        names = {s.name for s in self.registry.skills}
        assert names == {
            "summarize_page",
            "stock_fundamentals",
            "options_analysis",
            "financial_statements",
            "technical_analysis",
            "web_research",
        }

    def test_best_match_summarize(self):
        skill = self.registry.best_match("summarize this page", has_prescraped=True, domain=None)
        assert skill.name == "summarize_page"

    def test_best_match_stock_price(self):
        skill = self.registry.best_match("what is AAPL stock price?", has_prescraped=False, domain=None)
        assert skill.name == "stock_fundamentals"

    def test_best_match_fallback(self):
        skill = self.registry.best_match(
            "find me some interesting investment ideas for biotech sector",
            has_prescraped=False,
            domain=None,
        )
        assert skill.name == "web_research"

    def test_best_match_options(self):
        skill = self.registry.best_match("options volume for AVGO", has_prescraped=False, domain=None)
        assert skill.name == "options_analysis"

    def test_best_match_earnings(self):
        skill = self.registry.best_match("when are AAPL earnings?", has_prescraped=False, domain=None)
        assert skill.name == "financial_statements"

    def test_best_match_rsi(self):
        skill = self.registry.best_match("what is RSI for TSLA?", has_prescraped=False, domain=None)
        assert skill.name == "technical_analysis"
```

**Step 2: Run test to verify it fails**

Run: `cd Main/backend && python3 -m pytest tests/test_skills.py -k "TestWebResearch or TestSkillRegistry" -v`
Expected: FAIL with `ModuleNotFoundError`

**Step 3: Write implementations**

```python
# planner/skills/web_research.py
from typing import Optional, List
from .base import BaseSkill


class WebResearchSkill(BaseSkill):
    """Fallback skill — current full-autonomy behavior."""

    @property
    def name(self) -> str:
        return "web_research"

    @property
    def tools_allowed(self) -> Optional[List[str]]:
        return None  # All tools

    @property
    def max_turns(self) -> int:
        return 10

    def matches(self, query: str, *, has_prescraped: bool, domain: str | None) -> float:
        return 0.1  # Always matches as a fallback, but with lowest priority
```

```python
# planner/skills/registry.py
import logging
from typing import Optional
from .base import BaseSkill
from .summarize_page import SummarizePageSkill
from .stock_fundamentals import StockFundamentalsSkill
from .options_analysis import OptionsAnalysisSkill
from .financial_statements import FinancialStatementsSkill
from .technical_analysis import TechnicalAnalysisSkill
from .web_research import WebResearchSkill

logger = logging.getLogger(__name__)


class SkillRegistry:
    """Maintains a ranked list of skills and selects the best match."""

    def __init__(self):
        self.skills: list[BaseSkill] = [
            SummarizePageSkill(),
            StockFundamentalsSkill(),
            OptionsAnalysisSkill(),
            FinancialStatementsSkill(),
            TechnicalAnalysisSkill(),
            WebResearchSkill(),  # Always last — fallback
        ]

    def best_match(
        self,
        query: str,
        *,
        has_prescraped: bool,
        domain: str | None,
    ) -> BaseSkill:
        """Return the skill with the highest confidence score."""
        best_skill = self.skills[-1]  # WebResearchSkill fallback
        best_score = 0.0

        for skill in self.skills:
            score = skill.matches(query, has_prescraped=has_prescraped, domain=domain)
            if score > best_score:
                best_score = score
                best_skill = skill

        logger.info(f"[SkillRegistry] Selected '{best_skill.name}' (score={best_score:.2f}) for query: {query[:80]}")
        return best_skill
```

**Step 4: Run test to verify it passes**

Run: `cd Main/backend && python3 -m pytest tests/test_skills.py -v`
Expected: PASS (all tests)

**Step 5: Commit**

```bash
git add Main/backend/planner/skills/web_research.py \
        Main/backend/planner/skills/registry.py \
        Main/backend/tests/test_skills.py
git commit -m "feat(planner): add WebResearchSkill fallback and SkillRegistry"
```

---

## Task 5: Planner class

**Files:**
- Create: `Main/backend/planner/planner.py`
- Create: `Main/backend/tests/test_planner.py`

**Step 1: Write the failing test**

```python
# tests/test_planner.py
import pytest
from planner.planner import Planner
from planner.plan import ExecutionPlan


class TestPlanner:
    def setup_method(self):
        self.planner = Planner()

    def test_plan_returns_execution_plan(self):
        plan = self.planner.plan(
            user_query="summarize this page",
            system_prompt="[CURRENT PAGE CONTENT - Already scraped, do NOT re-scrape]:\n- From https://example.com:\nSome content here",
            domain="example.com",
        )
        assert isinstance(plan, ExecutionPlan)

    def test_summarize_plan_no_tools(self):
        plan = self.planner.plan(
            user_query="what does this article say?",
            system_prompt="[CURRENT PAGE CONTENT - Already scraped, do NOT re-scrape]:\n- From https://example.com:\nArticle about earnings...",
            domain="example.com",
        )
        assert plan.skill_name == "summarize_page"
        assert plan.tools_allowed == []
        assert plan.max_turns == 1
        assert plan.instructions is not None
        assert "Article about earnings" in plan.instructions

    def test_stock_price_plan(self):
        plan = self.planner.plan(
            user_query="what is AAPL stock price?",
            system_prompt=None,
            domain="finance.yahoo.com",
        )
        assert plan.skill_name == "stock_fundamentals"
        assert "get_stock_info" in plan.tools_allowed
        assert plan.max_turns == 3
        assert plan.instructions is None  # Uses default PromptBuilder

    def test_fallback_plan(self):
        plan = self.planner.plan(
            user_query="find me biotech investment ideas",
            system_prompt=None,
            domain=None,
        )
        assert plan.skill_name == "web_research"
        assert plan.tools_allowed is None  # All tools
        assert plan.max_turns == 10

    def test_prescraped_detection(self):
        """Planner correctly detects pre-scraped content in system_prompt."""
        plan = self.planner.plan(
            user_query="summarize this",
            system_prompt="[CURRENT PAGE CONTENT - Already scraped, do NOT re-scrape]:\n- From url:\nContent",
            domain=None,
        )
        assert plan.skill_name == "summarize_page"

    def test_no_prescraped_detection(self):
        """Planner detects no pre-scraped content when absent."""
        plan = self.planner.plan(
            user_query="summarize this",
            system_prompt="Some other system prompt without page content",
            domain=None,
        )
        # Without prescraped, summarize_page won't match → fallback
        assert plan.skill_name == "web_research"

    def test_options_plan(self):
        plan = self.planner.plan(
            user_query="show me options volume for AVGO",
            system_prompt=None,
            domain="finance.yahoo.com",
        )
        assert plan.skill_name == "options_analysis"
        assert "get_options_summary" in plan.tools_allowed

    def test_earnings_plan(self):
        plan = self.planner.plan(
            user_query="when are MSFT earnings and what's the EPS estimate?",
            system_prompt=None,
            domain=None,
        )
        assert plan.skill_name == "financial_statements"
        assert "get_earnings_info" in plan.tools_allowed

    def test_technical_analysis_plan(self):
        plan = self.planner.plan(
            user_query="what's the RSI for BTC?",
            system_prompt=None,
            domain=None,
        )
        assert plan.skill_name == "technical_analysis"
```

**Step 2: Run test to verify it fails**

Run: `cd Main/backend && python3 -m pytest tests/test_planner.py -v`
Expected: FAIL with `ModuleNotFoundError`

**Step 3: Write implementation**

```python
# planner/planner.py
import logging
from typing import Optional
from .plan import ExecutionPlan
from .skills.registry import SkillRegistry

logger = logging.getLogger(__name__)

_PRESCRAPED_MARKER = "[CURRENT PAGE CONTENT"


class Planner:
    """
    Analyzes a user query and produces an ExecutionPlan.

    v1: Code heuristics (no LLM call). Fast, deterministic, zero API cost.
    """

    def __init__(self):
        self._registry = SkillRegistry()

    def plan(
        self,
        user_query: str,
        system_prompt: Optional[str],
        domain: Optional[str],
    ) -> ExecutionPlan:
        """
        Produce an ExecutionPlan for the given query.

        Args:
            user_query: The user's latest message.
            system_prompt: The extracted system prompt (may contain pre-scraped content).
            domain: The domain extracted from the current URL (e.g. "finance.yahoo.com").
        """
        has_prescraped = self._has_prescraped_content(system_prompt)
        pre_scraped_content = self._extract_prescraped(system_prompt) if has_prescraped else None

        skill = self._registry.best_match(
            user_query,
            has_prescraped=has_prescraped,
            domain=domain,
        )

        instructions = skill.build_instructions(pre_scraped_content=pre_scraped_content)

        plan = ExecutionPlan(
            skill_name=skill.name,
            tools_allowed=skill.tools_allowed,
            max_turns=skill.max_turns,
            instructions=instructions,
        )

        logger.info(
            f"[Planner] plan={plan.skill_name} tools={len(plan.tools_allowed) if plan.tools_allowed is not None else 'ALL'} "
            f"turns={plan.max_turns} has_instructions={'yes' if plan.instructions else 'no'}"
        )
        return plan

    @staticmethod
    def _has_prescraped_content(system_prompt: Optional[str]) -> bool:
        if not system_prompt:
            return False
        return _PRESCRAPED_MARKER in system_prompt

    @staticmethod
    def _extract_prescraped(system_prompt: Optional[str]) -> Optional[str]:
        """Extract the pre-scraped page content from the system prompt."""
        if not system_prompt:
            return None

        idx = system_prompt.find(_PRESCRAPED_MARKER)
        if idx == -1:
            return None

        # Content starts after the marker line
        content = system_prompt[idx:]
        return content
```

**Step 4: Run test to verify it passes**

Run: `cd Main/backend && python3 -m pytest tests/test_planner.py -v`
Expected: PASS (9 tests)

**Step 5: Commit**

```bash
git add Main/backend/planner/planner.py Main/backend/tests/test_planner.py
git commit -m "feat(planner): add Planner with code-heuristic skill selection"
```

---

## Task 6: Add `allowed_tools` + `instructions_override` to `create_fin_agent`

**Files:**
- Modify: `Main/backend/mcp_client/agent.py:60-224`
- Create: `Main/backend/tests/test_agent_tool_filtering.py`

**Step 1: Write the failing test**

```python
# tests/test_agent_tool_filtering.py
"""
Tests for the tool-filtering capability in create_fin_agent.
Uses mocking to avoid needing actual MCP servers or API keys.
"""
import pytest
import asyncio
from unittest.mock import patch, MagicMock, AsyncMock


class TestToolFiltering:
    """Test that create_fin_agent respects allowed_tools parameter."""

    @pytest.fixture
    def mock_env(self):
        """Provide minimal env for agent creation."""
        env = {
            "OPENAI_API_KEY": "test-key",
            "GOOGLE_API_KEY": "",
        }
        with patch.dict("os.environ", env, clear=False):
            yield

    @pytest.fixture
    def mock_mcp(self):
        """Mock the global MCP manager to return no MCP tools."""
        with patch("mcp_client.agent.get_global_mcp_manager", return_value=None):
            yield

    def test_all_tools_when_none(self, mock_env, mock_mcp):
        """allowed_tools=None gives all direct tools (default behavior)."""
        from mcp_client.agent import create_fin_agent

        async def run():
            async with create_fin_agent(
                model="gpt-4o-mini",
                allowed_tools=None,
            ) as agent:
                # Without MCP, we get 6 direct tools: 2 url + 3 playwright + 1 calculator
                assert len(agent.tools) == 6
                names = {t.name for t in agent.tools}
                assert "scrape_url" in names
                assert "navigate_to_url" in names
                assert "calculate" in names

        asyncio.run(run())

    def test_no_tools_when_empty(self, mock_env, mock_mcp):
        """allowed_tools=[] gives zero tools."""
        from mcp_client.agent import create_fin_agent

        async def run():
            async with create_fin_agent(
                model="gpt-4o-mini",
                allowed_tools=[],
            ) as agent:
                assert agent.tools == []

        asyncio.run(run())

    def test_filtered_tools(self, mock_env, mock_mcp):
        """allowed_tools=['calculate', 'scrape_url'] gives exactly those tools."""
        from mcp_client.agent import create_fin_agent

        async def run():
            async with create_fin_agent(
                model="gpt-4o-mini",
                allowed_tools=["calculate", "scrape_url"],
            ) as agent:
                assert len(agent.tools) == 2
                names = {t.name for t in agent.tools}
                assert names == {"calculate", "scrape_url"}

        asyncio.run(run())

    def test_instructions_override_bypasses_prompt_builder(self, mock_env, mock_mcp):
        """instructions_override skips PromptBuilder and uses the override directly."""
        from mcp_client.agent import create_fin_agent

        override = "You are a test agent. Only summarize."

        async def run():
            async with create_fin_agent(
                model="gpt-4o-mini",
                instructions_override=override,
                allowed_tools=[],
            ) as agent:
                assert agent.instructions == override

        asyncio.run(run())

    def test_no_override_uses_prompt_builder(self, mock_env, mock_mcp):
        """Without instructions_override, PromptBuilder is used normally."""
        from mcp_client.agent import create_fin_agent

        async def run():
            async with create_fin_agent(
                model="gpt-4o-mini",
            ) as agent:
                # Should contain core.md content
                assert "FinGPT" in agent.instructions

        asyncio.run(run())
```

**Step 2: Run test to verify it fails**

Run: `cd Main/backend && python3 -m pytest tests/test_agent_tool_filtering.py -v`
Expected: FAIL with `TypeError: create_fin_agent() got an unexpected keyword argument 'allowed_tools'`

**Step 3: Modify `create_fin_agent` in `agent.py`**

Three changes to `Main/backend/mcp_client/agent.py`:

**Change 1 — Add parameters to function signature (line 61-66):**

Replace:
```python
@asynccontextmanager
async def create_fin_agent(model: str = "gpt-4o-mini",
                          system_prompt: Optional[str] = None,
                          current_url: Optional[str] = None,
                          user_input: Optional[str] = None,
                          user_timezone: Optional[str] = None,
                          user_time: Optional[str] = None):
```

With:
```python
@asynccontextmanager
async def create_fin_agent(model: str = "gpt-4o-mini",
                          system_prompt: Optional[str] = None,
                          current_url: Optional[str] = None,
                          user_input: Optional[str] = None,
                          user_timezone: Optional[str] = None,
                          user_time: Optional[str] = None,
                          allowed_tools: Optional[List[str]] = None,
                          instructions_override: Optional[str] = None):
```

**Change 2 — Prompt building (line 81-86):**

Replace:
```python
    instructions = _prompt_builder.build(
        current_url=current_url,
        system_prompt=system_prompt,
        user_timezone=user_timezone,
        user_time=user_time,
    )
```

With:
```python
    if instructions_override is not None:
        instructions = instructions_override
    else:
        instructions = _prompt_builder.build(
            current_url=current_url,
            system_prompt=system_prompt,
            user_timezone=user_timezone,
            user_time=user_time,
        )
```

**Change 3 — Tool filtering (after line 191, before the `try:` that creates the Agent):**

Replace the block from `tools: List = []` (line 120) through the MCP tool collection (ends ~line 197) with:

```python
    tools: List = []

    # Skip tool collection entirely when plan specifies zero tools
    if allowed_tools is not None and len(allowed_tools) == 0:
        logging.info("[AGENT] Skill specifies zero tools — skipping tool collection")
    else:
        url_tools = get_url_tools()
        tools.extend(url_tools)

        playwright_tools = get_playwright_tools()
        tools.extend(playwright_tools)

        from datascraper.calculator_tool import get_calculator_tools
        calculator_tools = get_calculator_tools()
        tools.extend(calculator_tools)

        from .mcp_manager import MCPClientManager
        from .tool_wrapper import convert_mcp_tool_to_python_callable
        import asyncio

        global _mcp_init_lock

        _mcp_manager = get_global_mcp_manager()

        if _mcp_manager is None:
            logging.warning("Global MCP manager not found, creating fallback instance")

            if _mcp_init_lock is None:
                _mcp_init_lock = asyncio.Lock()

            async with _mcp_init_lock:
                _mcp_manager = get_global_mcp_manager()
                if _mcp_manager is None:
                    manager = MCPClientManager()
                    try:
                        await manager.connect_to_servers()
                        _mcp_manager = manager
                        logging.info("Fallback MCP manager connected")
                    except Exception as e:
                        logging.error(f"Failed to initialize MCP tools: {e}")
                        _mcp_manager = None

        if _mcp_manager:
            try:
                if _mcp_manager._loop:
                    import concurrent.futures
                    future = asyncio.run_coroutine_threadsafe(
                        _mcp_manager.get_all_tools(),
                        _mcp_manager._loop
                    )
                    try:
                        mcp_tools = future.result(timeout=10)
                    except concurrent.futures.TimeoutError:
                        logging.warning("Timeout fetching MCP tools")
                        mcp_tools = []
                else:
                    mcp_tools = await _mcp_manager.get_all_tools()

                if mcp_tools:
                    logging.info(f"Agent configured with {len(mcp_tools)} MCP tools")

                    for tool in mcp_tools:

                        async def execute_mcp_tool(name, args, mgr=_mcp_manager):
                            if mgr._loop:
                                future = asyncio.run_coroutine_threadsafe(
                                    mgr.execute_tool(name, args),
                                    mgr._loop
                                )
                                return future.result(timeout=60)
                            else:
                                return await mgr.execute_tool(name, args)

                        agent_tool = convert_mcp_tool_to_python_callable(tool, execute_mcp_tool)
                        tools.append(agent_tool)

                else:
                    logging.warning("No MCP tools found")

            except Exception as e:
                logging.error(f"Error fetching/adding MCP tools: {e}", exc_info=True)

        # Apply tool filter if specified
        if allowed_tools is not None:
            pre_filter_count = len(tools)
            tools = [t for t in tools if t.name in allowed_tools]
            logging.info(
                f"[AGENT] Tool filter applied: {pre_filter_count} -> {len(tools)} "
                f"(allowed: {allowed_tools})"
            )
```

**Step 4: Run test to verify it passes**

Run: `cd Main/backend && python3 -m pytest tests/test_agent_tool_filtering.py -v`
Expected: PASS (5 tests)

Also run existing tests to verify no regressions:

Run: `cd Main/backend && python3 -m pytest tests/ -v`
Expected: All existing tests still PASS

**Step 5: Commit**

```bash
git add Main/backend/mcp_client/agent.py Main/backend/tests/test_agent_tool_filtering.py
git commit -m "feat(agent): add allowed_tools + instructions_override to create_fin_agent"
```

---

## Task 7: Integrate Planner into datascraper.py

**Files:**
- Modify: `Main/backend/datascraper/datascraper.py:1154-1200`

This is the critical integration task. We insert the Planner between message extraction and agent creation.

**Step 1: Write the failing test**

```python
# tests/test_planner_integration.py
"""
Integration test: verify the planner correctly constrains the agent.
Tests the full flow from message_list → planner → create_fin_agent.
"""
import pytest
import asyncio
from unittest.mock import patch, MagicMock


def _make_message_list(user_msg: str, prescraped_content: str | None = None) -> list:
    """Build a message_list as views.py would."""
    messages = []
    if prescraped_content:
        system = (
            "[SYSTEM MESSAGE]: "
            "[CURRENT PAGE CONTENT - Already scraped, do NOT re-scrape]:\n"
            f"- From https://example.com:\n{prescraped_content}"
        )
        messages.append({"content": system})
    messages.append({"content": f"[USER MESSAGE]: {user_msg}"})
    return messages


class TestPlannerIntegration:
    """Test that the planner integration in datascraper works end-to-end."""

    @pytest.fixture
    def mock_deps(self):
        """Mock external dependencies."""
        with patch("mcp_client.agent.get_global_mcp_manager", return_value=None), \
             patch.dict("os.environ", {"OPENAI_API_KEY": "test", "GOOGLE_API_KEY": ""}):
            yield

    def test_summarize_uses_zero_tools(self, mock_deps):
        """When prescraped content exists and user asks to summarize, agent gets zero tools."""
        from planner.planner import Planner

        planner = Planner()
        plan = planner.plan(
            user_query="summarize this page",
            system_prompt=(
                "[CURRENT PAGE CONTENT - Already scraped, do NOT re-scrape]:\n"
                "- From https://example.com:\nEarnings report for Q4..."
            ),
            domain="example.com",
        )

        assert plan.skill_name == "summarize_page"
        assert plan.tools_allowed == []
        assert plan.max_turns == 1
        assert plan.instructions is not None
        assert "Earnings report for Q4" in plan.instructions

    def test_fallback_uses_all_tools(self, mock_deps):
        """Complex queries with no skill match get full tool access."""
        from planner.planner import Planner

        planner = Planner()
        plan = planner.plan(
            user_query="research biotech trends and navigate to FDA.gov",
            system_prompt=None,
            domain=None,
        )

        assert plan.skill_name == "web_research"
        assert plan.tools_allowed is None
        assert plan.max_turns == 10

    def test_stock_query_gets_filtered_tools(self, mock_deps):
        """Stock price queries get only fundamental tools."""
        from planner.planner import Planner

        planner = Planner()
        plan = planner.plan(
            user_query="what is the current price of TSLA?",
            system_prompt=None,
            domain="finance.yahoo.com",
        )

        assert plan.skill_name == "stock_fundamentals"
        assert set(plan.tools_allowed) == {"get_stock_info", "get_stock_history", "calculate"}
        assert plan.max_turns == 3
```

**Step 2: Run test to verify it passes** (these test the planner in isolation — they should pass already)

Run: `cd Main/backend && python3 -m pytest tests/test_planner_integration.py -v`
Expected: PASS

**Step 3: Modify `datascraper.py`**

In `datascraper.py`, modify the `_stream()` inner function (starting at line 1154).

Find the block at lines ~1157-1164 where `extracted_system_prompt` is built:

```python
        context = ""
        extracted_system_prompt = None

        for msg in message_list:
            content = msg.get("content", "")
            if content.startswith(SYSTEM_PREFIX):
                actual_content = content.replace(SYSTEM_PREFIX, "", 1)
                extracted_system_prompt = actual_content
                continue
```

Right after line 1181 (`full_prompt = context.rstrip()`), insert the planner:

```python
        full_prompt = context.rstrip()

        # --- Planner: select skill and constrain agent ---
        from planner.planner import Planner
        _planner = Planner()
        _domain = None
        if current_url:
            from urllib.parse import urlparse
            _domain = urlparse(current_url).netloc.lower() or None

        execution_plan = _planner.plan(
            user_query=user_input,
            system_prompt=extracted_system_prompt,
            domain=_domain,
        )
        logging.info(
            f"[AGENT STREAM] Plan: skill={execution_plan.skill_name} "
            f"tools={'ALL' if execution_plan.tools_allowed is None else len(execution_plan.tools_allowed)} "
            f"max_turns={execution_plan.max_turns}"
        )
        # --- End planner ---
```

Then modify the `create_fin_agent` call at line ~1193 to pass plan constraints:

Replace:
```python
                async with create_fin_agent(
                    model=model,
                    system_prompt=extracted_system_prompt,
                    user_input=user_input,
                    current_url=current_url,
                    user_timezone=user_timezone,
                    user_time=user_time
                ) as agent:
```

With:
```python
                async with create_fin_agent(
                    model=model,
                    system_prompt=extracted_system_prompt,
                    user_input=user_input,
                    current_url=current_url,
                    user_timezone=user_timezone,
                    user_time=user_time,
                    allowed_tools=execution_plan.tools_allowed,
                    instructions_override=execution_plan.instructions,
                ) as agent:
```

And modify the `MAX_AGENT_TURNS` usage at line ~1184 and the Runner calls:

Replace:
```python
        MAX_AGENT_TURNS = int(os.getenv("AGENT_MAX_TURNS", "10"))
```

With:
```python
        MAX_AGENT_TURNS = execution_plan.max_turns
```

**Step 4: Run all tests**

Run: `cd Main/backend && python3 -m pytest tests/ -v`
Expected: All tests PASS

Run: `cd Main/backend && uv run python manage.py check`
Expected: System check identified no issues.

**Step 5: Commit**

```bash
git add Main/backend/datascraper/datascraper.py Main/backend/tests/test_planner_integration.py
git commit -m "feat(planner): integrate planner into agent stream — tool-gating by code"
```

---

## Task 8: Verification + edge case tests

**Files:**
- Modify: `Main/backend/tests/test_planner.py`

**Step 1: Add edge case tests**

Append to `tests/test_planner.py`:

```python
class TestPlannerEdgeCases:
    def setup_method(self):
        self.planner = Planner()

    def test_empty_query(self):
        plan = self.planner.plan(user_query="", system_prompt=None, domain=None)
        assert plan.skill_name == "web_research"  # Fallback

    def test_prescraped_but_data_query(self):
        """Pre-scraped content exists but user asks for stock data → use data skill, not summarize."""
        plan = self.planner.plan(
            user_query="what is the PE ratio?",
            system_prompt="[CURRENT PAGE CONTENT - Already scraped, do NOT re-scrape]:\n- From url:\nSome article",
            domain="finance.yahoo.com",
        )
        assert plan.skill_name == "stock_fundamentals"
        assert plan.instructions is None  # No override — use PromptBuilder

    def test_multiple_intents_highest_wins(self):
        """When query matches multiple skills, the highest-confidence one wins."""
        plan = self.planner.plan(
            user_query="what is AAPL RSI and earnings date?",
            system_prompt=None,
            domain=None,
        )
        # Both technical_analysis and financial_statements match.
        # Either is acceptable, but it should not be web_research.
        assert plan.skill_name in {"technical_analysis", "financial_statements"}

    def test_none_system_prompt(self):
        plan = self.planner.plan(user_query="hello", system_prompt=None, domain=None)
        assert isinstance(plan, ExecutionPlan)

    def test_summarize_with_web_search_only(self):
        """Web search results (not page content) should NOT trigger SummarizePageSkill."""
        plan = self.planner.plan(
            user_query="summarize the search results",
            system_prompt="[WEB SEARCH RESULTS]:\n- From google.com: some results",
            domain=None,
        )
        # No [CURRENT PAGE CONTENT] marker → has_prescraped=False
        assert plan.skill_name == "web_research"
```

**Step 2: Run tests**

Run: `cd Main/backend && python3 -m pytest tests/test_planner.py -v`
Expected: PASS (14 tests)

**Step 3: Run full test suite**

Run: `cd Main/backend && python3 -m pytest tests/ -v`
Expected: All tests PASS

**Step 4: Commit**

```bash
git add Main/backend/tests/test_planner.py
git commit -m "test(planner): add edge case tests for multi-intent and prescraped scenarios"
```

---

## Task 9: Final verification

**Step 1: Run all tests**

Run: `cd Main/backend && python3 -m pytest tests/ -v`
Expected: All tests PASS

**Step 2: Django check**

Run: `cd Main/backend && uv run python manage.py check`
Expected: System check identified no issues.

**Step 3: Verify import chain**

Run: `cd Main/backend && python3 -c "from planner.planner import Planner; p = Planner(); print('Planner OK')" && python3 -c "from planner.skills.registry import SkillRegistry; r = SkillRegistry(); print(f'Registry OK: {len(r.skills)} skills')"`
Expected: `Planner OK` and `Registry OK: 6 skills`

**Step 4: Log review**

Manually review that the planner logs are informative:
```
[SkillRegistry] Selected 'summarize_page' (score=0.90) for query: summarize this page
[Planner] plan=summarize_page tools=0 turns=1 has_instructions=yes
[AGENT STREAM] Plan: skill=summarize_page tools=0 max_turns=1
[AGENT] Skill specifies zero tools — skipping tool collection
```

---

## Summary of Changes

| File | Change |
|------|--------|
| `planner/__init__.py` | New — package init |
| `planner/plan.py` | New — ExecutionPlan dataclass |
| `planner/planner.py` | New — Planner with code heuristics |
| `planner/skills/__init__.py` | New — package init |
| `planner/skills/base.py` | New — BaseSkill ABC |
| `planner/skills/registry.py` | New — SkillRegistry |
| `planner/skills/summarize_page.py` | New — zero-tool summarization |
| `planner/skills/stock_fundamentals.py` | New — filtered to 3 tools |
| `planner/skills/options_analysis.py` | New — filtered to 3 tools |
| `planner/skills/financial_statements.py` | New — filtered to 3 tools |
| `planner/skills/technical_analysis.py` | New — filtered to 8 tools |
| `planner/skills/web_research.py` | New — fallback, all tools |
| `mcp_client/agent.py` | Modified — `allowed_tools` + `instructions_override` params |
| `datascraper/datascraper.py` | Modified — planner inserted before agent creation |
| `tests/test_skills.py` | New — skill config + registry tests |
| `tests/test_planner.py` | New — planner heuristic tests |
| `tests/test_agent_tool_filtering.py` | New — agent tool filtering tests |
| `tests/test_planner_integration.py` | New — end-to-end integration tests |

## Risk Assessment

| Risk | Mitigation |
|------|-----------|
| Planner selects wrong skill | WebResearchSkill fallback ensures no regression; heuristics are conservative |
| SummarizePageSkill misses edge cases | `build_instructions` returns None when no content → falls back to normal flow |
| Tool filtering breaks MCP tools | Filter uses `.name` attribute, verified on FunctionTool; MCP tools also have `.name` |
| Existing tests break | All changes are additive; `allowed_tools=None` preserves current behavior |
| Performance impact | Planner is pure Python regex matching — sub-millisecond |
