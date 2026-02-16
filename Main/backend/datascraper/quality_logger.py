"""
Response quality logger for monitoring data accuracy in production.

Logs structured quality signals for each response:
- Mode (Thinking / Research)
- Data source path (MCP-first, web search, ETF proxy)
- Response length
- Quality flags (JSON leak detected, numerical mismatch, etc.)

Enable with QUALITY_LOG=true in environment. Outputs to the 'quality' logger.
"""

import os
import json
import time
import logging
from typing import Optional

logger = logging.getLogger("quality")

QUALITY_LOG_ENABLED = os.getenv("QUALITY_LOG", "false").lower() in ("true", "1", "yes")


class QualityTracker:
    """Accumulates quality signals during a single request lifecycle.

    Usage:
        tracker = QualityTracker(mode="research", query="What is AAPL price?")
        tracker.set_data_source("mcp_first")
        tracker.flag("etf_proxy_used", symbol="^GSPC", proxy="SPY")
        tracker.complete(response_text)
    """

    def __init__(self, mode: str, query: str, model: str = ""):
        self.mode = mode
        self.query = query[:120]
        self.model = model
        self.data_source: str = ""
        self.flags: list[dict] = []
        self._start = time.monotonic()

    def set_data_source(self, source: str) -> None:
        """Record which data path produced the response.

        Common values: 'mcp_tools', 'mcp_first', 'web_search', 'etf_proxy', 'direct_llm'
        """
        self.data_source = source

    def flag(self, name: str, **details) -> None:
        """Record a quality signal.

        Args:
            name: Signal name (e.g. 'json_leak_detected', 'numerical_mismatch',
                  'etf_proxy_used', 'mcp_first_fallback', 'source_missing')
            **details: Additional context for the signal
        """
        entry = {"signal": name}
        if details:
            entry.update(details)
        self.flags.append(entry)

    def complete(self, response: Optional[str] = None) -> None:
        """Finalize and emit the quality log entry."""
        if not QUALITY_LOG_ENABLED:
            return

        elapsed_ms = int((time.monotonic() - self._start) * 1000)
        resp_len = len(response) if response else 0

        entry = {
            "mode": self.mode,
            "model": self.model,
            "query": self.query,
            "data_source": self.data_source or "unknown",
            "response_length": resp_len,
            "elapsed_ms": elapsed_ms,
            "flags": self.flags if self.flags else None,
        }
        # Remove None values for cleaner output
        entry = {k: v for k, v in entry.items() if v is not None}

        logger.info(f"[QUALITY] {json.dumps(entry)}")
