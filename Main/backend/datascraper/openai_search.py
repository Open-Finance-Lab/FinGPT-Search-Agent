"""
OpenAI Responses API integration for web search functionality.

Optimized version with preview/snippet functionality removed for better performance.
"""

import os
import re
import logging
import asyncio
import json
from typing import List, Dict, Optional, Any, Iterable, AsyncGenerator, Tuple, Set
from urllib.parse import urlparse
from openai import OpenAI, AsyncOpenAI
from dotenv import load_dotenv
from pathlib import Path

# Load environment variables
backend_dir = Path(__file__).resolve().parent.parent
load_dotenv(backend_dir / '.env')

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Initialize OpenAI client lazily to allow imports without secrets (e.g., CI)
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

if not OPENAI_API_KEY:
    logger.warning("OPENAI_API_KEY missing; OpenAI-backed features will be unavailable until configured.")
    sync_client = None
    async_client = None
else:
    sync_client = OpenAI(api_key=OPENAI_API_KEY)
    async_client = AsyncOpenAI(api_key=OPENAI_API_KEY)

# Feature flag for using Responses API (can be controlled via env var)
USE_RESPONSES_API = os.getenv("USE_OPENAI_RESPONSES_API", "true").lower() == "true"


def _get_site_name(url: str) -> str:
    """Extract a readable site name from URL."""
    try:
        hostname = urlparse(url).netloc
        if not hostname:
            return "Source"

        # Remove www prefix
        hostname = re.sub(r'^www\.', '', hostname, flags=re.IGNORECASE)

        # Extract site name from domain
        parts = hostname.split('.')
        if len(parts) >= 2:
            # Get the main domain part
            site_name = parts[-2] if parts[-1] in ['com', 'org', 'net', 'edu', 'gov', 'io', 'co'] else parts[0]
            # Capitalize first letter
            return site_name.capitalize()

        return hostname.capitalize()
    except Exception:
        return "Source"


def _format_display_url(url: str, max_length: int = 30) -> str:
    """Format URL for display with truncation."""
    try:
        parsed = urlparse(url)
        display = f"{parsed.netloc}{parsed.path or ''}"
        if parsed.query:
            display += f"?{parsed.query}"

        # Remove www prefix
        display = re.sub(r'^www\.', '', display, flags=re.IGNORECASE)

        # Truncate if too long
        if len(display) > max_length:
            display = display[:max_length - 3] + "..."

        return display
    except Exception:
        return url[:max_length] if len(url) > max_length else url


def extract_citations_from_response(response) -> List[Dict[str, Any]]:
    """
    Extract URL citations from OpenAI Responses API response.

    Args:
        response: The response object from OpenAI Responses API

    Returns:
        List of dictionaries containing citation information
    """
    citations = []

    try:
        # Check if response has output attribute (Responses API structure)
        if hasattr(response, 'output') and response.output:
            for output_item in response.output:
                # Check for message type outputs
                if hasattr(output_item, 'type') and output_item.type == 'message':
                    # Extract content blocks
                    if hasattr(output_item, 'content') and output_item.content:
                        for content_block in output_item.content:
                            # Check for annotations in content blocks
                            if hasattr(content_block, 'annotations') and content_block.annotations:
                                for annotation in content_block.annotations:
                                    # Extract URL citations
                                    if annotation.type == 'url_citation':
                                        citations.append({
                                            'url': annotation.url,
                                            'title': getattr(annotation, 'title', '') or '',
                                            'snippet': getattr(annotation, 'text', '') or getattr(annotation, 'snippet', '') or '',
                                            'type': 'url_citation'
                                        })
                                    elif annotation.type == 'file_citation':
                                        citations.append({
                                            'file_id': getattr(annotation, 'file_id', None),
                                            'quote': getattr(annotation, 'quote', '') or '',
                                            'type': 'file_citation'
                                        })

        # Log citation extraction results
        logger.info(f"Extracted {len(citations)} citations from response")
        for idx, citation in enumerate(citations, 1):
            if citation['type'] == 'url_citation':
                logger.info(f"  Citation {idx}: {citation['url']} - {citation.get('title', 'No title')}")

    except Exception as e:
        logger.error(f"Error extracting citations: {e}")

    return citations


