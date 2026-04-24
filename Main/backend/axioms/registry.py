"""Session-scoped claim registry.

The agent calls the `report_claim` MCP tool each time it emits a supported
ratio; claims are stored here keyed by session_id. When the user clicks
Validate, the API view pulls all claims for the session and runs them
through the resolver + engine.

Backed by Django's cache framework (same substrate as UnifiedContextManager),
with a 1-hour TTL. No persistence beyond cache; that's intentional — claims
are tied to a conversational session, not audit history.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List

from django.core.cache import cache

_KEY_PREFIX = "axiom_claims:"
_TTL_SECONDS = 3600  # 1 hour


def _key(session_id: str) -> str:
    return f"{_KEY_PREFIX}{session_id}"


def add_claim(session_id: str, claim: Dict[str, Any]) -> None:
    """Append a claim to the session's claim list.

    Attaches a backend-generated ``claim_id`` so the in-text marking layer
    can join prose spans to validation results. Scheme is
    ``{ratio}-{ticker}-{period}-{n}`` where ``n`` is the claim's index
    within the session — unique within a turn, human-readable in logs.
    """
    if not session_id:
        return
    claim = dict(claim)
    claim.setdefault("emitted_at", datetime.now(timezone.utc).isoformat())
    claims = cache.get(_key(session_id), []) or []
    if "claim_id" not in claim:
        ratio = claim.get("ratio", "ratio")
        ticker = claim.get("ticker", "")
        period = claim.get("period", "")
        claim["claim_id"] = f"{ratio}-{ticker}-{period}-{len(claims)}"
    claims.append(claim)
    cache.set(_key(session_id), claims, _TTL_SECONDS)


def get_claims(session_id: str) -> List[Dict[str, Any]]:
    """Return all claims recorded for the session (oldest first)."""
    if not session_id:
        return []
    return cache.get(_key(session_id), []) or []


def clear_claims(session_id: str) -> None:
    if not session_id:
        return
    cache.delete(_key(session_id))
