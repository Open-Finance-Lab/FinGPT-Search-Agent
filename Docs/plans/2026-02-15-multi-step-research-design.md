# Multi-Step Iterative Research — Design Document

**Date**: 2026-02-15
**Status**: Approved
**Parent Plan**: `2026-02-15-research-mode-enhancement.md` (Phase 1: items 1A + 1B)

---

## Problem

Research mode currently makes a **single** OpenAI Responses API call with `web_search`. For complex, multi-part financial queries (e.g., "Compare AAPL and MSFT revenue growth over the last 3 quarters"), this produces shallow answers because the model tries to answer everything in one search pass.

Commercial products (ChatGPT Deep Research, Gemini Deep Research, Perplexity) use iterative plan-search-evaluate-refine loops that produce significantly better results.

## Approach: Hybrid Client-Side Orchestration

We decompose queries into sub-questions, route each to the best data source (MCP for numerical, web search for qualitative), detect gaps, execute follow-ups, and synthesize a final answer.

**Key constraints:**
- GPT-5.2 as default research model, easily swappable for demos (o3, o4, etc.)
- GPT-5-mini for cheap/fast query decomposition and gap detection
- Max 3 iteration rounds to cap cost
- Stream final answer only (with "Researching..." status), but design for future phase-by-phase streaming
- Simple queries skip the orchestration entirely (no added overhead)

---

## Architecture

```
User Query
    │
    ▼
┌─────────────────────────┐
│  Query Analyzer           │  ← gpt-5-mini (no tools)
│  - Classify complexity    │
│  - Decompose if needed    │
│  - Classify sub-questions │
└───────────┬───────────────┘
            │
    ┌───────▼───────┐
    │ needs_decomp? │
    └───┬───────┬───┘
     no │       │ yes
        ▼       ▼
  ┌──────────┐  ┌──────────────────────┐
  │ Existing │  │  Research Executor     │
  │ single   │  │  Per sub-question:     │
  │ search   │  │  - numerical → MCP     │
  │ path     │  │  - qualitative → web   │
  └──────────┘  │  - analytical → defer  │
                └───────────┬──────────┘
                            │
                ┌───────────▼──────────┐
                │  Gap Detector         │  ← gpt-5-mini
                │  "All answered?"      │
                │  If no → follow-ups   │
                │  Max 3 rounds         │
                └───────────┬──────────┘
                            │
                ┌───────────▼──────────┐
                │  Synthesizer          │  ← research model
                │  Combine findings     │
                │  Inline citations     │
                │  Streamed to user     │
                └───────────────────────┘
```

---

## Components

### 1. Query Analyzer

**Model**: gpt-5-mini (no tools, structured JSON output)
**Input**: User query + time context
**Output**:
```json
{
  "needs_decomposition": true,
  "sub_questions": [
    {"question": "AAPL quarterly revenue Q2-Q4 2025", "type": "numerical"},
    {"question": "MSFT quarterly revenue Q2-Q4 2025", "type": "numerical"},
    {"question": "Revenue growth comparison analysis", "type": "analytical"}
  ]
}
```

**Sub-question types:**
- `numerical` → Route to MCP (Yahoo Finance) first, fall back to web search
- `qualitative` → Route to web search (news, sentiment, analysis)
- `analytical` → No search needed; synthesize from other sub-question results

**Bypass rule**: If `needs_decomposition: false`, skip straight to existing single-search path. This means simple queries like "What's AAPL price?" have zero added latency.

### 2. Research Executor

Routes each sub-question to the appropriate data source:

- **Numerical**: Reuses existing `_try_mcp_for_numerical_query()`. If MCP fails, falls back to a focused web search via `create_responses_api_search_async()`.
- **Qualitative**: Calls `create_responses_api_search_async()` with the sub-question as the query.
- **Analytical**: Skipped during search; handled by synthesizer.

Independent sub-questions run **concurrently** (e.g., AAPL and MSFT data fetch in parallel).

### 3. Gap Detector

