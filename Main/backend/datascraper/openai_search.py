"""
OpenAI Responses API integration for web search functionality.

Optimized version with preview/snippet functionality removed for better performance.
"""

import os
import re
import logging
import asyncio
from typing import List, Dict, Optional, Any, Iterable, AsyncGenerator, Tuple
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

# Initialize OpenAI client
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY not found in environment variables")

# Feature flag for using Responses API (can be controlled via env var)
USE_RESPONSES_API = os.getenv("USE_OPENAI_RESPONSES_API", "true").lower() == "true"

# Initialize clients
sync_client = OpenAI(api_key=OPENAI_API_KEY)
async_client = AsyncOpenAI(api_key=OPENAI_API_KEY)


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
    snippet = entry.get('snippet') or ''

    return {
        'url': url,
        'title': normalized_title,
        'snippet': snippet,
        'site_name': entry.get('site_name') or _get_site_name(url),
        'display_url': entry.get('display_url') or _format_display_url(url),
        'icon': None
    }


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
            "Instructions: You are a helpful assistant with access to web search. "
            "Always search for current information when answering questions. "
            "Cite your sources inline and provide comprehensive, accurate answers. "
            "Focus on factual information from reputable sources."
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

        # Combine system instructions with the user prompt (Responses API does not take system role yet)
        combined_input = f"{system_instructions}\n\n{enhanced_prompt}"

        logger.info(f"Calling OpenAI Responses API with model: {model} (stream={stream})")
        logger.info(f"Web search enabled for query: {user_query[:100]}...")

        response = await async_client.responses.create(
            model=model,
            input=combined_input,
            tools=[{"type": "web_search"}],
            tool_choice="auto",
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
    Also collects source URLs and yields them at the end.

    Yields:
        Tuples of (chunk_text, source_entries)
        During streaming: (chunk_text, [])
        Final chunk: ("", source_entries)
    """
    full_response = ""
    final_response = None
    source_order: list[str] = []
    source_map: Dict[str, Dict[str, Any]] = {}

    def upsert_citation(entry: Dict[str, Any]) -> None:
        normalized = _normalize_citation_entry(entry)
        url = normalized.get('url')
        if not url:
            return
        if url not in source_map:
            source_map[url] = normalized
            source_order.append(url)
        else:
            current = source_map[url]
            for key, value in normalized.items():
                if key == 'url':
                    continue
                if value and not current.get(key):
                    current[key] = value

    try:
        async for event in stream_response:
            event_type = getattr(event, "type", None)

            if event_type == "response.output_text.delta":
                delta = getattr(event, "delta", "")
                text = getattr(delta, "text", "") if hasattr(delta, "text") else delta or ""
                if text:
                    full_response += text
                    yield (text, [])
            elif event_type == "response.refusal.delta":
                delta = getattr(event, "delta", "")
                text = getattr(delta, "text", "") if hasattr(delta, "text") else delta or ""
                if text:
                    full_response += text
                    yield (text, [])
            elif event_type in ("response.citation.delta", "response.citation.done"):
                citation = getattr(event, "citation", None)
                if citation:
                    entry = {
                        "url": getattr(citation, "url", None),
                        "title": getattr(citation, "title", None),
                        "snippet": getattr(citation, "snippet", None) or getattr(citation, "text", None),
                    }
                    upsert_citation(entry)
            elif event_type == "response.error":
                error_obj = getattr(event, "error", None)
                message = getattr(error_obj, "message", None) if error_obj else None
                raise RuntimeError(message or "Responses API streaming error")
            elif event_type == "response.completed":
                final_response = getattr(event, "response", None)
            elif event_type == "response.output_text.done":
                continue
            else:
                if event_type and event_type.startswith("response.tool"):
                    output = getattr(event, "output", None)
                    if isinstance(output, str) and output:
                        logger.debug(f"Tool output during streaming: {output[:200]}")
                    elif isinstance(output, list):
                        for entry in output:
                            if isinstance(entry, dict):
                                text = entry.get("output_text") or entry.get("result") or ""
                                if text:
                                    logger.debug(f"Tool output during streaming: {text[:200]}")
                continue

        if not final_response:
            get_final = getattr(stream_response, "get_final_response", None)
            if callable(get_final):
                try:
                    final_candidate = await get_final()
                    if final_candidate:
                        final_response = final_candidate
                except Exception as final_err:
                    logger.debug(f"Unable to fetch final streamed response: {final_err}")

        if final_response:
            try:
                citations = extract_citations_from_response(final_response)
                for citation in citations:
                    if citation.get('type') != 'url_citation':
                        continue
                    upsert_citation(citation)
            except Exception as citation_err:
                logger.warning(f"Failed to extract citations from final response: {citation_err}")

        ordered_sources = [source_map[url] for url in source_order if url in source_map]
        logger.info(f"Streaming completed with {len(ordered_sources)} source URLs")
        yield ("", ordered_sources)

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
            "icon": None  # No icon fetching for performance
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
            "icon": None
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
