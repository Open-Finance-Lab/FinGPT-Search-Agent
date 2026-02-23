"""
OpenAI-compatible API views for FinGPT.
Stateless adapter for the stateful UnifiedContextManager.

Provides /v1/models and /v1/chat/completions endpoints with:
- Bearer token authentication
- Research mode with domain scoping and source return
- Thinking mode with MCP tool source tracking
- Streaming with proper status events and source delivery
"""

import json
import os
import time
import uuid
import logging
import asyncio
from typing import List, Dict, Any, Optional

from django.http import JsonResponse, StreamingHttpResponse, HttpRequest
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings

from datascraper import datascraper as ds
from datascraper.url_tools import _scrape_url_impl as scrape_url
from datascraper.models_config import MODELS_CONFIG
from datascraper.unified_context_manager import (
    UnifiedContextManager,
    ContextMode,
    get_context_manager
)
from datascraper.context_integration import (
    ContextIntegration,
    get_context_integration
)

logger = logging.getLogger(__name__)

# Valid mode strings for the API
_VALID_MODES = {'thinking', 'research', 'normal'}


def _safe_error_message(exception: Exception, context: str = "") -> str:
    """
    Return a safe error message for client responses.
    NEVER returns exception details to prevent information disclosure.
    Full error details are logged server-side for debugging.
    """
    logger.error(f"Error in {context}: {type(exception).__name__}: {str(exception)}", exc_info=True)
    return "An error occurred while processing your request. Please check server logs for details."


def _get_api_session_id(request: HttpRequest, user_id: Optional[str] = None) -> str:
    """
    Get a session ID.
    If user_id is provided, use it for potential continuity.
    If no user_id, generate a random one for this request.
    """
    if user_id:
        return f"api_user_{user_id}"
    return f"api_req_{uuid.uuid4().hex}"


def _authenticate_request(request: HttpRequest) -> Optional[JsonResponse]:
    """
    Validate Bearer token authentication for API requests.
    Returns None if authenticated, or a JsonResponse error if not.

    The API key is configured via the FINGPT_API_KEY environment variable.
    If FINGPT_API_KEY is not set, authentication is disabled (development mode).
    """
    api_key = os.getenv('FINGPT_API_KEY')
    if not api_key:
        # No API key configured — authentication disabled (dev mode)
        return None

    auth_header = request.META.get('HTTP_AUTHORIZATION', '')
    if not auth_header:
        return JsonResponse(
            {'error': {'message': 'Missing Authorization header. Use: Authorization: Bearer <api_key>', 'type': 'authentication_error'}},
            status=401
        )

    if not auth_header.startswith('Bearer '):
        return JsonResponse(
            {'error': {'message': 'Invalid Authorization format. Use: Authorization: Bearer <api_key>', 'type': 'authentication_error'}},
            status=401
        )

    provided_key = auth_header[7:]  # Strip 'Bearer '
    if provided_key != api_key:
        return JsonResponse(
            {'error': {'message': 'Invalid API key', 'type': 'authentication_error'}},
            status=401
        )

    return None


def _merge_domains_into_preferred_links(
    preferred_links: List[str],
    search_domains: Optional[List[str]]
) -> List[str]:
    """
    Merge search_domains into the preferred_links list.
    Domains are normalized to URL format (e.g., 'reuters.com' -> 'https://reuters.com').
    """
    if not search_domains:
        return preferred_links

    merged = list(preferred_links)
    for domain in search_domains:
        domain = domain.strip()
        if not domain:
            continue
        # Normalize bare domains to URLs
        if not domain.startswith('http://') and not domain.startswith('https://'):
            domain = f"https://{domain}"
        if domain not in merged:
            merged.append(domain)
    return merged


@csrf_exempt
def models_list(request: HttpRequest) -> JsonResponse:
    """
    List available models in OpenAI format.
    GET /v1/models
    """
    auth_error = _authenticate_request(request)
    if auth_error:
        return auth_error

    if request.method != 'GET':
        return JsonResponse({'error': 'Method not allowed'}, status=405)

    data = []
    for model_id, config in MODELS_CONFIG.items():
        data.append({
            "id": model_id,
            "object": "model",
            "created": int(time.time()),
            "owned_by": config.get("provider", "fingpt"),
            "permission": [],
            "root": model_id,
            "parent": None,
        })

    return JsonResponse({
        "object": "list",
        "data": data
    })


