# Options Summary Tool + Agent Stability Fixes

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Fix 5 bugs exposed by a failed AVGO options volume query: Timestamp serialization crash, wasteful MaxTurnsExceeded retries, missing aggregate options tool, Playwright version mismatch, and invisible max_turns config.

**Architecture:** Fix serialization bugs in 3 MCP handlers by stringifying DataFrame index/columns before `to_dict()`. Add a new `get_options_summary` MCP tool that aggregates volume/OI across all expirations in a single call. Make the agent loop smarter by catching `MaxTurnsExceeded` separately and exposing `max_turns` via env var. Bump Playwright Docker image version.

**Tech Stack:** Python 3.12, yfinance, pandas, MCP SDK, OpenAI Agents SDK, Docker

---

### Task 1: Fix Timestamp key serialization in `stock_analysis.py`

**Files:**
- Modify: `main/backend/mcp_server/handlers/stock_analysis.py:40-49`
- Test: `Main/backend/tests/test_stock_analysis_serialization.py`

**Step 1: Write the failing test**

Create `Main/backend/tests/test_stock_analysis_serialization.py`:

```python
"""Tests for stock_analysis Timestamp key serialization fix."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import json
import pandas as pd


def test_safe_dict_with_timestamp_index():
    """Reproduces TypeError: keys must be str, not Timestamp."""
    from mcp_server.handlers.stock_analysis import GetStockAnalysisHandler

    # Simulate upgrades_downgrades DataFrame with DatetimeIndex
    df = pd.DataFrame(
        {"Firm": ["Goldman", "Morgan"], "ToGrade": ["Buy", "Hold"]},
        index=pd.to_datetime(["2026-01-15", "2026-02-10"]),
    )
    handler = GetStockAnalysisHandler()
    result = handler._safe_dict(df)

    # Must be JSON-serializable (no Timestamp keys)
    serialized = json.dumps(result, default=str)
    assert isinstance(serialized, str)

    # Keys should be strings, not Timestamp objects
    for col_data in result.values():
        if isinstance(col_data, dict):
            for key in col_data:
                assert isinstance(key, str), f"Key {key!r} is {type(key).__name__}, expected str"


def test_safe_dict_with_timestamp_columns():
    """Financial statements use Timestamp column headers."""
    from mcp_server.handlers.stock_analysis import GetStockAnalysisHandler

    df = pd.DataFrame(
        {"Revenue": [100, 200]},
        index=["row1", "row2"],
    )
    df.columns = pd.to_datetime(["2026-01-01"])

    handler = GetStockAnalysisHandler()
    result = handler._safe_dict(df)
    serialized = json.dumps(result, default=str)
    assert isinstance(serialized, str)

    # Top-level keys should be strings
    for key in result:
        assert isinstance(key, str), f"Column key {key!r} is {type(key).__name__}, expected str"


def test_safe_dict_with_none():
    from mcp_server.handlers.stock_analysis import GetStockAnalysisHandler
    handler = GetStockAnalysisHandler()
    assert handler._safe_dict(None) == {}


def test_safe_dict_with_empty_dataframe():
    from mcp_server.handlers.stock_analysis import GetStockAnalysisHandler
    handler = GetStockAnalysisHandler()
    assert handler._safe_dict(pd.DataFrame()) == {}


def test_safe_dict_with_plain_dict():
    from mcp_server.handlers.stock_analysis import GetStockAnalysisHandler
    handler = GetStockAnalysisHandler()
    d = {"target_mean": 250.0}
    assert handler._safe_dict(d) == d
```

**Step 2: Run test to verify it fails**

Run: `cd Main/backend && python -m pytest tests/test_stock_analysis_serialization.py -v`
Expected: `test_safe_dict_with_timestamp_index` FAIL with `AttributeError` (method not accessible) or `TypeError: keys must be str`

**Step 3: Implement the fix**

In `main/backend/mcp_server/handlers/stock_analysis.py`, replace the `_safe_dict` function (lines 40-49) and make it a static method on the class so tests can access it:

Replace lines 18-61 with:

