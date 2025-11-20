"""
API Views for FinGPT Search Agent - Unified Context Manager Integration
Integrates the new UnifiedContextManager while maintaining complete backward compatibility

SECURITY NOTE: CSRF Protection
-------------------------------
Most endpoints use @csrf_exempt because this backend serves a browser extension frontend.
Browser extensions cannot easily include CSRF tokens in their requests.

Security is provided through:
1. CORS_ALLOWED_ORIGINS restricting which origins can make requests
2. SESSION_COOKIE_SAMESITE='None' with SESSION_COOKIE_SECURE=True (in production)
3. Session-based authentication via Django sessions
"""

import json
import os
import csv
import asyncio
import logging
import re
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.cache import cache_page
from django.http import JsonResponse, StreamingHttpResponse, HttpRequest
from django.conf import settings

# Legacy imports (kept for compatibility)
from datascraper import datascraper as ds
from datascraper.preferred_links_manager import get_manager
from datascraper.models_config import MODELS_CONFIG

# Unified context manager imports (clean version - no legacy support)
from datascraper.unified_context_manager import (
    UnifiedContextManager,
    ContextMode,
    get_context_manager
)
from datascraper.context_integration import (
    ContextIntegration,
    get_context_integration
)

# Configure logging
logger = logging.getLogger(__name__)

# Constants
QUESTION_LOG_PATH = os.path.join(os.path.dirname(__file__), 'questionLog.csv')

# ============================================================================
# Helper Functions
# ============================================================================

def _get_version():
    """Dynamically fetch version from pyproject.toml"""
    try:
        pyproject_path = Path(__file__).resolve().parent.parent / 'pyproject.toml'
        with open(pyproject_path, 'r', encoding='utf-8') as f:
            content = f.read()
            match = re.search(r'^version\s*=\s*["\']([^"\']+)["\']', content, re.MULTILINE)
            if match:
                return match.group(1)
    except Exception:
        pass
    return 'unknown'


def _int_env(name: str, default: int) -> int:
    """Safely parse integer environment variables."""
    try:
        return int(os.getenv(name, default))
    except (TypeError, ValueError):
        return default


def _get_session_id(request: HttpRequest) -> str:
    """Get or create session ID for context management."""
    # Try custom session ID from frontend
    custom_session_id = request.GET.get('session_id')

    # For POST requests, check body data
    if not custom_session_id and request.method == 'POST':
        try:
            body_data = json.loads(request.body)
            custom_session_id = body_data.get('session_id')
        except:
            pass

    if custom_session_id:
        return custom_session_id

    # Use Django session
    if not request.session.session_key:
        request.session.create()

    return request.session.session_key


def _build_status_frame(label: str, detail: Optional[str] = None, url: Optional[str] = None) -> bytes:
    """Create an SSE frame containing only status data."""
    status_payload = {"status": {"label": label}}
    if detail:
        status_payload["status"]["detail"] = detail
    if url:
        status_payload["status"]["url"] = url
    return f'data: {json.dumps(status_payload)}\n\n'.encode('utf-8')


def _ensure_log_file_exists():
    """Create log file with headers if it doesn't exist, using UTF-8 encoding."""
    if not os.path.isfile(QUESTION_LOG_PATH):
        with open(QUESTION_LOG_PATH, 'w', newline='', encoding='utf-8') as log_file:
            writer = csv.writer(log_file)
            writer.writerow(['Button', 'URL', 'Question', 'Date', 'Time', 'Response_Preview'])


def _log_interaction(button_clicked: str, current_url: str, question: str, response: Optional[str] = None):
    """
    Log interaction details with timestamp and response preview.
    Uses UTF-8 with `errors="replace"`
    """
    _ensure_log_file_exists()

    now = datetime.now()
    date_str = now.strftime('%Y-%m-%d')
    time_str = now.strftime('%H:%M:%S')

    # Handles invalid chars
    def safe_str(s):
        return str(s).encode('utf-8', errors='replace').decode('utf-8')

    # Only record first 80 chars of the response
    response_preview = response[:80] if response else "N/A"

    # Clean each field before writing
    button_clicked = safe_str(button_clicked)
    current_url = safe_str(current_url)
    question = safe_str(question)
    response_preview = safe_str(response_preview)

    try:
        with open(QUESTION_LOG_PATH, 'a', newline='', encoding='utf-8', errors='replace') as log_file:
            writer = csv.writer(log_file)
            writer.writerow([button_clicked, current_url, question, date_str, time_str, response_preview])
    except Exception as e:
        logger.error(f"Failed to log interaction: {e}")