@csrf_exempt
def chat_completions(request: HttpRequest) -> JsonResponse:
    """
    Create chat completion.
    POST /v1/chat/completions

    Stateless adapter:
    1. Authenticates the request via Bearer token.
    2. Accepts 'messages' list with 'mode' (required: 'thinking' or 'research').
    3. Resets/Creates a session context.
    4. Populates context with history.
    5. Generates response using the last user message as prompt.

    Extra parameters beyond OpenAI standard:
    - mode (required): 'thinking' or 'research'
    - url (optional): target URL for page context / site-specific agent behavior
    - search_domains (optional, research mode): list of domains to scope research to
    - preferred_links (optional, research mode): list of preferred URLs for research
    - user_timezone (optional): IANA timezone string
    - user_time (optional): ISO 8601 current time

    Response extensions (in addition to standard OpenAI fields):
    - sources: list of source objects used to generate the response
    """
    auth_error = _authenticate_request(request)
    if auth_error:
        return auth_error

    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)

    try:
        body = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': {'message': 'Invalid JSON body', 'type': 'invalid_request_error'}}, status=400)

    model = body.get('model', 'FinGPT')
    messages = body.get('messages', [])
    stream = body.get('stream', False)
    user_id = body.get('user')

    # Required parameter
    mode_str = body.get('mode')

    # Optional parameters
    target_url = body.get('url')
    user_timezone = body.get('user_timezone')
    user_time = body.get('user_time')
    preferred_links = body.get('preferred_links', [])
    search_domains = body.get('search_domains')

    # --- Validation ---
    if not messages:
        return JsonResponse(
            {'error': {'message': 'messages array is required', 'type': 'invalid_request_error'}},
            status=400
        )

    if not mode_str:
        return JsonResponse(
            {'error': {'message': "mode is required. Valid values: 'thinking', 'research'", 'type': 'invalid_request_error'}},
            status=400
        )

    if mode_str.lower() not in _VALID_MODES:
        return JsonResponse(
            {'error': {'message': f"Invalid mode '{mode_str}'. Valid values: {', '.join(sorted(_VALID_MODES))}", 'type': 'invalid_request_error'}},
            status=400
        )

    if model not in MODELS_CONFIG:
        return JsonResponse(
            {'error': {'message': f"Model '{model}' does not exist. Use GET /v1/models to list available models.", 'type': 'invalid_request_error'}},
            status=404
        )

    # Merge search_domains into preferred_links for research mode
    if search_domains and mode_str.lower() == 'research':
        preferred_links = _merge_domains_into_preferred_links(preferred_links, search_domains)
        logger.info(f"Merged {len(search_domains)} search domains into preferred_links (total: {len(preferred_links)})")

    # --- Session Setup ---
    session_id = _get_api_session_id(request, user_id)
    context_mgr = get_context_manager()
    integration = get_context_integration()

    # Reset Context (Statelessness) — call context_mgr directly since we already have session_id
    context_mgr.clear_session(session_id)
    context_mgr.set_system_prompt(session_id, "You are a helpful financial assistant.")

    # Handle URL initialization (Scraping)
    if target_url:
        try:
            logger.info(f"API initializing with URL: {target_url}")
            scrape_result_json = scrape_url(target_url)
            scrape_result = json.loads(scrape_result_json)

            if "error" not in scrape_result:
                content = scrape_result.get("content", "")
                integration.add_web_content(
                    request=request,
                    text_content=content,
                    current_url=target_url,
                    source_type="js_scraping",
                    session_id=session_id
                )
        except Exception as e:
            logger.error(f"Failed to scrape initial URL {target_url}: {e}")

    # --- Populate Context from messages ---
    history_messages = messages[:-1]
    last_message = messages[-1]

    for msg in history_messages:
        role = msg.get('role')
        content = msg.get('content', '')
        if role == 'system':
            context_mgr.set_system_prompt(session_id, content)
        elif role == 'user':
            context_mgr.add_user_message(session_id, content)
        elif role == 'assistant':
            context_mgr.add_assistant_message(session_id, content, model=model)

    if last_message.get('role') == 'user':
        last_user_content = last_message.get('content', '')
        context_mgr.add_user_message(session_id, last_user_content)
    else:
        last_user_content = ""

    # Determine Context Mode
    mode_lower = mode_str.lower()
    if mode_lower == 'research':
        context_mode = ContextMode.RESEARCH
    elif mode_lower == 'normal':
        context_mode = ContextMode.NORMAL
    else:
        context_mode = ContextMode.THINKING

    # Update metadata
    context_mgr.update_metadata(
        session_id=session_id,
        mode=context_mode,
        current_url=target_url if target_url else "",
        user_timezone=user_timezone,
        user_time=user_time
    )

    formatted_messages = context_mgr.get_formatted_messages_for_api(session_id)

    logger.info(f"API request: mode={mode_lower}, model={model}, session={session_id}, stream={stream}")

    # --- Generate Response ---
    if stream:
        return _handle_streaming(
            context_mgr, integration, session_id,
            last_user_content, formatted_messages,
            model, context_mode, preferred_links
        )
    else:
        return _handle_sync(
            context_mgr, integration, session_id,
            last_user_content, formatted_messages,
            model, context_mode, preferred_links
        )


