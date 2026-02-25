# Memory Leak Fixes Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Fix all P0 and P1 memory leak vectors identified in the pre-deployment audit before pushing the new image to the Fedora droplet.

**Architecture:** Targeted fixes to 5 files — no new dependencies, no architectural changes. Each fix is backward-compatible and independently testable. The fixes address: unbounded Yahoo Finance ticker cache (P0), incomplete event loop cleanup in streaming views (P0), Playwright browser leak on exception paths (P1), and abandoned SSE generator resource retention (P1).

**Tech Stack:** Python 3.12, Django 6.0, Gunicorn (gthread), asyncio, Playwright, yfinance

---

## Summary of Fixes

| Task | Priority | File | Issue |
|------|----------|------|-------|
| 1 | P0 | `mcp_server/cache.py` | TimedCache has no max-size — unbounded growth from yfinance Ticker objects |
| 2 | P0 | `api/views.py` | `adv_response_stream` doesn't restore previous event loop; both streaming views have fragile cleanup |
| 3 | P1 | `datascraper/url_tools.py` | `scrape_with_playwright()` browser.close() not in finally block |
| 4 | P1 | `datascraper/playwright_tools.py` | Remove mutable global state (`_current_browser`, `_current_page`) |
| 5 | P1 | `openai_search.py` | Remove `logging.basicConfig()` at import time (handler accumulation) |

---

### Task 1: Cap TimedCache with max_entries + LRU eviction

**Files:**
- Modify: `Main/backend/mcp_server/cache.py`
- Test: `Main/backend/tests/test_timed_cache.py`

**Problem:** The `TimedCache` stores yfinance Ticker objects (10-50MB each) with no max entry count. Only TTL-based expiration exists, and eviction only runs on `set()`. A burst of diverse ticker queries can push RSS to 500MB+.

**Fix:** Add `max_entries` parameter (default 50). On `set()`, after TTL eviction, if still over limit, evict oldest entries (LRU by insertion time). Also add eviction on `get()` for the specific expired key.

---

### Task 2: Fix event loop lifecycle in streaming views

**Files:**
- Modify: `Main/backend/api/views.py`

**Problem 1:** `adv_response_stream` (line 600) creates a new event loop but does NOT restore the previous loop after cleanup — unlike `chat_response_stream` which does.

**Problem 2:** Both streaming views swallow exceptions from `stream_iter.aclose()` and `loop.shutdown_asyncgens()` with bare `except Exception: pass`, which can mask resource leaks.

**Fix:** Unify both streaming views to use the same robust cleanup pattern: save previous loop, create new loop, iterate, close in finally with logged exceptions, restore previous loop.

---

### Task 3: Fix Playwright browser leak in url_tools

**Files:**
- Modify: `Main/backend/datascraper/url_tools.py`

**Problem:** In `scrape_with_playwright()`, `browser.close()` is called at line 170 inside the `try` block's happy path. If any exception occurs between `browser = p.chromium.launch()` and `browser.close()`, the browser process leaks (~50-100MB).

**Fix:** Move `browser.close()` into a `finally` block.

---

### Task 4: Remove global mutable state from playwright_tools

**Files:**
- Modify: `Main/backend/datascraper/playwright_tools.py`

**Problem:** Module-level globals `_current_browser` and `_current_page` are set inside the `PlaywrightBrowser` context manager. These serve no purpose (nothing reads them outside the CM) and create a risk of state corruption under concurrent requests.

**Fix:** Remove the globals entirely. The context manager already yields the page directly.

---

### Task 5: Remove logging.basicConfig() from openai_search.py

**Files:**
- Modify: `Main/backend/datascraper/openai_search.py`

**Problem:** `logging.basicConfig()` at line 21 runs at import time. In edge cases (module re-import, test runners), this adds duplicate handlers. Django's `LOGGING` setting already handles configuration.

**Fix:** Remove the `logging.basicConfig()` call.

---