**Model**: gpt-5-mini (no tools, structured JSON output)
**Input**: Original query + research plan + results collected so far
**Output**:
```json
{
  "complete": false,
  "gaps": ["Missing Q3 2025 revenue for MSFT"],
  "follow_up_queries": [
    {"question": "MSFT Q3 2025 quarterly revenue earnings report", "type": "qualitative"}
  ]
}
```

**Hard cap**: 3 total rounds (initial + 2 follow-ups). Configurable via `RESEARCH_CONFIG`.

### 4. Synthesizer

**Model**: Research model (gpt-5.2 default, configurable)
**Input**: Original query + all collected findings + all sources
**Output**: Comprehensive response with inline citations (streamed to user)

The synthesizer is the only component whose output reaches the user. All prior steps are internal.

### 5. Research Config

```python
RESEARCH_CONFIG = {
    "planner_model": "gpt-5-mini",
    "research_model": "gpt-5.2-chat-latest",
    "max_iterations": 3,
    "max_sub_questions": 5,
    "parallel_searches": True,
    "complexity_threshold": True,  # Enable query analysis bypass for simple queries
}
```

Swap `research_model` to `"o3"` or `"o4-mini"` for demos with reasoning models.

---

## Files to Create/Modify

| File | Action | Description |
|------|--------|-------------|
| `datascraper/research_engine.py` | **NEW** | Core orchestration: QueryAnalyzer, ResearchExecutor, GapDetector, Synthesizer |
| `datascraper/datascraper.py` | MODIFY | Hook research engine into `create_advanced_response()` for complex queries |
| `datascraper/openai_search.py` | MODIFY | Expose lightweight single-sub-question search function |
| `datascraper/models_config.py` | MODIFY | Add `RESEARCH_CONFIG` with configurable models |
| `datascraper/quality_logger.py` | MODIFY | Add research-specific quality signals (iteration count, sub-question routing) |

---

## Integration Points

### Entry: `create_advanced_response()` in datascraper.py

Current flow:
1. MCP-first check → if numerical, try MCP
2. If MCP fails or not numerical → single web search

New flow:
1. MCP-first check → if numerical AND simple, try MCP (unchanged)
2. **Query analysis** → if complex, route to research engine
3. If simple → single web search (unchanged, zero overhead)

### Streaming

**Phase 1 (this implementation):**
- During research phases: SSE events with `{"type": "status", "content": "Researching..."}`
- Once synthesizer starts: normal text streaming via existing `_stream_response_chunks()`

**Phase 2 (future):**
- Stream intermediate findings as they arrive
- Progress indicators per sub-question
- Requires frontend changes

### Quality Logging

New quality signals:
- `iterative_research`: Mode flag
- `sub_questions_count`: How many sub-questions generated
- `iterations_used`: How many rounds executed
- `mcp_hits` / `web_hits`: Routing breakdown
- `early_completion`: Completed before max iterations

---

## Cost Analysis

| Component | Model | Est. Cost per Call |
|-----------|-------|--------------------|
| Query Analyzer | gpt-5-mini | ~$0.001 |
| MCP sub-question (Yahoo Finance) | n/a | Free (local tool) |
| Web search sub-question | gpt-5.2 | ~$0.03-0.10 |
| Gap Detector | gpt-5-mini | ~$0.001 |
| Synthesizer | gpt-5.2 | ~$0.02-0.05 |

**Simple query** (bypass): Same cost as today (~$0.03-0.10)
**Complex query** (3 sub-questions, 1 iteration): ~$0.10-0.35
**Complex query** (3 sub-questions, 3 iterations): ~$0.20-0.60

---

## Out of Scope

- Multi-source cross-validation (Phase 2: 1C, 1D)
- Evidence chain formatting (Phase 4: 1E)
- Phase-by-phase streaming (future enhancement)
- Source quality scoring tiers
- Code interpreter for ad-hoc calculations

---

## References

- Parent plan: `Docs/plans/2026-02-15-research-mode-enhancement.md`
- OpenAI Responses API: web_search tool with `search_context_size` parameter
- OpenAI Deep Research: `o3-deep-research` model with autonomous multi-step browsing
- Gemini Deep Research: Interactions API with plan → search → iterate → output
- Perplexity Sonar: OpenAI-compatible API with built-in grounded search