def _normalize_citation_entry(entry: Dict[str, Any]) -> Dict[str, Any]:
    """
    Normalize citation metadata to the structure expected downstream.
    """
    url = entry.get('url')
    if not url:
        return {}

    normalized_title = entry.get('title') or _format_display_url(url)
    snippet = (entry.get('snippet') or '').strip()

    return {
        'url': url,
        'title': normalized_title,
        'snippet': snippet,
        'site_name': entry.get('site_name') or _get_site_name(url),
        'display_url': entry.get('display_url') or _format_display_url(url),
        'icon': None,
        'provisional': bool(entry.get('provisional', False))
    }


_TOOL_URL_PATTERN = re.compile(r'https?://[^\s<>"\'\]]+', re.IGNORECASE)
_MAX_PROVISIONAL_SOURCES = 12


def _safe_json_loads(value: str) -> Optional[Any]:
    """
    Attempt to parse a string as JSON. Returns None if parsing fails.
    """
    try:
        return json.loads(value)
    except Exception:
        return None


def _collect_sources_from_payload(payload: Any, visited_urls: Set[str], seen_nodes: Set[int]) -> List[Dict[str, Any]]:
    """
    Recursively walk payloads emitted by the Responses web_search tool and extract URL candidates.
    """
    if payload is None:
        return []

    node_id = id(payload)
    if node_id in seen_nodes:
        return []
    seen_nodes.add(node_id)

    results: List[Dict[str, Any]] = []
    if isinstance(payload, str):
        payload_str = payload.strip()
        if payload_str.startswith("{") or payload_str.startswith("["):
            parsed = _safe_json_loads(payload_str)
            if parsed is not None:
                results.extend(_collect_sources_from_payload(parsed, visited_urls, seen_nodes))
        else:
            for match in _TOOL_URL_PATTERN.findall(payload_str):
                if len(visited_urls) >= _MAX_PROVISIONAL_SOURCES:
                    break
                if match in visited_urls:
                    continue
                provisional = _normalize_citation_entry({
                    "url": match,
                    "provisional": True
                })
                if provisional:
                    visited_urls.add(match)
                    results.append(provisional)
        return results

    if isinstance(payload, list):
        for item in payload:
            if len(visited_urls) >= _MAX_PROVISIONAL_SOURCES:
                break
            results.extend(_collect_sources_from_payload(item, visited_urls, seen_nodes))
        return results

    if isinstance(payload, dict):
        url = payload.get("url") or payload.get("link") or payload.get("href")
        if url and url not in visited_urls and len(visited_urls) < _MAX_PROVISIONAL_SOURCES:
            entry = {
                "url": url,
                "title": payload.get("title") or payload.get("name") or payload.get("headline") or payload.get("page_title"),
                "snippet": payload.get("snippet") or payload.get("description") or payload.get("summary") or payload.get("text") or "",
                "site_name": payload.get("site_name") or payload.get("source") or payload.get("publisher"),
                "display_url": payload.get("display_url") or payload.get("displayUrl") or payload.get("formattedUrl"),
                "provisional": True
            }
            normalized = _normalize_citation_entry(entry)
            if normalized:
                visited_urls.add(url)
                results.append(normalized)

        candidate_keys = [
            "results", "items", "value", "web_results", "web_pages", "documents",
            "data", "webSearchResults", "entries"
        ]
        for key in candidate_keys:
            if key in payload and len(visited_urls) < _MAX_PROVISIONAL_SOURCES:
                results.extend(_collect_sources_from_payload(payload[key], visited_urls, seen_nodes))

        for value in payload.values():
            if len(visited_urls) >= _MAX_PROVISIONAL_SOURCES:
                break
            results.extend(_collect_sources_from_payload(value, visited_urls, seen_nodes))

        return results

    return results