# ============================================================================
# Core Chat Endpoints with Unified Context Manager
# ============================================================================

@csrf_exempt
def chat_response(request: HttpRequest) -> JsonResponse:
    """
    Normal Mode: Help user understand the CURRENT website using Playwright navigation.
    Agent stays within the current domain and navigates to find information.
    Now uses Unified Context Manager for full conversation history.
    """
    try:
        question = request.GET.get('question', '')
        selected_models = request.GET.get('models', 'gpt-4o-mini')
        current_url = request.GET.get('current_url', '')
        use_unified = request.GET.get('use_unified', 'true').lower() == 'true'

        if not question:
            return JsonResponse({'error': 'No question provided'}, status=400)

        # Extract domain from current URL for restriction
        restricted_domain = None
        if current_url:
            parsed = urlparse(current_url)
            restricted_domain = parsed.netloc

        logger.info(f"Chat request: question='{question[:50]}...', domain={restricted_domain}")

        # Get session ID
        session_id = _get_session_id(request)

        # Initialize context integration
        integration = get_context_integration()
        context_mgr = get_context_manager()

        # Update metadata
        context_mgr.update_metadata(
            session_id=session_id,
            mode=ContextMode.THINKING,
            current_url=current_url,
            user_timezone=request.GET.get('user_timezone'),
            user_time=request.GET.get('user_time')
        )

        # Add user message to context
        context_mgr.add_user_message(session_id, question)

        # Get formatted messages for API
        messages = context_mgr.get_formatted_messages_for_api(session_id)

        # Process each model
        models = [m.strip() for m in selected_models.split(',') if m.strip()]
        responses = {}

        for model in models:
            try:
                import time
                start_time = time.time()

                # Use agent with Playwright for domain navigation
                response = ds.create_agent_response(
                    user_input=question,
                    message_list=messages,
                    model=model,
                    use_playwright=True,
                    restricted_domain=restricted_domain,
                    current_url=current_url,
            auto_fetch_page=True
                )

                responses[model] = response
                # Persist Playwright scraped context, if any
                for entry in ds.get_last_playwright_context() or []:
                    integration.add_playwright_content(
                        session_id=session_id,
                        content=entry.get("content", ""),
                        url=entry.get("url") or current_url,
                        action=entry.get("action")
                    )

                # Add response to context
                response_time_ms = int((time.time() - start_time) * 1000)
                context_mgr.add_assistant_message(
                    session_id=session_id,
                    content=response,
                    model=model,
                    tools_used=["playwright"] if restricted_domain else [],
                    response_time_ms=response_time_ms
                )

            except Exception as e:
                logger.error(f"Error with model {model}: {e}", exc_info=True)
                responses[model] = f"Error: {str(e)}"

        # Get context statistics
        stats = context_mgr.get_session_stats(session_id)

        # Log interaction
        first_response = next(iter(responses.values()), "No response")
        _log_interaction("normal_chat", current_url, question, first_response)

        # Build response
        result = {
            'resp': responses,
            'context_stats': {
                'session_id': session_id,
                'mode': stats['mode'],
                'message_count': stats['message_count'],
                'token_count': stats['token_count'],
                'fetched_context': stats['fetched_context_counts']
            }
        }

        return JsonResponse(result)

    except Exception as e:
        logger.error(f"Chat response error: {e}", exc_info=True)
        return JsonResponse({'error': str(e)}, status=500)


