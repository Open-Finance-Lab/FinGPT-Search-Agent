"""
Debug logger that dumps the full payload sent to foundation models.

Enable by setting LLM_DEBUG_LOG=true in the environment (or .env).
Outputs to stdout/stderr (Docker terminal) via Python logging.
"""

import os
import json
import logging
import textwrap

logger = logging.getLogger("llm_debug")

LLM_DEBUG_ENABLED = os.getenv("LLM_DEBUG_LOG", "false").lower() in ("true", "1", "yes")

_SEPARATOR = "=" * 80
_THIN_SEP = "-" * 60


def _truncate(text: str, max_chars: int = 500) -> str:
    if len(text) <= max_chars:
        return text
    return text[:max_chars] + f"... [truncated, {len(text)} chars total]"


def _format_message(msg: dict, index: int, verbose: bool) -> str:
    role = msg.get("role", "unknown")
    content = msg.get("content", "")
    char_count = len(content)

    if verbose:
        body = content
    else:
        body = _truncate(content)

    return f"  [{index}] role={role}  ({char_count} chars)\n{textwrap.indent(body, '      ')}"


def log_llm_payload(
    *,
    call_site: str,
    model: str,
    provider: str,
    messages: list | str | None = None,
    stream: bool = False,
    extra: dict | None = None,
):
    """
    Log the full context about to be sent to a foundation model.

    Args:
        call_site: Human-readable label, e.g. "_create_response_sync"
        model: Model name/id being called
        provider: Provider name (openai, anthropic, deepseek, buffet, agent)
        messages: The messages list (or combined_input string for Responses API)
        stream: Whether this is a streaming call
        extra: Any additional metadata to include
    """
    if not LLM_DEBUG_ENABLED:
        return

    lines = [
        "",
        _SEPARATOR,
        f"  LLM PAYLOAD DEBUG  |  {call_site}",
        _SEPARATOR,
        f"  model:    {model}",
        f"  provider: {provider}",
        f"  stream:   {stream}",
    ]

    if extra:
        for k, v in extra.items():
            lines.append(f"  {k}: {v}")

    lines.append(_THIN_SEP)

    # Verbose mode: dump full content (no truncation)
    verbose = os.getenv("LLM_DEBUG_VERBOSE", "false").lower() in ("true", "1", "yes")

    if messages is None:
        lines.append("  [no messages provided]")
    elif isinstance(messages, str):
        char_count = len(messages)
        lines.append(f"  combined_input ({char_count} chars):")
        if verbose:
            lines.append(textwrap.indent(messages, "    "))
        else:
            lines.append(textwrap.indent(_truncate(messages, 1000), "    "))
    elif isinstance(messages, list):
        lines.append(f"  messages ({len(messages)} total):")
        for i, msg in enumerate(messages):
            lines.append(_format_message(msg, i, verbose))
    else:
        lines.append(f"  [unexpected type: {type(messages).__name__}]")
        lines.append(f"  {str(messages)[:500]}")

    # Total token-ish estimate (chars / 4 as rough approximation)
    total_chars = 0
    if isinstance(messages, str):
        total_chars = len(messages)
    elif isinstance(messages, list):
        total_chars = sum(len(m.get("content", "")) for m in messages)

    lines.append(_THIN_SEP)
    lines.append(f"  total chars: {total_chars:,}  (~{total_chars // 4:,} tokens est.)")
    lines.append(_SEPARATOR)
    lines.append("")

    logger.info("\n".join(lines))