```python
class GetStockAnalysisHandler(ToolHandler):
    """Handler for get_stock_analysis tool."""

    @staticmethod
    def _safe_dict(df):
        """Convert DataFrame/dict to a JSON-safe dict.

        Stringifies index and column labels so pd.Timestamp keys
        don't crash json.dumps (which only applies default= to values, not keys).
        """
        if df is None:
            return {}
        if hasattr(df, 'empty') and df.empty:
            return {}
        if hasattr(df, 'to_dict'):
            df = df.copy()
            df.index = df.index.astype(str)
            df.columns = df.columns.astype(str)
            return df.to_dict()
        if isinstance(df, dict):
            return df
        return {}

    async def execute(self, ctx: ToolContext) -> List[types.TextContent]:
        """Execute get_stock_analysis tool."""
        stock = await get_ticker(ctx.ticker)

        recommendations, recommendations_summary, upgrades_downgrades, price_targets = await asyncio.gather(
            run_in_executor(lambda: stock.recommendations),
            run_in_executor(lambda: stock.recommendations_summary),
            run_in_executor(lambda: stock.upgrades_downgrades),
            run_in_executor(lambda: stock.analyst_price_targets),
        )

        analysis = {
            "recommendations": self._safe_dict(recommendations),
            "recommendations_summary": self._safe_dict(recommendations_summary),
            "upgrades_downgrades": self._safe_dict(upgrades_downgrades),
            "analyst_price_targets": self._safe_dict(price_targets),
        }

        return [types.TextContent(
            type="text",
            text=json.dumps(analysis, indent=2, default=str)
        )]
```

**Step 4: Run test to verify it passes**

Run: `cd Main/backend && python -m pytest tests/test_stock_analysis_serialization.py -v`
Expected: All 5 tests PASS

**Step 5: Commit**

```bash
git add main/backend/mcp_server/handlers/stock_analysis.py Main/backend/tests/test_stock_analysis_serialization.py
git commit -m "fix: stringify DataFrame index/columns in stock_analysis to prevent Timestamp key TypeError"
```

---

### Task 2: Fix Timestamp key serialization in `earnings_info.py`

**Files:**
- Modify: `main/backend/mcp_server/handlers/earnings_info.py:19-28`
- Test: `Main/backend/tests/test_earnings_serialization.py`

**Step 1: Write the failing test**

Create `Main/backend/tests/test_earnings_serialization.py`:

```python
"""Tests for earnings_info Timestamp key serialization fix."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import json
import pandas as pd
from mcp_server.handlers.earnings_info import _safe_df_to_dict


def test_safe_df_to_dict_with_timestamp_index():
    """earnings_dates DataFrame has DatetimeIndex."""
    df = pd.DataFrame(
        {"EPS Estimate": [3.25, 3.50], "Reported EPS": [3.30, None]},
        index=pd.to_datetime(["2026-01-30", "2026-04-30"]),
    )
    result = _safe_df_to_dict(df)
    serialized = json.dumps(result, default=str)
    assert isinstance(serialized, str)

    for col_data in result.values():
        if isinstance(col_data, dict):
            for key in col_data:
                assert isinstance(key, str)


def test_safe_df_to_dict_none():
    assert _safe_df_to_dict(None) == {}


def test_safe_df_to_dict_empty():
    assert _safe_df_to_dict(pd.DataFrame()) == {}


def test_safe_df_to_dict_plain_dict():
    d = {"next_earnings": "2026-04-30"}
    assert _safe_df_to_dict(d) == d
```

**Step 2: Run test to verify it fails**

Run: `cd Main/backend && python -m pytest tests/test_earnings_serialization.py::test_safe_df_to_dict_with_timestamp_index -v`
Expected: FAIL — Timestamp keys survive `to_dict()`, `isinstance(key, str)` assertion fails

**Step 3: Implement the fix**

In `main/backend/mcp_server/handlers/earnings_info.py`, replace `_safe_df_to_dict` (lines 19-28):

```python
def _safe_df_to_dict(df) -> dict:
    """Convert a DataFrame to dict, handling None, empty, and Timestamp key cases."""
    if df is None or (isinstance(df, pd.DataFrame) and df.empty):
        return {}
    if isinstance(df, pd.DataFrame):
        df = df.copy()
        df.index = df.index.astype(str)
        df.columns = df.columns.astype(str)
        return df.to_dict()
    if isinstance(df, dict):
        return df
    return {}
```

**Step 4: Run test to verify it passes**

Run: `cd Main/backend && python -m pytest tests/test_earnings_serialization.py -v`
Expected: All 4 tests PASS

**Step 5: Commit**

```bash
git add main/backend/mcp_server/handlers/earnings_info.py Main/backend/tests/test_earnings_serialization.py
git commit -m "fix: stringify DataFrame index/columns in earnings_info to prevent Timestamp key TypeError"
```

---

### Task 3: Fix Timestamp key serialization in `stock_financials.py`

**Files:**
- Modify: `main/backend/mcp_server/handlers/stock_financials.py:39-43`
- Test: `Main/backend/tests/test_financials_serialization.py`