@csrf_exempt
def adv_response(request: HttpRequest) -> JsonResponse:
    """
    Extensive Mode: Search for information ANYWHERE on the web using web_search.
    Uses OpenAI Responses API with built-in web_search tool (no domain restrictions).
    Now uses Unified Context Manager for full conversation history.
    """
    try:
        question = request.GET.get('question', '')
        selected_models = request.GET.get('models', 'gpt-4o-mini')
        preferred_links_json = request.GET.get('preferred_links', '')
        current_url = request.GET.get('current_url', '')

        if not question:
            return JsonResponse({'error': 'No question provided'}, status=400)

        # Parse preferred links
        preferred_links = []
        if preferred_links_json:
            try:
                preferred_links = json.loads(preferred_links_json)
                logger.info(f"Received {len(preferred_links)} preferred links")
            except json.JSONDecodeError:
                logger.error(f"Failed to parse preferred links JSON")

        # Get session ID
        session_id = _get_session_id(request)

        # Initialize context
        integration = get_context_integration()
        context_mgr = get_context_manager()

        # Update metadata for RESEARCH mode
        context_mgr.update_metadata(
            session_id=session_id,
            mode=ContextMode.RESEARCH,
            current_url=current_url,
            user_timezone=request.GET.get('user_timezone'),
            user_time=request.GET.get('user_time')
        )

        # Add user message
        context_mgr.add_user_message(session_id, question)

        # Get formatted messages
        messages = context_mgr.get_formatted_messages_for_api(session_id)

        # Process each model
        models = [m.strip() for m in selected_models.split(',') if m.strip()]
        responses = {}
        all_sources = []

        for model in models:
            try:
                import time
                start_time = time.time()

                # Create advanced response with web search
                response, sources = ds.create_advanced_response(
                    user_input=question,
                    message_list=messages,
                    model=model,
                    preferred_links=preferred_links,
                    stream=False,
                    user_timezone=request.GET.get('user_timezone'),
                    user_time=request.GET.get('user_time')
                )

                responses[model] = response
                all_sources.extend(sources)

                # Add search results to context
                if sources:
                    integration.add_search_results(session_id, sources)

                # Add response to context
                response_time_ms = int((time.time() - start_time) * 1000)
                context_mgr.add_assistant_message(
                    session_id=session_id,
                    content=response,
                    model=model,
                    sources_used=sources,
                    tools_used=["web_search"],
                    response_time_ms=response_time_ms
                )

            except Exception as e:
                logger.error(f"Error with model {model}: {e}", exc_info=True)
                responses[model] = f"Error: {str(e)}"

        # Get context statistics
        stats = context_mgr.get_session_stats(session_id)

        # Log interaction
        first_response = next(iter(responses.values()), "No response")
        _log_interaction("advanced_search", current_url, question, first_response)

        # Build response
        result = {
            'resp': responses,
            'used_sources': all_sources,
            'context_stats': {
                'session_id': session_id,
                'mode': stats['mode'],
                'message_count': stats['message_count'],
                'token_count': stats['token_count'],
                'fetched_context': stats['fetched_context_counts']
            }
        }

        return JsonResponse(result)

    except Exception as e:
        logger.error(f"Advanced response error: {e}", exc_info=True)
        return JsonResponse({'error': str(e)}, status=500)


@csrf_exempt
def agent_chat_response(request: HttpRequest) -> JsonResponse:
    """
    Process chat response via Agent with optional tools (Playwright, etc.)
    Now uses Unified Context Manager for full conversation history.
    """
    try:
        question = request.GET.get('question', '')
        selected_models = request.GET.get('models', 'gpt-4o-mini')
        current_url = request.GET.get('current_url', '')
        use_playwright = request.GET.get('use_playwright', 'false').lower() == 'true'

        if not question:
            return JsonResponse({'error': 'No question provided'}, status=400)

        # Get session ID
        session_id = _get_session_id(request)

        # Initialize context
        integration = get_context_integration()
        context_mgr = get_context_manager()

        # Update metadata for THINKING mode
        context_mgr.update_metadata(
            session_id=session_id,
            mode=ContextMode.THINKING,
            current_url=current_url,
            user_timezone=request.GET.get('user_timezone'),
            user_time=request.GET.get('user_time')
        )

        # Add user message
        context_mgr.add_user_message(session_id, question)

        # Get formatted messages
        messages = context_mgr.get_formatted_messages_for_api(session_id)

        # Process each model
        models = [m.strip() for m in selected_models.split(',') if m.strip()]
        responses = {}

        for model in models:
            try:
                import time
                start_time = time.time()

                # Create agent response
                response = ds.create_agent_response(
                    user_input=question,
                    message_list=messages,
                    model=model,
                    use_playwright=use_playwright,
                    restricted_domain=None,  # No restriction in agent mode
                    current_url=current_url,
                    auto_fetch_page=True
                )

                responses[model] = response
                # Persist Playwright scraped context, if any
                for entry in ds.get_last_playwright_context() or []:
                    integration.add_playwright_content(
                        session_id=session_id,
                        content=entry.get("content", ""),
                        url=entry.get("url") or current_url,
                        action=entry.get("action")
                    )

                # Add response to context
                response_time_ms = int((time.time() - start_time) * 1000)
                tools_used = ["playwright"] if use_playwright else []
                context_mgr.add_assistant_message(
                    session_id=session_id,
                    content=response,
                    model=model,
                    tools_used=tools_used,
                    response_time_ms=response_time_ms
                )

            except Exception as e:
                logger.error(f"Error with model {model}: {e}", exc_info=True)
                responses[model] = f"Error: {str(e)}"

        # Get context statistics
        stats = context_mgr.get_session_stats(session_id)

        # Log interaction
        first_response = next(iter(responses.values()), "No response")
        _log_interaction("agent_chat", current_url, question, first_response)

        # Build response
        result = {
            'resp': responses,
            'context_stats': {
                'session_id': session_id,
                'mode': stats['mode'],
                'message_count': stats['message_count'],
                'token_count': stats['token_count'],
                'fetched_context': stats['fetched_context_counts']
            }
        }

        return JsonResponse(result)

    except Exception as e:
        logger.error(f"Agent response error: {e}", exc_info=True)
        return JsonResponse({'error': str(e)}, status=500)