def _handle_sync(context_mgr, integration, session_id, question, messages, model, mode, preferred_links=None):
    """Handle synchronous (non-streaming) API responses."""
    try:
        start_time = time.time()

        meta = context_mgr.get_session_metadata(session_id)
        current_url = meta.current_url
        sources = []

        if mode == ContextMode.RESEARCH:
            response_content, sources = ds.create_advanced_response(
                user_input=question,
                message_list=messages,
                model=model,
                preferred_links=preferred_links or [],
                user_timezone=meta.user_timezone,
                user_time=meta.user_time
            )
            # Store research sources in context
            if sources:
                integration.add_search_results(session_id, sources)
        else:
            # Thinking mode
            response_content, sources = ds.create_agent_response(
                user_input=question,
                message_list=messages,
                model=model,
                current_url=current_url,
                user_timezone=meta.user_timezone,
                user_time=meta.user_time
            )

        # Record response in context
        response_time_ms = int((time.time() - start_time) * 1000)
        context_mgr.add_assistant_message(
            session_id=session_id,
            content=response_content,
            model=model,
            sources_used=sources if mode == ContextMode.RESEARCH else [],
            tools_used=[s.get('tool_name', '') for s in sources] if mode != ContextMode.RESEARCH else ["web_search"],
            response_time_ms=response_time_ms
        )

        # Format OpenAI-compatible response with source extensions
        completion_id = f"chatcmpl-{uuid.uuid4().hex}"
        created = int(time.time())
        stats = context_mgr.get_session_stats(session_id)

        response_body = {
            "id": completion_id,
            "object": "chat.completion",
            "created": created,
            "model": model,
            "choices": [{
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": response_content
                },
                "finish_reason": "stop"
            }],
            "usage": {
                "prompt_tokens": stats.get('token_count', 0),
                "completion_tokens": len(response_content) // 4,
                "total_tokens": stats.get('token_count', 0) + (len(response_content) // 4)
            },
            # FinGPT extensions — source tracking
            "sources": sources,
        }

        return JsonResponse(response_body)

    except Exception as e:
        return JsonResponse(
            {'error': {'message': _safe_error_message(e, 'API Sync'), 'type': 'server_error'}},
            status=500
        )