def _gather_text_fragments(payload: Any, seen_nodes: Set[int]) -> List[str]:
    """
    Recursively collect textual fragments from tool payloads for buffering.
    """
    if payload is None:
        return []

    node_id = id(payload)
    if node_id in seen_nodes:
        return []
    seen_nodes.add(node_id)

    fragments: List[str] = []
    if isinstance(payload, str):
        fragments.append(payload)
        return fragments

    if isinstance(payload, list):
        for item in payload:
            fragments.extend(_gather_text_fragments(item, seen_nodes))
        return fragments

    if isinstance(payload, dict):
        for key in ("text", "output_text", "result", "delta"):
            value = payload.get(key)
            if isinstance(value, str):
                fragments.append(value)
        for value in payload.values():
            fragments.extend(_gather_text_fragments(value, seen_nodes))
        return fragments

    return fragments


def _extract_sources_from_tool_event(event_type: str, event: Any, buffers: Dict[str, List[str]]) -> List[Dict[str, Any]]:
    """
    Parse Responses tool output events to surface provisional sources before citations land.
    """
    if not event_type or "tool" not in event_type:
        return []

    tool_name = getattr(event, "tool_name", None) or getattr(event, "tool_type", None)
    if not tool_name and "web_search" in event_type:
        tool_name = "web_search"

    if tool_name and "web_search" not in str(tool_name):
        return []

    tool_call_id = getattr(event, "tool_call_id", None) or getattr(event, "id", None) or getattr(event, "tool_call", None)
    buffer_key = str(tool_call_id) if tool_call_id is not None else None

    payloads: List[Any] = []
    for attr in ("output_json", "output", "delta", "result", "content"):
        if hasattr(event, attr):
            value = getattr(event, attr)
            if value not in (None, "", []):
                payloads.append(value)

    if event_type.endswith(".delta") and buffer_key:
        fragment_nodes: Set[int] = set()
        for payload in payloads:
            fragments = _gather_text_fragments(payload, fragment_nodes)
            if fragments:
                buffers.setdefault(buffer_key, []).extend(fragments)
        return []

    if buffer_key and buffer_key in buffers:
        buffered_text = "".join(buffers.pop(buffer_key))
        if buffered_text:
            payloads.append(buffered_text)

    collected: List[Dict[str, Any]] = []
    visited_urls: Set[str] = set()
    seen_nodes: Set[int] = set()

    for payload in payloads:
        if len(visited_urls) >= _MAX_PROVISIONAL_SOURCES:
            break
        extracted = _collect_sources_from_payload(payload, visited_urls, seen_nodes)
        if extracted:
            collected.extend(extracted)

    return collected


def prepare_search_prompt(user_query: str, preferred_domains: List[str] = None) -> str:
    """
    Prepare an enhanced prompt that guides the web search behavior.

    Args:
        user_query: The user's original question
        preferred_domains: List of preferred domains to search

    Returns:
        Enhanced prompt string
    """
    prompt_parts = []

    # Add domain preferences if provided
    if preferred_domains:
        domains_str = ', '.join(preferred_domains)
        prompt_parts.append(f"When searching, prioritize these sources: {domains_str}")

    # Add the user query
    prompt_parts.append(user_query)

    # Add instruction for comprehensive search
    prompt_parts.append("\nProvide a comprehensive answer with citations from multiple reputable sources.")

    return '\n'.join(prompt_parts)