# ============================================================================
# Streaming Endpoints
# ============================================================================

@csrf_exempt
def chat_response_stream(request: HttpRequest) -> StreamingHttpResponse:
    """
    Normal Mode Streaming: Help user understand the CURRENT website using Playwright navigation.
    Agent stays within the current domain and navigates to find information.
    """
    try:
        question = request.GET.get('question', '')
        selected_models = request.GET.get('models', 'gpt-4o-mini')
        current_url = request.GET.get('current_url', '')

        if not question:
            return JsonResponse({'error': 'No question provided'}, status=400)

        # Extract domain
        restricted_domain = None
        if current_url:
            parsed = urlparse(current_url)
            restricted_domain = parsed.netloc

        # Get session ID
        session_id = _get_session_id(request)

        user_timezone = request.GET.get('user_timezone')
        user_time = request.GET.get('user_time')

        # Initialize context
        context_mgr = get_context_manager()
        integration = get_context_integration()
        context_mgr.update_metadata(
            session_id=session_id,
            mode=ContextMode.THINKING,
            current_url=current_url,
            user_timezone=user_timezone,
            user_time=user_time
        )

        # Add user message
        context_mgr.add_user_message(session_id, question)

        # Get messages
        messages = context_mgr.get_formatted_messages_for_api(session_id)

        model = selected_models.split(',')[0].strip()

        def event_stream():
            """Generator for SSE streaming"""
            try:
                # Send initial connection
                yield b'event: connected\ndata: {"status": "connected"}\n\n'
                yield _build_status_frame("Preparing context")

                if restricted_domain:
                    yield _build_status_frame("Navigating site", restricted_domain)

                import time
                start_time = time.time()
                aggregated_chunks: List[str] = []

                stream_generator, stream_state = ds.create_agent_response_stream(
                    user_input=question,
                    message_list=messages,
                    model=model,
                    use_playwright=True,
                    restricted_domain=restricted_domain,
                    current_url=current_url,
                    auto_fetch_page=True,
                    user_timezone=user_timezone,
                    user_time=user_time
                )

                previous_loop = None
                try:
                    previous_loop = asyncio.get_event_loop()
                except RuntimeError:
                    previous_loop = None

                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                stream_iter = stream_generator.__aiter__()
                drafting_sent = False

                try:
                    while True:
                        chunk = loop.run_until_complete(stream_iter.__anext__())
                        if not chunk:
                            continue

                        aggregated_chunks.append(chunk)
                        if not drafting_sent:
                            drafting_sent = True
                            yield _build_status_frame("Drafting answer")

                        yield f'data: {json.dumps({"content": chunk, "done": False})}\n\n'.encode('utf-8')
                except StopAsyncIteration:
                    pass
                finally:
                    loop.close()
                    if previous_loop is not None:
                        asyncio.set_event_loop(previous_loop)
                    else:
                        asyncio.set_event_loop(None)

                final_response = ""
                if stream_state:
                    final_response = stream_state.get("final_output") or ""
                if not final_response and aggregated_chunks:
                    final_response = "".join(aggregated_chunks)

                # Persist Playwright scraped context, if any
                for entry in ds.get_last_playwright_context() or []:
                    integration.add_playwright_content(
                        session_id=session_id,
                        content=entry.get("content", ""),
                        url=entry.get("url") or current_url,
                        action=entry.get("action")
                    )

                # Add to context
                response_time_ms = int((time.time() - start_time) * 1000)
                context_mgr.add_assistant_message(
                    session_id=session_id,
                    content=final_response,
                    model=model,
                    tools_used=["playwright"] if restricted_domain else [],
                    response_time_ms=response_time_ms
                )

                # Get stats
                stats = context_mgr.get_session_stats(session_id)

                # Send completion
                yield _build_status_frame("Finalizing response")
                final_data = {
                    "content": "",
                    "done": True,
                    "context_stats": {
                        'session_id': session_id,
                        'message_count': stats['message_count'],
                        'token_count': stats['token_count'],
                        'response_time_ms': response_time_ms
                    }
                }
                yield f'data: {json.dumps(final_data)}\n\n'.encode('utf-8')

                # Log interaction
                _log_interaction("normal_stream", current_url, question, final_response)

            except Exception as e:
                logger.error(f"Streaming error: {e}", exc_info=True)
                yield f'data: {json.dumps({"error": str(e), "done": True})}\n\n'.encode('utf-8')

        response = StreamingHttpResponse(
            event_stream(),
            content_type='text/event-stream'
        )
        response['Cache-Control'] = 'no-cache'
        response['X-Accel-Buffering'] = 'no'

        return response

    except Exception as e:
        logger.error(f"Stream error: {e}", exc_info=True)
        return JsonResponse({'error': str(e)}, status=500)


