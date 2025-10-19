"""
OpenAI Responses API integration for web search functionality.

This module replaces the custom DuckDuckGo + BeautifulSoup scraping
with OpenAI's built-in web_search tool from the Responses API.
"""

import os
import re
import html
import socket
import logging
import asyncio
from html.parser import HTMLParser
from typing import List, Dict, Tuple, Optional, Any, Iterable
from urllib.parse import urlparse
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError
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

_PREVIEW_CACHE: Dict[str, str] = {}
_PREVIEW_FAILURES: set[str] = set()
_MAX_PREVIEW_CACHE_LENGTH = 2048
_PREVIEW_FETCH_TIMEOUT = 6
_PREVIEW_FETCH_BYTES = 65536
_ALLOWED_SCHEMES = {"http", "https"}


class _PreviewHTMLParser(HTMLParser):
    """
    Lightweight HTML parser to collect visible text for previews.
    """

    def __init__(self) -> None:
        super().__init__()
        self._parts: list[str] = []

    def handle_data(self, data: str) -> None:
        if data and not data.isspace():
            self._parts.append(data.strip())

    def get_text(self) -> str:
        return " ".join(self._parts)


def _truncate_preview(text: str, max_chars: int = 160) -> str:
    if not text:
        return ""
    if len(text) <= max_chars:
        return text
    truncated = text[:max_chars].rstrip()
    if len(truncated) < len(text):
        truncated = truncated.rstrip(" ,.;:-")
        return f"{truncated}..."
    return truncated


def _coerce_preview_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, (list, tuple)):
        return " ".join(_coerce_preview_text(item) for item in value if item)
    if isinstance(value, dict):
        for key in ("text", "snippet", "content", "value"):
            if key in value and value[key]:
                return _coerce_preview_text(value[key])
        return ""
    text_attr = getattr(value, "text", None)
    if text_attr:
        return _coerce_preview_text(text_attr)
    snippet_attr = getattr(value, "snippet", None)
    if snippet_attr:
        return _coerce_preview_text(snippet_attr)
    return str(value)