**Step 1: Write the failing test**

Create `Main/backend/tests/test_financials_serialization.py`:

```python
"""Tests for stock_financials Timestamp column key serialization."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import json
import pandas as pd


def _safe_financials_to_dict(df):
    """Mirror the inline logic from stock_financials.py."""
    if df.empty:
        return {}
    return df.to_dict()


def test_financials_timestamp_columns_crash():
    """Financial statement DataFrames use Timestamp column headers (quarterly dates)."""
    df = pd.DataFrame(
        {"Revenue": [100_000, 200_000], "NetIncome": [10_000, 20_000]},
        index=["Revenue", "NetIncome"],
    )
    df.columns = pd.to_datetime(["2025-09-30", "2025-12-31"])

    result = _safe_financials_to_dict(df)

    # This should crash with current code
    try:
        json.dumps(result, default=str)
        assert False, "Expected TypeError for Timestamp keys"
    except TypeError:
        pass  # Confirms the bug exists


def test_financials_safe_dict_after_fix():
    """After fix, Timestamp columns should be stringified."""
    df = pd.DataFrame(
        {"Revenue": [100_000, 200_000], "NetIncome": [10_000, 20_000]},
        index=["Revenue", "NetIncome"],
    )
    df.columns = pd.to_datetime(["2025-09-30", "2025-12-31"])

    # Apply the fix inline
    df_copy = df.copy()
    df_copy.index = df_copy.index.astype(str)
    df_copy.columns = df_copy.columns.astype(str)
    result = df_copy.to_dict()

    serialized = json.dumps(result, default=str)
    assert isinstance(serialized, str)
    for key in result:
        assert isinstance(key, str)
```

**Step 2: Run test to verify `test_financials_timestamp_columns_crash` confirms the bug**

Run: `cd Main/backend && python -m pytest tests/test_financials_serialization.py::test_financials_timestamp_columns_crash -v`
Expected: PASS (confirms the bug — the try/except catches TypeError)

**Step 3: Implement the fix**

In `main/backend/mcp_server/handlers/stock_financials.py`, add a helper and replace the inline `.to_dict()` calls. Replace lines 17-56:

```python
def _safe_financials_to_dict(df) -> dict:
    """Convert financial DataFrame to dict, stringifying Timestamp index/columns."""
    if df is None or df.empty:
        return {}
    df = df.copy()
    df.index = df.index.astype(str)
    df.columns = df.columns.astype(str)
    return df.to_dict()


class GetStockFinancialsHandler(ToolHandler):
    """Handler for get_stock_financials tool."""

    async def execute(self, ctx: ToolContext) -> List[types.TextContent]:
        """Execute get_stock_financials tool."""
        stock = await get_ticker(ctx.ticker)

        income_stmt, balance_sheet, cashflow = await asyncio.gather(
            run_in_executor(lambda: stock.income_stmt),
            run_in_executor(lambda: stock.balance_sheet),
            run_in_executor(lambda: stock.cashflow),
        )

        financials = {
            "income_statement": _safe_financials_to_dict(income_stmt),
            "balance_sheet": _safe_financials_to_dict(balance_sheet),
            "cash_flow": _safe_financials_to_dict(cashflow),
        }

        if all(v == {} for v in financials.values()):
            return [types.TextContent(
                type="text",
                text=f"No financial statements available for {ctx.ticker}. "
                     "Financial data is only available for individual stocks, not indices or funds."
            )]

        return [types.TextContent(
            type="text",
            text=json.dumps(financials, indent=2, default=str)
        )]
```