def _handle_streaming(context_mgr, integration, session_id, question, messages, model, mode, preferred_links=None):
    """Handle streaming (SSE) API responses with proper source delivery."""

    def event_stream():
        completion_id = f"chatcmpl-{uuid.uuid4().hex}"
        created = int(time.time())

        # Initial chunk (role)
        initial_chunk = {
            "id": completion_id,
            "object": "chat.completion.chunk",
            "created": created,
            "model": model,
            "choices": [{"index": 0, "delta": {"role": "assistant"}, "finish_reason": None}]
        }
        yield f"data: {json.dumps(initial_chunk)}\n\n"

        meta = context_mgr.get_session_metadata(session_id)
        current_url = meta.current_url

        # Save and create event loop (matching UI behavior)
        previous_loop = None
        try:
            previous_loop = asyncio.get_event_loop()
        except RuntimeError:
            previous_loop = None

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            full_content = []
            sources = []

            if mode == ContextMode.RESEARCH:
                yield from _stream_research_mode(
                    loop, completion_id, created, model,
                    question, messages, preferred_links, meta,
                    full_content, sources
                )
            else:
                yield from _stream_thinking_mode(
                    loop, completion_id, created, model,
                    question, messages, current_url, meta,
                    full_content
                )

            # Final chunk with finish_reason and sources
            final_chunk = {
                "id": completion_id,
                "object": "chat.completion.chunk",
                "created": created,
                "model": model,
                "choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}],
                "sources": sources,
            }
            yield f"data: {json.dumps(final_chunk)}\n\n"
            yield "data: [DONE]\n\n"

            # Post-processing: save to context
            final_text = "".join(full_content)
            context_mgr.add_assistant_message(
                session_id, final_text, model=model,
                sources_used=sources if mode == ContextMode.RESEARCH else [],
            )

        except Exception as e:
            err_chunk = {
                "error": {"message": _safe_error_message(e, 'API Stream'), "type": "server_error"}
            }
            yield f"data: {json.dumps(err_chunk)}\n\n"

        finally:
            loop.close()
            if previous_loop is not None:
                asyncio.set_event_loop(previous_loop)
            else:
                asyncio.set_event_loop(None)

    response = StreamingHttpResponse(event_stream(), content_type='text/event-stream')
    response['Cache-Control'] = 'no-cache'
    response['X-Accel-Buffering'] = 'no'
    return response


def _stream_research_mode(loop, completion_id, created, model, question, messages, preferred_links, meta, full_content, sources):
    """
    Generator for research mode streaming.
    Handles status events, content chunks, and source delivery.
    """
    stream_generator, stream_state = ds.create_advanced_response_streaming(
        user_input=question,
        message_list=messages,
        model=model,
        preferred_links=preferred_links or [],
        user_timezone=meta.user_timezone,
        user_time=meta.user_time
    )
    stream_iter = stream_generator.__aiter__()

    while True:
        try:
            chunk_tuple = loop.run_until_complete(stream_iter.__anext__())
            text_chunk, entries = chunk_tuple

            # Status event from research engine (e.g., "Analyzing query", "Searching the web")
            if text_chunk is None and isinstance(entries, dict) and "label" in entries:
                status_chunk = {
                    "id": completion_id,
                    "object": "chat.completion.chunk",
                    "created": created,
                    "model": model,
                    "choices": [{"index": 0, "delta": {}, "finish_reason": None}],
                    "status": {"label": entries["label"], "detail": entries.get("detail")}
                }
                yield f"data: {json.dumps(status_chunk)}\n\n"
                continue

            # Content chunk
            if text_chunk:
                full_content.append(text_chunk)
                resp_chunk = {
                    "id": completion_id,
                    "object": "chat.completion.chunk",
                    "created": created,
                    "model": model,
                    "choices": [{"index": 0, "delta": {"content": text_chunk}, "finish_reason": None}]
                }
                yield f"data: {json.dumps(resp_chunk)}\n\n"

            # Source delivery
            if isinstance(entries, list) and entries:
                sources.clear()
                sources.extend([dict(entry) for entry in entries if entry])

        except StopAsyncIteration:
            break

    # Also check stream_state for sources if not captured from chunks
    if not sources and stream_state:
        state_sources = stream_state.get("used_sources", [])
        if state_sources:
            sources.extend(state_sources)


def _stream_thinking_mode(loop, completion_id, created, model, question, messages, current_url, meta, full_content):
    """
    Generator for thinking mode streaming.
    Streams content chunks from the agent.
    """
    stream_generator, stream_state = ds.create_agent_response_stream(
        user_input=question,
        message_list=messages,
        model=model,
        current_url=current_url,
        user_timezone=meta.user_timezone,
        user_time=meta.user_time
    )
    stream_iter = stream_generator.__aiter__()

    while True:
        try:
            chunk = loop.run_until_complete(stream_iter.__anext__())
            if chunk:
                full_content.append(chunk)
                resp_chunk = {
                    "id": completion_id,
                    "object": "chat.completion.chunk",
                    "created": created,
                    "model": model,
                    "choices": [{"index": 0, "delta": {"content": chunk}, "finish_reason": None}]
                }
                yield f"data: {json.dumps(resp_chunk)}\n\n"
        except StopAsyncIteration:
            break