def _normalize_preview_text(value: Any) -> str:
    text = _coerce_preview_text(value)
    if not text:
        return ""
    text = html.unescape(text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _extract_meta_description(html_content: str) -> str:
    if not html_content:
        return ""
    meta_pattern = re.compile(
        r'<meta\s+[^>]*(?:name|property)\s*=\s*["\'](?:description|og:description)["\'][^>]*?>',
        re.IGNORECASE
    )
    content_pattern = re.compile(r'content\s*=\s*["\']([^"\']+)["\']', re.IGNORECASE)
    match = meta_pattern.search(html_content)
    if not match:
        return ""
    tag = match.group(0)
    content_match = content_pattern.search(tag)
    if not content_match:
        return ""
    return html.unescape(content_match.group(1).strip())


def _extract_text_from_html(html_content: str) -> str:
    parser = _PreviewHTMLParser()
    try:
        parser.feed(html_content)
        parser.close()
    except Exception as exc:
        logger.debug(f"HTML parsing error for preview extraction: {exc}")
    return parser.get_text()


def _fetch_preview_from_url(url: str, *, max_chars: int = 160) -> str:
    if not url:
        return ""
    parsed = urlparse(url)
    if parsed.scheme.lower() not in _ALLOWED_SCHEMES:
        return ""
    if url in _PREVIEW_CACHE:
        cached = _PREVIEW_CACHE[url]
        return _truncate_preview(cached, max_chars)
    if url in _PREVIEW_FAILURES:
        return ""

    request = Request(
        url,
        headers={
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/123.0.0.0 Safari/537.36"
            ),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,text/plain;q=0.8,*/*;q=0.5",
            "Accept-Language": "en-US,en;q=0.9",
        },
    )

    try:
        with urlopen(request, timeout=_PREVIEW_FETCH_TIMEOUT) as response:
            content_type = response.headers.get("Content-Type", "") or ""
            charset = response.headers.get_content_charset() or "utf-8"
            raw_content = response.read(_PREVIEW_FETCH_BYTES)
    except (URLError, HTTPError, TimeoutError, ValueError, socket.timeout) as exc:
        logger.debug(f"Unable to fetch preview for {url}: {exc}")
        _PREVIEW_FAILURES.add(url)
        return ""
    except Exception as exc:
        logger.warning(f"Unexpected error fetching preview for {url}: {exc}")
        _PREVIEW_FAILURES.add(url)
        return ""

    try:
        text_content = raw_content.decode(charset, errors="ignore")
    except LookupError:
        text_content = raw_content.decode("utf-8", errors="ignore")

    meta_description = _normalize_preview_text(_extract_meta_description(text_content))
    if meta_description:
        normalized = meta_description
    else:
        if "text/html" in content_type.lower() or "<html" in text_content.lower():
            body_text = _extract_text_from_html(text_content)
        elif "text/" in content_type.lower():
            body_text = text_content
        else:
            body_text = ""
        normalized = _normalize_preview_text(body_text)

    if not normalized:
        _PREVIEW_FAILURES.add(url)
        return ""

    if len(normalized) > _MAX_PREVIEW_CACHE_LENGTH:
        normalized = normalized[:_MAX_PREVIEW_CACHE_LENGTH].rstrip()

    _PREVIEW_CACHE[url] = normalized
    return _truncate_preview(normalized, max_chars)


def extract_citations_from_response(response) -> List[Dict[str, Any]]:
    """
    Extract URL citations from OpenAI Responses API response.

    Args:
        response: The response object from OpenAI Responses API

    Returns:
        List of dictionaries containing citation information:
        [{"url": "...", "title": "...", "type": "url_citation"}, ...]
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
                                    # Also handle file citations if needed
                                    elif annotation.type == 'file_citation':
                                        citations.append({
                                            'file_id': annotation.file_id,
                                            'quote': getattr(annotation, 'quote', ''),
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
    Ensure citation entries contain the expected keys and default values.
    """
    url = entry.get('url')
    if not url:
        return {}

    snippet = _normalize_preview_text(entry.get('snippet'))
    snippet = _truncate_preview(snippet, 160)
    if not snippet:
        snippet = ""

    return {
        'url': url,
        'title': entry.get('title') or '',
        'snippet': snippet,
        'image': entry.get('image') or None,
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
        stream: If True, returns async generator; if False, returns Tuple[str, List[str]]
        user_timezone: User's IANA timezone
        user_time: User's current time in ISO format

    Returns:
        If stream=False: Tuple of (response_text, list_of_source_urls)
        If stream=True: Async generator yielding text chunks
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

        # Combine system instructions with the user prompt (Responses API doesn't accept system parameter)
        combined_input = f"{system_instructions}\n\n{enhanced_prompt}"

        logger.info(f"Calling OpenAI Responses API with model: {model} (stream={stream})")
        logger.info(f"Web search enabled for query: {user_query[:100]}...")

        # Call the Responses API with web_search tool (no system parameter)
        response = await async_client.responses.create(
            model=model,
            input=combined_input,
            tools=[{"type": "web_search"}],  # Enable web search
            tool_choice="auto",  # Let model decide when to search
            stream=stream  # Enable streaming if requested
        )

        if stream:
            # Return async generator for streaming
            return _stream_response_chunks(response)
        else:
            # Extract the response text (non-streaming mode)
            response_text = ""

            # Primary method: check output_text directly
            if hasattr(response, 'output_text') and response.output_text:
                response_text = response.output_text
            # Fallback: check output field for structured content
            elif hasattr(response, 'output') and response.output:
                # The output may contain the text directly or in structured format
                if isinstance(response.output, str):
                    response_text = response.output
                elif isinstance(response.output, list):
                    # Extract text from list of output items
                    for item in response.output:
                        if hasattr(item, 'content'):
                            response_text = str(item.content)
                            break

            if not response_text:
                logger.warning("Could not extract text from response. Response structure may have changed.")

            # Extract citations/sources
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
        # Provide more detailed error information
        error_msg = f"Error in Responses API search: {str(e)}"

        # Check for common errors
        if "unexpected keyword argument" in str(e).lower():
            error_msg += " (API parameter issue - check OpenAI SDK version)"
        elif "not found" in str(e).lower():
            error_msg += f" (Model '{model}' may not support Responses API)"
        elif "api key" in str(e).lower():
            error_msg += " (Authentication issue - check OPENAI_API_KEY)"

        logger.error(error_msg)

        # Include debugging information
        logger.debug(f"Model: {model}, Query: {user_query[:50]}...")
        logger.debug(f"Preferred domains: {preferred_domains if preferred_domains else 'None'}")

        raise Exception(error_msg) from e


async def _stream_response_chunks(stream_response):
    """
    Async generator that yields text chunks from streaming Responses API.
    Also collects source URLs and yields them at the end.

    Yields:
        Tuples of (chunk_text, source_urls_list)
        During streaming: (chunk_text, [])
        Final chunk: ("", source_urls_list)
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
            # Merge new details without overwriting existing non-empty values
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
                # Treat refusal deltas as streamed text so the UI shows the reason
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
                        "image": getattr(citation, "image_url", None),
                    }
                    upsert_citation(entry)
            elif event_type == "response.error":
                error_obj = getattr(event, "error", None)
                message = getattr(error_obj, "message", None) if error_obj else None
                raise RuntimeError(message or "Responses API streaming error")
            elif event_type == "response.completed":
                final_response = getattr(event, "response", None)
            elif event_type == "response.output_text.done":
                # Nothing to do, wait for completed event which carries full payload
                continue
            else:
                # Handle tool outputs that may include interim search notes
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
                # Ignore other event types (logs, metrics, etc.)
                continue

        # Extract citations from the final response if available
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


def _extract_citations_from_content(content) -> List[Dict[str, str]]:
    """
    Extract citations from content object.

    Args:
        content: Content object from streaming response

    Returns:
        List of citation dictionaries
    """
    citations = []

    try:
        if hasattr(content, 'annotations') and content.annotations:
            for annotation in content.annotations:
                if annotation.type == 'url_citation':
                    citations.append({
                        'url': annotation.url,
                        'title': getattr(annotation, 'title', ''),
                        'type': 'url_citation'
                    })
    except Exception as e:
        logger.error(f"Error extracting citations from content: {e}")

    return citations


def create_responses_api_search(
    user_query: str,
    message_history: List[Dict[str, str]],
    model: str = "gpt-4o-mini",
    preferred_links: List[str] = None,
    user_timezone: str = None,
    user_time: str = None
) -> Tuple[str, List[Dict[str, Any]]]:
    """
    Synchronous wrapper for create_responses_api_search_async.

    Args:
        user_query: The user's question
        message_history: Previous conversation messages
        model: OpenAI model to use
        preferred_links: List of preferred URLs/domains
        user_timezone: User's IANA timezone
        user_time: User's current time in ISO format

    Returns:
        Tuple of (response_text, list_of_source_urls)
    """
    # Run the async function in a new event loop if needed
    try:
        # Try to get the current event loop
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # If loop is already running, create a task
            task = asyncio.create_task(
                create_responses_api_search_async(user_query, message_history, model, preferred_links, stream=False, user_timezone=user_timezone, user_time=user_time)
            )
            return asyncio.run_coroutine_threadsafe(task, loop).result()
        else:
            # If no loop is running, use asyncio.run
            return asyncio.run(
                create_responses_api_search_async(user_query, message_history, model, preferred_links, stream=False, user_timezone=user_timezone, user_time=user_time)
            )
    except RuntimeError:
        # No event loop exists, create one
        return asyncio.run(
            create_responses_api_search_async(user_query, message_history, model, preferred_links, stream=False, user_timezone=user_timezone, user_time=user_time)
        )


def _get_site_name(url: str) -> str:
    """
    Generate a human-readable site name from a URL.
    """
    if not url:
        return "Source"

    try:
        parsed = urlparse(url)
        hostname = parsed.netloc.lower()
        hostname = hostname.lstrip('www.')
        parts = hostname.split('.')
        neutral = {"co", "com", "org", "net", "gov", "edu"}
        candidate = parts[-2] if len(parts) >= 2 else parts[0]
        if candidate in neutral and len(parts) >= 3:
            candidate = parts[-3]
        cleaned = candidate.replace('-', ' ').replace('_', ' ').strip()
        return cleaned.title() if cleaned else hostname or "Source"
    except Exception:
        return "Source"


def _format_display_url(url: str) -> str:
    """
    Shorten a URL for display purposes.
    """
    if not url:
        return ""
    try:
        parsed = urlparse(url)
        display = f"{parsed.netloc}{parsed.path or ''}"
        if parsed.query:
            display += f"?{parsed.query}"
        display = display.lstrip('www.')
        if len(display) > 80:
            display = f"{display[:77]}..."
        return display or url
    except Exception:
        return url


def format_sources_for_frontend(
    source_entries: Iterable[Dict[str, Any]],
    current_url: Optional[str] = None
) -> Dict[str, Any]:
    """
    Prepare structured source metadata for the frontend.

    Args:
        source_entries: Iterable of citation metadata dicts.
        current_url: The user's active page URL.

    Returns:
        Dict with `current_page` metadata (if available) and ordered `sources` list.
    """
    entries = []
    seen: set[str] = set()
    current_entry: Optional[Dict[str, Any]] = None

    for raw_entry in source_entries or []:
        url = raw_entry.get("url")
        if not url or url in seen:
            continue
        seen.add(url)
        normalized = {
            "url": url,
            "title": raw_entry.get("title") or "",
            "snippet": raw_entry.get("snippet") or "",
            "image": raw_entry.get("image") or None,
        }
        normalized["site_name"] = raw_entry.get("site_name") or _get_site_name(url)
        normalized["display_url"] = raw_entry.get("display_url") or _format_display_url(url)
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
            "image": None,
        }

    combined_entries: list[Dict[str, Any]] = []
    if current_entry:
        combined_entries.append(current_entry)
    combined_entries.extend(entries)

    for entry in combined_entries:
        if not entry.get("url"):
            continue
        snippet = _normalize_preview_text(entry.get("snippet"))
        if snippet:
            entry["snippet"] = _truncate_preview(snippet, 160)
            continue
        fetched_preview = _fetch_preview_from_url(entry["url"], max_chars=160)
        entry["snippet"] = fetched_preview or ""

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
    # As of late 2024, web search is specifically available for:
    supported_models = [
        "gpt-4o",
        "gpt-4o-mini",
        "gpt-4o-2024-11-20",
        "gpt-5-mini",  # GPT-5 models should support it
        "gpt-5-nano",  # FinGPT-Light uses this
        "gpt-5-chat",  # FinGPT uses this
        # Note: o1 models may have limited tool support
        # Check OpenAI docs for latest model support
    ]

    # Check if the model or its base version is supported
    model_lower = model.lower()
    for supported in supported_models:
        if supported in model_lower:
            logger.debug(f"Model '{model}' supports Responses API with web search")
            return True

    # Log when model doesn't support Responses API
    logger.info(f"Model '{model}' does not support Responses API with web search - will use fallback")
    return False


# Optional: Test function for development
async def _test_responses_api():
    """Test function to verify Responses API integration."""
    test_query = "What are the latest developments in renewable energy this week?"
    test_history = []

    try:
        response, sources = await create_responses_api_search_async(
            test_query,
            test_history,
            model="gpt-4o-mini"
        )

        print(f"Response: {response[:200]}...")
        print(f"Sources found: {len(sources)}")
        for idx, url in enumerate(sources, 1):
            print(f"  {idx}. {url}")

        return True
    except Exception as e:
        print(f"Test failed: {e}")
        return False


if __name__ == "__main__":
    # Run test when module is executed directly
    import asyncio
    asyncio.run(_test_responses_api())