@csrf_exempt
def adv_response_stream(request: HttpRequest) -> StreamingHttpResponse:
    """Process streaming advanced chat response from selected models using SSE"""
    try:
        question = request.GET.get('question', '')
        selected_models = request.GET.get('models', 'gpt-4o-mini')
        current_url = request.GET.get('current_url', '')
        preferred_links_json = request.GET.get('preferred_links', '')

        # Parse preferred links
        preferred_links = []
        if preferred_links_json:
            try:
                preferred_links = json.loads(preferred_links_json)
                logger.info(f"Received {len(preferred_links)} preferred links for streaming")
            except json.JSONDecodeError:
                logger.error(f"Failed to parse preferred links JSON")

        if not question:
            return JsonResponse({'error': 'No question provided'}, status=400)

        # Get session ID
        session_id = _get_session_id(request)

        # Initialize context
        integration = get_context_integration()
        context_mgr = get_context_manager()
        context_mgr.update_metadata(
            session_id=session_id,
            mode=ContextMode.RESEARCH,
            current_url=current_url,
            user_timezone=request.GET.get('user_timezone'),
            user_time=request.GET.get('user_time')
        )

        # Add user message
        context_mgr.add_user_message(session_id, question)

        # Get messages
        messages = context_mgr.get_formatted_messages_for_api(session_id)

        model = selected_models.split(',')[0].strip()

        def event_stream():
            """Generator for SSE streaming"""
            try:
                # Send initial connection
                yield b'event: connected\ndata: {"status": "connected"}\n\n'
                yield _build_status_frame("Preparing context", "Research mode")
                yield _build_status_frame("Searching the web")

                import time
                start_time = time.time()
                full_response = ""
                source_entries = []

                # Use streaming advanced response
                stream_generator, stream_state = ds.create_advanced_response_streaming(
                    question,
                    messages,
                    model,
                    preferred_links,
                    user_timezone=request.GET.get('user_timezone'),
                    user_time=request.GET.get('user_time')
                )

                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                stream_iter = stream_generator.__aiter__()
                drafting_sent = False

                while True:
                    try:
                        text_chunk, entries = loop.run_until_complete(stream_iter.__anext__())
                    except StopAsyncIteration:
                        break

                    if text_chunk:
                        full_response += text_chunk
                        if not drafting_sent:
                            drafting_sent = True
                            yield _build_status_frame("Drafting answer")
                        yield f'data: {json.dumps({"content": text_chunk, "done": False})}\n\n'.encode('utf-8')

                    if entries:
                        source_entries = [dict(entry) for entry in entries if entry]

                loop.close()

                # Add search results to context
                if source_entries:
                    integration.add_search_results(session_id, source_entries)

                # Add response to context
                response_time_ms = int((time.time() - start_time) * 1000)
                context_mgr.add_assistant_message(
                    session_id=session_id,
                    content=full_response,
                    model=model,
                    sources_used=source_entries,
                    tools_used=["web_search"],
                    response_time_ms=response_time_ms
                )

                # Get stats
                stats = context_mgr.get_session_stats(session_id)

                # Send completion
                yield _build_status_frame("Finalizing response")
                final_data = {
                    "content": "",
                    "done": True,
                    "used_sources": source_entries,
                    "context_stats": {
                        'session_id': session_id,
                        'message_count': stats['message_count'],
                        'token_count': stats['token_count'],
                        'response_time_ms': response_time_ms
                    }
                }
                yield f'data: {json.dumps(final_data)}\n\n'.encode('utf-8')

                # Log interaction
                _log_interaction("advanced_stream", current_url, question, full_response)

            except Exception as e:
                logger.error(f"Advanced streaming error: {e}", exc_info=True)
                yield f'data: {json.dumps({"error": str(e), "done": True})}\n\n'.encode('utf-8')

        response = StreamingHttpResponse(
            event_stream(),
            content_type='text/event-stream'
        )
        response['Cache-Control'] = 'no-cache'
        response['X-Accel-Buffering'] = 'no'

        return response

    except Exception as e:
        logger.error(f"Advanced stream error: {e}", exc_info=True)
        return JsonResponse({'error': str(e)}, status=500)