async def create_responses_api_search_async(
    user_query: str,
    message_history: List[Dict[str, str]],
    model: str = "gpt-4o-mini",
    preferred_links: List[str] = None,
    stream: bool = False,
    user_timezone: str = None,
    user_time: str = None
):
    """
    Async version: Create a response using OpenAI Responses API with web search.

    Args:
        user_query: The user's question
        message_history: Previous conversation messages
        model: OpenAI model to use (must support Responses API)
        preferred_links: List of preferred URLs/domains to search
        stream: If True, returns async generator; if False, returns Tuple[str, List[Dict[str, Any]]]
        user_timezone: User's IANA timezone
        user_time: User's current time in ISO format

    Returns:
        If stream=False: Tuple of (response_text, list_of_source_entries)
        If stream=True: Async generator yielding (chunk_text, source_entries) tuples
    """
    if async_client is None:
        raise RuntimeError("OPENAI_API_KEY is not configured; cannot execute OpenAI search.")

    try:
        # Extract domains from preferred links
        preferred_domains = []
        if preferred_links:
            for link in preferred_links:
                # Extract domain from URL
                domain = urlparse(link).netloc
                if domain and domain not in preferred_domains:
                    preferred_domains.append(domain)

        # Prepare enhanced prompt
        enhanced_prompt = prepare_search_prompt(user_query, preferred_domains)

        # Build system instructions with timezone/time context
        system_instructions = (
            "Instructions: You are an expert and a helpful financial assistant with access to web search. "
            "Decide whether to search based on intent: use web_search when the question needs external or current information; "
            "if the user asks to recap/summarize/clarify something from this conversation, answer from the existing messages and do NOT search. "
            "Cite your sources inline and provide comprehensive, accurate answers based on calculations or fetched sources. "
            "Focus on factual information from reputable sources. "
            "\n\nIMPORTANT - Mathematical Formatting:\n"
            "Use LaTeX with $ for inline math and $$ for display equations.\n\n"
            "Display equations - use $$...$$:\n"
            "$$C = S_0 N(d_1) - K e^{-rT} N(d_2)$$\n"
            "$$d_1 = \\frac{\\ln(S_0/K) + (r + \\sigma^2/2)T}{\\sigma\\sqrt{T}}$$\n\n"
            "Inline math - use $...$:\n"
            "where $S_0 = 262.76$, $K = 270$, $r = 0.05$, $\\sigma = 0.2974$\n\n"
            "Do NOT use:\n"
            "- Square brackets [...] for equations\n"
            "- Plain text like S0 = 100 or d1 ≈ -0.0976\n"
            "- Parentheses (S_0) for inline variables\n"
            "- Unicode symbols like ≈ or · outside of $ delimiters"
        )

        # Add timezone and time information if available
        if user_timezone or user_time:
            from datetime import datetime
            import pytz

            time_info_parts = []
            if user_timezone and user_time:
                try:
                    # Parse ISO time and convert to user's timezone
                    utc_time = datetime.fromisoformat(user_time.replace('Z', '+00:00'))
                    user_tz = pytz.timezone(user_timezone)
                    local_time = utc_time.astimezone(user_tz)

                    time_info_parts.append(f"User's timezone: {user_timezone}")
                    time_info_parts.append(f"Current local time for user: {local_time.strftime('%Y-%m-%d %H:%M:%S %Z')}")
                except Exception as e:
                    logger.warning(f"Error formatting time info in search: {e}")
                    if user_timezone:
                        time_info_parts.append(f"User's timezone: {user_timezone}")
            elif user_timezone:
                time_info_parts.append(f"User's timezone: {user_timezone}")

            if time_info_parts:
                system_instructions += f"\n\n[TIME CONTEXT]: {' | '.join(time_info_parts)}"

        # Build conversation context from message_history
        conversation_context = ""

        # Process message history to include full conversation
        if message_history:
            # Extract system message
            system_msg = None
            conversation_parts = []

            for msg in message_history:
                content = msg.get('content', '')

                if content.startswith("[SYSTEM MESSAGE]:"):
                    # Extract system message content
                    system_msg = content.replace("[SYSTEM MESSAGE]:", "").strip()
                elif content.startswith("[USER MESSAGE]:"):
                    # Add user message
                    user_content = content.replace("[USER MESSAGE]:", "").strip()
                    conversation_parts.append(f"User: {user_content}")
                elif content.startswith("[ASSISTANT MESSAGE]:"):
                    # Add assistant message
                    assistant_content = content.replace("[ASSISTANT MESSAGE]:", "").strip()
                    conversation_parts.append(f"Assistant: {assistant_content}")

            # Use extracted system message if available, otherwise use default
            if system_msg:
                system_instructions = system_msg + "\n\n" + system_instructions

            # Add conversation history if it exists (excluding the current query which is the last user message)
            if len(conversation_parts) > 1:  # More than just the current question
                conversation_context = "\n\n[CONVERSATION HISTORY]:\n" + "\n".join(conversation_parts[:-1])

        # Combine all parts: system instructions, conversation history, and current query
        combined_input = system_instructions
        if conversation_context:
            combined_input += conversation_context
        combined_input += f"\n\n[CURRENT QUERY]:\n{enhanced_prompt}"

        logger.info(f"Calling OpenAI Responses API with model: {model} (stream={stream})")
        logger.info(f"Web search enabled for query: {user_query[:100]}...")
        logger.info(f"Including {len(message_history)} messages from conversation history")

        response = await async_client.responses.create(
            model=model,
            input=combined_input,
            tools=[{"type": "web_search"}],
            tool_choice="auto",
            parallel_tool_calls=True,
            stream=stream
        )

        if stream:
            return _stream_response_chunks(response)

        response_text = ""
        if hasattr(response, 'output_text') and response.output_text:
            response_text = response.output_text
        elif hasattr(response, 'output') and response.output:
            if isinstance(response.output, str):
                response_text = response.output
            elif isinstance(response.output, list):
                for item in response.output:
                    if hasattr(item, 'content'):
                        response_text = str(item.content)
                        break

        if not response_text:
            logger.warning("Could not extract text from response. Response structure may have changed.")

        citations = extract_citations_from_response(response)
        source_entries: List[Dict[str, Any]] = []
        seen_urls: set[str] = set()

        for citation in citations:
            if citation.get('type') != 'url_citation':
                continue
            normalized = _normalize_citation_entry(citation)
            url = normalized.get('url')
            if not url or url in seen_urls:
                continue
            source_entries.append(normalized)
            seen_urls.add(url)

        logger.info(f"Response generated successfully with {len(source_entries)} unique source URLs")

        return response_text, source_entries

    except Exception as e:
        error_msg = f"Error in Responses API search: {str(e)}"
        if "unexpected keyword argument" in str(e).lower():
            error_msg += " (API parameter issue - check OpenAI SDK version)"
        elif "not found" in str(e).lower():
            error_msg += f" (Model '{model}' may not support Responses API)"
        elif "api key" in str(e).lower():
            error_msg += " (Authentication issue - check OPENAI_API_KEY)"

        logger.error(error_msg)
        raise Exception(error_msg) from e


