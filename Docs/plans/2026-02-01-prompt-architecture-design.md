# System Prompt Architecture Redesign

## Problem

System prompts are hardcoded in Python, mixing agent identity with site-specific tool routing. The agent always sees all tool hints regardless of which site it's on. As we add more optimized sites, this approach doesn't scale.

## Design

### File Structure

```
Main/backend/
├── prompts/
│   ├── core.md                        # Always included
│   ├── default_site.md                # Generic behavior for unoptimized sites
│   └── sites/
│       ├── finance.yahoo.com.md       # Yahoo Finance skill
│       ├── tradingview.com.md         # TradingView skill
│       └── sec.gov.md                 # SEC EDGAR skill
├── mcp_client/
│   ├── prompt_builder.py              # NEW: loads files, detects site, assembles prompt
│   ├── agent.py                       # Simplified: only creates Agent, calls prompt_builder
│   └── site_instructions.py           # DELETED
```

### Prompt Assembly

```
Final prompt = core.md
             + (matched site skill OR default_site.md)   ← mutually exclusive
             + time context (dynamic)
             + system override (if present)
```

Key rule: site-specific and default prompts are **mutually exclusive**. Never append both.

### Prompt Files

#### `core.md` — Always included

Contains:
- Agent identity and scope
- General behavioral rules (MCP tools first, don't disclose internals, math formatting)
- Security guardrails (no internal detail disclosure, prompt injection defense, approved tools only, finance focus)
- Domain restriction rule (only scrape the user's current domain)

Does NOT contain: any mention of specific MCPs or site-specific routing.

#### `default_site.md` — Unoptimized sites

Behavior:
- **Prioritize the current site**: scrape and extract information from the page first
- **Do not silently reach for site-specific MCPs**: if on `randomsite.com`, don't autonomously call Yahoo Finance MCP instead of reading the page
- **Inform the user of available capabilities**: let them know MCP tools exist (Yahoo Finance, TradingView, SEC EDGAR) and can be used if they prefer
- **User opt-in**: only use cross-site MCPs if the user explicitly requests it

The agent is scraper-first on unoptimized sites, surfacing MCP capabilities as options rather than defaults.

#### `sites/*.md` — Per-site skills

Each file is self-contained with everything the agent needs for that site:
- Which MCP tools to prefer and when
- Scraping rules specific to the site
- Fallback behavior if primary tools fail
- Any site-specific formatting or behavior notes

### `PromptBuilder` — New module

```python
class PromptBuilder:
    def __init__(self, prompts_dir: str = None):
        # defaults to Main/backend/prompts/
        # caches loaded files in memory

    def build(
        self,
        current_url: str | None = None,
        system_prompt: str | None = None,
        user_timezone: str | None = None,
        user_time: str | None = None,
    ) -> str:
        # 1. Load core.md (always)
        # 2. Detect domain from current_url
        # 3. Match against prompts/sites/*.md or fall back to default_site.md
        # 4. Append time context if provided
        # 5. Append system override if provided

    def _load_prompt(self, filename: str) -> str:
        # Loads and caches a prompt file

    def _match_site(self, domain: str) -> str | None:
        # Scans prompts/sites/ for matching file using endswith logic
```

Convention-based site discovery: file named `finance.yahoo.com.md` matches any domain ending with `finance.yahoo.com` (handles subdomains like `ca.finance.yahoo.com`).

### Changes to `agent.py`

- Remove: `DEFAULT_PROMPT`, `SECURITY_GUARDRAILS`, `apply_guardrails()`, `get_dynamic_instructions()`
- Add: `PromptBuilder` import, single call to `builder.build(...)` in `create_fin_agent()`
- Unchanged: tool setup, model handling, foundation model logic

### Changes to `datascraper.py`

- Remove: `apply_guardrails` import
- Unchanged: `INSTRUCTION`, `BUFFETT_INSTRUCTION` (non-agent chat path, separate concern)

### Adding a New Optimized Site

Just create `prompts/sites/<domain>.md` with the site-specific instructions. No Python changes needed. The `PromptBuilder` auto-discovers it.