# ============================================================================
# Context Management Endpoints
# ============================================================================

@csrf_exempt
def add_webtext(request: HttpRequest) -> JsonResponse:
    """
    Handle appending the site's text to the message list.
    Now uses Unified Context Manager for JS scraped content.
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'Invalid request method; use POST.'}, status=405)

    try:
        data = json.loads(request.body) if request.body else {}
        text_content = data.get('textContent', '')
        current_url = data.get('currentUrl', '')

        if not text_content:
            return JsonResponse({'error': 'No text content provided'}, status=400)

        logger.info(f"Receiving web content from {current_url}, length={len(text_content)}")

        # Get session ID
        session_id = _get_session_id(request)

        # Initialize context
        integration = get_context_integration()

        # Add to context (truncate if too long)
        MAX_CONTENT_LENGTH = 10000
        if len(text_content) > MAX_CONTENT_LENGTH:
            text_content = text_content[:MAX_CONTENT_LENGTH] + "... (truncated)"

        # Add to context
        integration.add_web_content(
            request=request,
            text_content=text_content,
            current_url=current_url,
            source_type="js_scraping"
        )

        # Get updated stats
        stats = integration.get_context_stats(session_id)

        # Log interaction
        _log_interaction("web_content", current_url, "Web content received", None)

        return JsonResponse({
            'status': 'success',
            'session_id': session_id,
            'context_stats': {
                'message_count': stats['message_count'],
                'token_count': stats['token_count'],
                'js_scraping_count': stats['fetched_context_counts'].get('js_scraping', 0)
            }
        })

    except Exception as e:
        logger.error(f"Input webtext error: {e}", exc_info=True)
        return JsonResponse({'error': str(e)}, status=500)


@csrf_exempt
def clear(request: HttpRequest) -> JsonResponse:
    """
    Clear conversation messages and optionally preserve scraped web content.
    Now uses Unified Context Manager.
    """
    try:
        preserve_web = request.GET.get('preserve_web', 'false').lower() == 'true'

        logger.info(f"Clearing messages, preserve_web={preserve_web}")

        # Get session ID
        session_id = _get_session_id(request)

        # Initialize context
        integration = get_context_integration()

        # Clear based on preference
        integration.clear_messages(request, preserve_web_content=preserve_web)

        # Log interaction
        _log_interaction("clear", "N/A", "Cleared messages", None)

        return JsonResponse({
            'status': 'success',
            'session_id': session_id,
            'preserved_web_content': preserve_web
        })

    except Exception as e:
        logger.error(f"Clear messages error: {e}", exc_info=True)
        return JsonResponse({'error': str(e)}, status=500)


@csrf_exempt
def get_memory_stats(request: HttpRequest) -> JsonResponse:
    """
    Get context statistics for current session.
    Now uses Unified Context Manager.
    """
    try:
        session_id = _get_session_id(request)

        # Initialize context
        integration = get_context_integration()

        # Get stats
        stats = integration.get_context_stats(session_id)

        return JsonResponse({
            'stats': {
                'session_id': session_id,
                'mode': stats['mode'],
                'message_count': stats['message_count'],
                'token_count': stats['token_count'],
                'fetched_context_counts': stats['fetched_context_counts'],
                'total_fetched_items': stats['total_fetched_items'],
                'current_url': stats.get('current_url'),
                'last_updated': stats.get('last_updated'),
                'using_unified_context': True
            }
        })

    except Exception as e:
        logger.error(f"Get stats error: {e}", exc_info=True)
        return JsonResponse({'stats': {"error": str(e), "using_unified_context": False}}, status=500)


# init_page_context endpoint removed - agent decides when to scrape based on query


# ============================================================================
# Utility Endpoints (Legacy Compatibility)
# ============================================================================

def health(request: HttpRequest) -> JsonResponse:
    """
    Health check endpoint for load balancers and monitoring.
    Returns 200 OK if the service is running.
    """
    return JsonResponse({
        'status': 'healthy',
        'service': 'fingpt-backend',
        'timestamp': datetime.now().isoformat(),
        'version': _get_version(),
        'using_unified_context': True
    })


@csrf_exempt
def get_sources(request: HttpRequest) -> JsonResponse:
    """Get sources for a query"""
    query = request.GET.get('query', '')
    current_url = request.GET.get('current_url')
    sources = ds.get_sources(query, current_url=current_url)

    # Log the source request
    _log_interaction("sources", current_url or 'N/A', f"Source request: {query}", None)

    return JsonResponse({'resp': sources})


def log_question(request: HttpRequest) -> JsonResponse:
    """Legacy question logging (redirects to enhanced logging)"""
    question = request.GET.get('question', '')
    button_clicked = request.GET.get('button', '')
    current_url = request.GET.get('current_url', '')

    if question and button_clicked and current_url:
        _log_interaction(button_clicked, current_url, question, None)

    return JsonResponse({'status': 'success'})


def get_preferred_urls(request: HttpRequest) -> JsonResponse:
    """Retrieve preferred URLs from storage"""
    manager = get_manager()
    urls = manager.get_links()
    return JsonResponse({'urls': urls})


@csrf_exempt
def add_preferred_url(request: HttpRequest) -> JsonResponse:
    """Add new preferred URL to storage"""
    if request.method == 'POST':
        try:
            # Try to get URL from POST data or JSON body
            new_url = request.POST.get('url')
            if not new_url and request.body:
                data = json.loads(request.body)
                new_url = data.get('url')

            if new_url:
                manager = get_manager()
                success = manager.add_link(new_url)

                if success:
                    # Log the action
                    _log_interaction("add_url", new_url, f"Added preferred URL: {new_url}", None)
                    return JsonResponse({'status': 'success'})
                else:
                    return JsonResponse({'status': 'exists'})
        except Exception as e:
            logger.error(f"Error adding preferred URL: {e}")
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

    return JsonResponse({'status': 'failed'}, status=400)


@csrf_exempt
def sync_preferred_urls(request: HttpRequest) -> JsonResponse:
    """Sync preferred URLs from frontend to backend storage"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            urls = data.get('urls', [])

            manager = get_manager()
            manager.set_links(urls)

            return JsonResponse({'status': 'success', 'synced': len(urls)})
        except Exception as e:
            logger.error(f"Error syncing preferred URLs: {e}")
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

    return JsonResponse({'status': 'failed'}, status=400)


def get_available_models(request: HttpRequest) -> JsonResponse:
    """Get list of available models with their configurations"""
    models = []
    for model_id, config in MODELS_CONFIG.items():
        models.append({
            'id': model_id,
            'provider': config['provider'],
            'description': config['description'],
            'supports_mcp': config['supports_mcp'],
            'supports_advanced': config['supports_advanced'],
            'display_name': f"{model_id} - {config['description']}"
        })
    return JsonResponse({'models': models})