async def _stream_response_chunks(stream_response) -> AsyncGenerator[Tuple[str, List[Dict[str, Any]]], None]:
    """
    Async generator that yields text chunks from streaming Responses API.
    Also collects source URLs and yields them incrementally, falling back to a final
    snapshot if no intermediate events triggered updates.

    Yields:
        Tuples of (chunk_text, source_entries)
        During streaming text: (chunk_text, [])
        On source updates: ("", source_entries) with current ordering
        Final chunk: ("", source_entries)
    """
    full_response = ""
    final_response = None
    source_order: list[str] = []
    source_map: Dict[str, Dict[str, Any]] = {}
    last_signature: Optional[List[Tuple[str, str, str, bool]]] = None
    tool_output_buffers: Dict[str, List[str]] = {}

    def _current_snapshot(force: bool = False) -> Optional[List[Dict[str, Any]]]:
        nonlocal last_signature
        ordered = [source_map[url] for url in source_order if url in source_map]
        signature = [
            (
                entry.get("url"),
                entry.get("title"),
                entry.get("snippet"),
                bool(entry.get("provisional"))
            )
            for entry in ordered
        ]
        if force or signature != last_signature:
            last_signature = signature
            return [dict(entry) for entry in ordered]
        return None

    def upsert_citation(entry: Dict[str, Any], *, provisional: Optional[bool] = None) -> bool:
        candidate = dict(entry)
        if provisional is not None:
            candidate["provisional"] = provisional

        normalized = _normalize_citation_entry(candidate)
        url = normalized.get('url')
        if not url:
            return False

        if url not in source_map:
            source_map[url] = normalized
            source_order.append(url)
            return True

        changed = False
        current = source_map[url]
        for key, value in normalized.items():
            if key == 'url':
                continue
            if key == 'provisional':
                desired = bool(value)
                existing = bool(current.get('provisional'))
                if desired != existing:
                    current['provisional'] = desired
                    changed = True
                continue
            if value and value != current.get(key):
                current[key] = value
                changed = True
        return changed

    try:
        async for event in stream_response:
            event_type = getattr(event, "type", "") or ""
            changed = False

            if event_type == "response.output_text.delta":
                delta = getattr(event, "delta", "")
                text = getattr(delta, "text", "") if hasattr(delta, "text") else delta or ""
                if text:
                    full_response += text
                    yield (text, [])
                continue

            if event_type == "response.refusal.delta":
                delta = getattr(event, "delta", "")
                text = getattr(delta, "text", "") if hasattr(delta, "text") else delta or ""
                if text:
                    full_response += text
                    yield (text, [])
                continue

            if event_type in ("response.citation.delta", "response.citation.done"):
                citation = getattr(event, "citation", None)
                if citation:
                    entry = {
                        "url": getattr(citation, "url", None),
                        "title": getattr(citation, "title", None),
                        "snippet": getattr(citation, "snippet", None) or getattr(citation, "text", None),
                        "site_name": getattr(citation, "site_name", None),
                        "display_url": getattr(citation, "display_url", None),
                    }
                    changed = upsert_citation(entry, provisional=False)
            elif event_type == "response.error":
                error_obj = getattr(event, "error", None)
                message = getattr(error_obj, "message", None) if error_obj else None
                raise RuntimeError(message or "Responses API streaming error")
            elif event_type == "response.completed":
                final_response = getattr(event, "response", None)
            elif event_type == "response.output_text.done":
                pass
            else:
                if event_type.startswith("response.tool"):
                    provisional_sources = _extract_sources_from_tool_event(event_type, event, tool_output_buffers)
                    for provisional_entry in provisional_sources:
                        changed = upsert_citation(provisional_entry, provisional=True) or changed
                else:
                    continue

            if changed:
                snapshot = _current_snapshot()
                if snapshot:
                    yield ("", snapshot)

        if not final_response:
            get_final = getattr(stream_response, "get_final_response", None)
            if callable(get_final):
                try:
                    final_candidate = await get_final()
                    if final_candidate:
                        final_response = final_candidate
                except Exception as final_err:
                    logger.debug(f"Unable to fetch final streamed response: {final_err}")

        if tool_output_buffers:
            visited_flush: Set[str] = set()
            flushed = False
            for fragments in list(tool_output_buffers.values()):
                buffered_text = "".join(fragments)
                if not buffered_text:
                    continue
                extracted = _collect_sources_from_payload(buffered_text, visited_flush, set())
                for entry in extracted:
                    flushed = upsert_citation(entry, provisional=True) or flushed
            tool_output_buffers.clear()
            if flushed:
                snapshot = _current_snapshot()
                if snapshot:
                    yield ("", snapshot)

        if final_response:
            try:
                citations = extract_citations_from_response(final_response)
                for citation in citations:
                    if citation.get('type') != 'url_citation':
                        continue
                    changed = upsert_citation(citation, provisional=False) or changed
            except Exception as citation_err:
                logger.warning(f"Failed to extract citations from final response: {citation_err}")

        snapshot = _current_snapshot(force=True)
        if snapshot is None:
            snapshot = []
        logger.info(f"Streaming completed with {len(snapshot)} source URLs")
        yield ("", snapshot)

    except Exception as e:
        logger.error(f"Error in streaming response: {e}")
        raise