Note: add `import asyncio` to the imports at line 3 (it's currently missing and was working only because `asyncio.gather` was called without explicit import — verify).

**Step 4: Run test to verify it passes**

Run: `cd Main/backend && python -m pytest tests/test_financials_serialization.py -v`
Expected: Both tests PASS

**Step 5: Commit**

```bash
git add main/backend/mcp_server/handlers/stock_financials.py Main/backend/tests/test_financials_serialization.py
git commit -m "fix: stringify DataFrame index/columns in stock_financials to prevent Timestamp key TypeError"
```

---

### Task 4: Handle `MaxTurnsExceeded` gracefully and make `max_turns` configurable

**Files:**
- Modify: `main/backend/datascraper/datascraper.py:1182-1276`

**Step 1: Add the `MaxTurnsExceeded` import and `MAX_AGENT_TURNS` env var**

At the top of the `_stream()` function (around line 1154), add the import. Then at line 1182, add the configurable max_turns:

```python
async def _stream() -> AsyncIterator[str]:
    from agents import Runner
    from agents.exceptions import MaxTurnsExceeded
    # ... existing code ...

    MAX_RETRIES = 2
    MAX_AGENT_TURNS = int(os.getenv("AGENT_MAX_TURNS", "10"))
    retry_count = 0
```

**Step 2: Pass `max_turns` to Runner calls**

Replace line 1236:
```python
# Before:
result = await Runner.run(agent, current_full_prompt)
# After:
result = await Runner.run(agent, current_full_prompt, max_turns=MAX_AGENT_TURNS)
```

Replace line 1243:
```python
# Before:
result = Runner.run_streamed(agent, current_full_prompt)
# After:
result = Runner.run_streamed(agent, current_full_prompt, max_turns=MAX_AGENT_TURNS)
```

**Step 3: Catch `MaxTurnsExceeded` separately — don't retry**

In the except block (line 1265), add a specific handler BEFORE the generic `Exception` catch:

```python
except MaxTurnsExceeded as mte:
    logging.error(f"[AGENT STREAM] Turn limit ({MAX_AGENT_TURNS}) reached: {mte}")
    if not has_yielded:
        yield "I wasn't able to fully answer this question within the allowed steps. Please try rephrasing your question or breaking it into smaller parts."
    break

except Exception as stream_error:
    # ... existing retry logic unchanged ...
```

**Step 4: Verify manually**

No unit test needed — this is error handling in the streaming path. Verify by checking the code compiles:
Run: `cd Main/backend && python -c "from datascraper.datascraper import create_agent_response_stream; print('OK')"`
Expected: `OK`

**Step 5: Commit**

```bash
git add main/backend/datascraper/datascraper.py
git commit -m "fix: stop retrying MaxTurnsExceeded, make max_turns configurable via AGENT_MAX_TURNS env var"
```

---

### Task 5: Add `get_options_summary` MCP tool

**Files:**
- Create: `main/backend/mcp_server/handlers/options_summary.py`
- Modify: `main/backend/mcp_server/yahoo_finance_server.py` (import + registry + tool schema)
- Test: `Main/backend/tests/test_options_summary.py`

**Step 1: Write the failing test**

Create `Main/backend/tests/test_options_summary.py`:

```python
"""Tests for get_options_summary handler."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import json
import math
import pandas as pd
from mcp_server.handlers.options_summary import aggregate_chain


def _make_chain(call_vols, put_vols, call_oi, put_oi):
    """Create a mock option chain with calls and puts DataFrames."""
    calls = pd.DataFrame({
        "volume": call_vols,
        "openInterest": call_oi,
        "strike": [100.0] * len(call_vols),
    })
    puts = pd.DataFrame({
        "volume": put_vols,
        "openInterest": put_oi,
        "strike": [100.0] * len(put_vols),
    })

    class Chain:
        pass

    c = Chain()
    c.calls = calls
    c.puts = puts
    return c


def test_aggregate_chain_basic():
    chain = _make_chain(
        call_vols=[100, 200, float("nan")],
        put_vols=[50, 150, 100],
        call_oi=[1000, 2000, 500],
        put_oi=[800, 1200, 400],
    )
    result = aggregate_chain(chain, "2026-03-21")
    assert result["expiration"] == "2026-03-21"
    assert result["call_volume"] == 300       # 100 + 200, NaN skipped
    assert result["put_volume"] == 300        # 50 + 150 + 100
    assert result["total_volume"] == 600
    assert result["call_oi"] == 3500
    assert result["put_oi"] == 2400
    assert result["total_oi"] == 5900
    assert abs(result["put_call_ratio"] - 1.0) < 0.01


def test_aggregate_chain_zero_call_volume():
    chain = _make_chain(
        call_vols=[0, 0],
        put_vols=[100, 200],
        call_oi=[0, 0],
        put_oi=[500, 600],
    )
    result = aggregate_chain(chain, "2026-03-21")
    assert result["call_volume"] == 0
    assert result["put_volume"] == 300
    assert result["put_call_ratio"] is None  # Division by zero guard


def test_aggregate_chain_all_nan():
    chain = _make_chain(
        call_vols=[float("nan")],
        put_vols=[float("nan")],
        call_oi=[float("nan")],
        put_oi=[float("nan")],
    )
    result = aggregate_chain(chain, "2026-03-21")
    assert result["call_volume"] == 0
    assert result["put_volume"] == 0
    assert result["total_volume"] == 0
```

**Step 2: Run test to verify it fails**

Run: `cd Main/backend && python -m pytest tests/test_options_summary.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'mcp_server.handlers.options_summary'`

**Step 3: Implement the handler**

Create `main/backend/mcp_server/handlers/options_summary.py`:

```python
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

    # Handle NaN sums (all-NaN columns sum to 0 with skipna=True, but check anyway)
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
```

**Step 4: Run tests to verify they pass**

Run: `cd Main/backend && python -m pytest tests/test_options_summary.py -v`
Expected: All 3 tests PASS

**Step 5: Register the tool in `yahoo_finance_server.py`**

Add import at line 19 (after `GetOptionsChainHandler`):

```python
from mcp_server.handlers.options_summary import GetOptionsSummaryHandler
```

Add to `TOOL_HANDLERS` dict (after `get_options_chain` entry):

```python
"get_options_summary": GetOptionsSummaryHandler(),
```

Add tool schema to `handle_list_tools()` (after the `get_options_chain` Tool entry, before `get_holders`):

```python
types.Tool(
    name="get_options_summary",
    description="Get aggregated options activity summary for a stock: total call/put volume, open interest, and put/call ratio across the nearest expiration dates. Use this for questions about overall options activity, flow, or volume. For detailed strike-by-strike data, use get_options_chain instead.",
    inputSchema={
        "type": "object",
        "properties": {
            "ticker": {
                "type": "string",
                "description": "The ticker symbol (e.g., 'AVGO', 'AAPL', 'TSLA')."
            }
        },
        "required": ["ticker"],
    },
),
```

**Step 6: Commit**

```bash
git add main/backend/mcp_server/handlers/options_summary.py main/backend/mcp_server/yahoo_finance_server.py Main/backend/tests/test_options_summary.py
git commit -m "feat: add get_options_summary MCP tool for aggregate options volume/OI/P:C ratio"
```

---

### Task 6: Bump Playwright Docker image version

**Files:**
- Modify: `main/backend/Dockerfile:1`

**Step 1: Update the base image**

In `main/backend/Dockerfile`, line 1:

```dockerfile
# Before:
FROM mcr.microsoft.com/playwright/python:v1.48.0-jammy
# After:
FROM mcr.microsoft.com/playwright/python:v1.58.0-jammy
```

Also update the symlink on line 46 — the new Playwright version uses `chromium_headless_shell-*` instead of `chromium-*`:

```dockerfile
# Before:
RUN ln -sf /ms-playwright/chromium-*/chrome-linux/chrome /usr/bin/chromium-bundled
# After:
RUN ln -sf /ms-playwright/chromium_headless_shell-*/chrome-headless-shell-linux64/chrome-headless-shell /usr/bin/chromium-bundled
```

And update the browser check on lines 49-52:

```dockerfile
# Before:
RUN echo "Verifying Playwright browsers..." && \
    ls -la /ms-playwright/ && \
    test -d /ms-playwright/chromium-* && \
    echo "✓ Chromium browser found at /ms-playwright"
# After:
RUN echo "Verifying Playwright browsers..." && \
    ls -la /ms-playwright/ && \
    test -d /ms-playwright/chromium_headless_shell-* && \
    echo "✓ Chromium browser found at /ms-playwright"
```

**Step 2: Verify the Dockerfile parses**

Run: `cd main/backend && docker build --check . 2>&1 || echo "Docker not available locally - verify on deploy"`

Note: The Docker build may not work locally (WSL2 environment). The image change will be verified on next deploy. The key change is matching the image tag to the installed Playwright package version.

**Step 3: Commit**

```bash
git add main/backend/Dockerfile
git commit -m "fix: bump Playwright Docker image v1.48.0 -> v1.58.0 to match installed package version"
```

---

## Summary

| Task | Bug | Type | Risk |
|------|-----|------|------|
| 1 | `stock_analysis` Timestamp keys | Bugfix | Low — isolated to one handler |
| 2 | `earnings_info` Timestamp keys | Bugfix | Low — same pattern |
| 3 | `stock_financials` Timestamp keys | Bugfix | Low — same pattern |
| 4 | `MaxTurnsExceeded` retry + configurable turns | Bugfix | Low — only changes error path |
| 5 | New `get_options_summary` tool | Feature | Low — additive, doesn't modify existing tools |
| 6 | Playwright Docker image version | Bugfix | Medium — requires rebuild + deploy |

**Execution order:** Tasks 1-3 are independent. Task 4 is independent. Task 5 depends on nothing. Task 6 is independent. All can be parallelized.
