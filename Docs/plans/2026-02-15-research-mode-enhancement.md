# Research Mode Enhancement Plan

**Date**: 2026-02-15
**Status**: Planning
**Priority**: High

## Context

Benchmark testing (Feb 3rd) revealed Research mode scored 16.7% vs Thinking mode's 85.7% on financial data retrieval. Initial fixes (MCP-first routing, source hardening, temporal grounding, etc.) addressed the worst failures. This plan documents the next wave of improvements informed by competitive analysis of ChatGPT Deep Research, Gemini Deep Research, and Perplexity Finance.

## Scope

This plan covers two focus areas:
1. **Multi-step iterative research** (priority — implement first)
2. **Symbolic computation** (implement second)

Documented but deferred (future work):
3. **Broader structured data sources**
4. **Confidence-based filtering**

---

## 1. Multi-Step Iterative Research

Currently, Research mode makes a single OpenAI Responses API call with web_search. Commercial products (ChatGPT Deep Research, Gemini Deep Research) use a plan-search-read-refine loop that iterates until the query is fully answered.

### 1A. Query Analysis & Research Planning
- Before executing any search, analyze the query to determine: what data points are needed, what time periods are relevant, and what sources would be authoritative
- For multi-part questions (e.g., "compare AAPL and MSFT revenue growth over the last 3 quarters"), decompose into sub-queries
- Generate an explicit research plan (list of sub-questions to answer)

### 1B. Iterative Search with Gap Detection
- After the first search pass, evaluate whether the response fully answers the query
- Identify missing data points, unverified claims, or unanswered sub-questions
- Execute follow-up searches targeting the gaps
- Cap iterations to prevent runaway costs (e.g., max 3 rounds)

### 1C. Multi-Source Cross-Validation for Numerical Claims
- For numerical financial data, attempt to verify key numbers from at least two sources
- When MCP (Yahoo Finance) and web search both return data for the same metric, compare values
- Flag discrepancies above a threshold (e.g., >1% difference) and prefer the structured source

### 1D. Source Quality Scoring
- Assign reliability tiers to sources encountered during research (Tier 1: Yahoo Finance, Bloomberg, SEC EDGAR; Tier 2: MarketWatch, CNBC, Reuters; Tier 3: everything else)
- When conflicting data exists, prefer higher-tier sources
- Include source tier in quality logging

### 1E. Research Summary with Evidence Chain
- Structure the final response to show the reasoning path: what was searched, what was found, how conflicts were resolved
- Provide inline citations linking each claim to its source
- For numerical data, indicate whether the value came from structured API or web search

---

## 2. Symbolic Computation

Currently, the LLM performs all arithmetic (percentage changes, ratios, ranges, etc.). Research shows symbolic-neural fusion — routing math to a programmatic calculator — eliminates a major class of numerical errors.

### 2A. Computation Router
- Detect when a query requires arithmetic (percentage change, ratio computation, aggregation, comparison, etc.)
- Route the computation to a programmatic function instead of letting the LLM calculate
- Return the computed result to the LLM for natural-language formatting only

### 2B. Financial Calculation Library
- Implement common financial computations as deterministic functions:
  - Percentage change: `(new - old) / old * 100`
  - Turnover ratio: `volume / shares_outstanding`
  - Price range: `high - low`
  - Market cap: `price * shares_outstanding`
  - Moving averages, YTD return, etc.
- Accept raw data from MCP tools as input, return exact results

### 2C. Code Interpreter Integration (Stretch)
- For complex or ad-hoc calculations that don't fit predefined functions, allow the agent to write and execute Python code
- Sandbox execution environment for safety
- Return computed results with the code shown for transparency

### 2D. Result Formatting Guard
- After symbolic computation, the LLM formats the result into natural language
- Validate that the formatted response preserves the exact computed values (no rounding, no re-derivation)
- If the LLM alters a computed number, replace it with the original

---

---

## 3. Broader Structured Data Sources (Deferred)

We currently rely on Yahoo Finance (yfinance) as our only structured data source. Perplexity Finance integrates 6+ API partners (FMP, FactSet, FinChat.io, Quartr, Unusual Whales, Crunchbase). Expanding our structured data coverage would improve accuracy for queries yfinance can't answer well (e.g., detailed quarterly financials, earnings transcripts, options data, institutional holdings).

### Candidates
- **Financial Modeling Prep (FMP)** — income statements, balance sheets, cash flow, key metrics; free tier available
- **SEC EDGAR XBRL API** — we already have an EDGAR MCP tool; expand to pull structured XBRL financials directly
- **Alpha Vantage** — real-time and historical data with free tier
- **Polygon.io** — market data, options, crypto
- **Earnings call transcripts** — Quartr API or open-source alternatives

---

## 4. Confidence-Based Filtering (Deferred)

Currently we serve every response regardless of how confident the model is about numerical claims. The ECLIPSE paper (arXiv:2512.03107) shows that measuring semantic entropy and filtering low-confidence responses can reduce hallucination rates from 43% to 3.3%.

### Possible Approaches
- **Semantic entropy** — sample multiple completions, cluster by meaning, high entropy = low confidence
- **Self-consistency check** — ask the model the same numerical question twice; if answers diverge, flag as uncertain
- **Source-grounding score** — if a numerical claim can be traced to a structured API value, mark as high confidence; if only from web text, mark as lower confidence
- **User-facing confidence indicator** — surface a confidence signal in the UI so users know when to double-check

---

## Implementation Order

| Phase | Item | Description |
|-------|------|-------------|
| **Phase 1** | 1A, 1B | Query decomposition + iterative search loop |
| **Phase 2** | 1C, 1D | Cross-validation + source scoring |
| **Phase 3** | 2A, 2B | Computation router + financial calc library |
| **Phase 4** | 1E, 2D | Evidence chains + formatting guards |
| **Phase 5** | 2C | Code interpreter (stretch goal) |
| **Phase 6** | 3 | Additional structured data sources |
| **Phase 7** | 4 | Confidence-based filtering |

## References

- [Daloopa Benchmark](https://daloopa.com/blog/research/benchmarking-ai-agents-on-financial-retrieval) — 71-point accuracy gain from structured data
- [HierFinRAG](https://www.mdpi.com/2227-9709/13/2/30) — Symbolic-Neural Fusion achieving 82.5% exact match
- [FinSight](https://arxiv.org/abs/2510.16844) — Multi-agent financial research outperforming ChatGPT/Gemini Deep Research
- [OpenAI Deep Research API](https://developers.openai.com/api/docs/guides/deep-research/) — Clarification → enrichment → adaptive execution pipeline
- [Gemini Deep Research API](https://ai.google.dev/gemini-api/docs/deep-research) — Plan → parallel execution → iterative refinement
- [ToolCaching](https://arxiv.org/abs/2601.15335) — Adaptive TTL for financial data freshness
- [ECLIPSE](https://arxiv.org/abs/2512.03107) — Semantic entropy for hallucination detection (92% reduction)