def create_responses_api_search(
    user_query: str,
    message_history: List[Dict[str, str]],
    model: str = "gpt-4o-mini",
    preferred_links: List[str] = None,
    user_timezone: str = None,
    user_time: str = None
) -> Tuple[str, List[Dict[str, Any]]]:
    """
    Sync wrapper for create_responses_api_search_async.
    """
    if async_client is None:
        raise RuntimeError("OPENAI_API_KEY is not configured; cannot execute OpenAI search.")

    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            task = asyncio.create_task(
                create_responses_api_search_async(
                    user_query,
                    message_history,
                    model,
                    preferred_links,
                    stream=False,
                    user_timezone=user_timezone,
                    user_time=user_time
                )
            )
            return asyncio.run_coroutine_threadsafe(task, loop).result()
        return asyncio.run(
            create_responses_api_search_async(
                user_query,
                message_history,
                model,
                preferred_links,
                stream=False,
                user_timezone=user_timezone,
                user_time=user_time
            )
        )
    except RuntimeError:
        return asyncio.run(
            create_responses_api_search_async(
                user_query,
                message_history,
                model,
                preferred_links,
                stream=False,
                user_timezone=user_timezone,
                user_time=user_time
            )
        )


def format_sources_for_frontend(
    source_entries: Iterable[Dict[str, Any]],
    current_url: Optional[str] = None
) -> Dict[str, Any]:
    """
    Prepare structured source metadata for the frontend.
    Optimized version without preview fetching.

    Args:
        source_entries: Iterable of citation metadata dicts.
        current_url: The user's active page URL.

    Returns:
        Dict with `current_page` metadata and ordered `sources` list.
    """
    entries = []
    seen: set[str] = set()
    current_entry: Optional[Dict[str, Any]] = None

    for raw_entry in source_entries or []:
        url = raw_entry.get("url")
        if not url or url in seen:
            continue
        seen.add(url)

        # Create normalized entry without snippet
        normalized = {
            "url": url,
            "title": raw_entry.get("title") or _format_display_url(url),
            "site_name": raw_entry.get("site_name") or _get_site_name(url),
            "display_url": raw_entry.get("display_url") or _format_display_url(url),
            "snippet": raw_entry.get("snippet") or "",
            "icon": None,  # No icon fetching for performance
            "provisional": bool(raw_entry.get("provisional", False))
        }

        if current_url and url == current_url:
            current_entry = normalized
        else:
            entries.append(normalized)

    # If current page not among sources but we have URL, synthesize entry
    if current_url and not current_entry:
        current_entry = {
            "url": current_url,
            "title": _format_display_url(current_url),
            "site_name": _get_site_name(current_url),
            "display_url": _format_display_url(current_url),
            "snippet": "",
            "icon": None,
            "provisional": False
        }

    return {
        "current_page": current_entry,
        "sources": entries
    }


def is_responses_api_available(model: str) -> bool:
    """
    Check if a model supports the Responses API with web search.

    Args:
        model: Model identifier (can be actual model name or frontend ID)

    Returns:
        True if model supports Responses API, False otherwise
    """
    # Models that support Responses API with web search (per OpenAI docs)
    supported_models = {
        "gpt-4o",
        "gpt-4o-mini",
        "gpt-4o-2024-11-20",
        "gpt-4o-2024-08-06",
        "gpt-4o-2024-05-13",
        "gpt-5-mini",
        "gpt-5-nano",
        "gpt-5-chat",
        "o1-preview",
        "o1-mini"
    }

    model_lower = model.lower()
    for supported in supported_models:
        if supported in model_lower:
            logger.debug(f"Model '{model}' supports Responses API with web search")
            return USE_RESPONSES_API

    logger.info(f"Model '{model}' does not support Responses API with web search - will use fallback")
    return False


# Maintain backward compatibility exports
__all__ = [
    'create_responses_api_search',
    'create_responses_api_search_async',
    'extract_citations_from_response',
    'format_sources_for_frontend',
    'is_responses_api_available',
    'prepare_search_prompt'
]
