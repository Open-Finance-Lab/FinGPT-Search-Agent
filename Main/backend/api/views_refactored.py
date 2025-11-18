"""
Refactored API Views using Unified Context Manager
Demonstrates integration of new context management system
Author: Linus (eliminating complexity through good taste)
"""

import json
import logging
import time
import asyncio
from typing import Dict, List, Optional, Any
from django.http import JsonResponse, HttpRequest, StreamingHttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from datascraper.context_integration import (
    prepare_context_messages,
    add_response_to_context,
    add_web_content,
    clear_messages,
    get_context_stats,
    get_context_integration
)
from datascraper.unified_context_manager import ContextMode
from datascraper.datascraper import (
    create_response,
    create_agent_response,
    create_advanced_response
)

logger = logging.getLogger(__name__)


# ============================================================================
# Core Chat Endpoints
# ============================================================================

@csrf_exempt
@require_http_methods(["GET"])
def chat_response(request: HttpRequest) -> JsonResponse:
    """
    Normal chat mode with domain-restricted Playwright.
    Uses unified context manager for full conversation history.
    """
    try:
        # Extract parameters
        question = request.GET.get('question', '')
        models = request.GET.get('models', 'gpt-4o-mini').split(',')
        current_url = request.GET.get('current_url', '')
        use_unified = request.GET.get('use_unified', 'true').lower() == 'true'

        if not question:
            return JsonResponse({'error': 'No question provided'}, status=400)

        # Extract domain from current URL for restriction
        restricted_domain = None
        if current_url:
            from urllib.parse import urlparse
            parsed = urlparse(current_url)
            restricted_domain = parsed.netloc

        logger.info(f"Chat request: models={models}, domain={restricted_domain}, unified={use_unified}")

        # Prepare context with full conversation history
        messages, session_id = prepare_context_messages(
            request=request,
            question=question,
            use_unified=use_unified,
            current_url=current_url,
            endpoint="chat_response"
        )

        responses = {}
        start_time = time.time()

        # Get response from each model
        for model in models:
            try:
                # Use agent with Playwright for domain navigation
                response = create_agent_response(
                    user_input=question,
                    message_list=messages,
                    model=model,
                    use_playwright=True,
                    restricted_domain=restricted_domain,
                    current_url=current_url
                )

                responses[model] = response

                # Add response to context with metadata
                response_time_ms = int((time.time() - start_time) * 1000)
                add_response_to_context(
                    session_id=session_id,
                    response=response,
                    model=model,
                    tools_used=["playwright"] if restricted_domain else [],
                    response_time_ms=response_time_ms
                )

            except Exception as e:
                logger.error(f"Error with model {model}: {e}")
                responses[model] = f"Error: {str(e)}"

        # Get context statistics
        stats = get_context_stats(session_id)

        # Build response
        result = {
            'resp': responses,
            'context_stats': {
                'session_id': session_id,
                'mode': stats['mode'],
                'message_count': stats['message_count'],
                'token_count': stats['token_count'],
                'fetched_context': stats['fetched_context_counts'],
                'current_url': current_url
            }
        }

        return JsonResponse(result)

    except Exception as e:
        logger.error(f"Chat response error: {e}", exc_info=True)
        return JsonResponse({'error': str(e)}, status=500)


@csrf_exempt
@require_http_methods(["GET"])
def adv_response(request: HttpRequest) -> JsonResponse:
    """
    Advanced mode with web search.
    Uses unified context manager with RESEARCH mode.
    """
    try:
        # Extract parameters
        question = request.GET.get('question', '')
        models = request.GET.get('models', 'gpt-4o-mini').split(',')
        preferred_links = request.GET.get('preferred_links', '[]')
        use_unified = request.GET.get('use_unified', 'true').lower() == 'true'

        if not question:
            return JsonResponse({'error': 'No question provided'}, status=400)

        # Parse preferred links
        try:
            preferred_urls = json.loads(preferred_links) if preferred_links else []
        except json.JSONDecodeError:
            preferred_urls = []

        logger.info(f"Advanced request: models={models}, preferred={len(preferred_urls)}, unified={use_unified}")

        # Prepare context with RESEARCH mode
        messages, session_id = prepare_context_messages(
            request=request,
            question=question,
            use_unified=use_unified,
            endpoint="adv_response"
        )

        # Update mode to RESEARCH
        if use_unified:
            integration = get_context_integration()
            integration.context_manager.update_metadata(
                session_id=session_id,
                mode=ContextMode.RESEARCH
            )

        responses = {}
        all_sources = []
        start_time = time.time()

        # Get response from each model
        for model in models:
            try:
                # Create advanced response with web search
                response, sources = create_advanced_response(
                    user_input=question,
                    message_list=messages,
                    model=model,
                    preferred_links=preferred_urls,
                    stream=False,
                    user_timezone=request.GET.get('user_timezone'),
                    user_time=request.GET.get('user_time')
                )

                responses[model] = response
                all_sources.extend(sources)

                # Add search results to context
                if use_unified and sources:
                    integration = get_context_integration()
                    integration.add_search_results(session_id, sources)

                # Add response to context
                response_time_ms = int((time.time() - start_time) * 1000)
                add_response_to_context(
                    session_id=session_id,
                    response=response,
                    model=model,
                    sources_used=sources,
                    tools_used=["web_search"],
                    response_time_ms=response_time_ms
                )

            except Exception as e:
                logger.error(f"Error with model {model}: {e}")
                responses[model] = f"Error: {str(e)}"

        # Get context statistics
        stats = get_context_stats(session_id)

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
@require_http_methods(["POST"])
def agent_chat_response(request: HttpRequest) -> JsonResponse:
    """
    Agent mode with optional Playwright tools.
    Uses unified context manager with THINKING mode.
    """
    try:
        # Parse request body
        body = json.loads(request.body) if request.body else {}
        question = body.get('question', request.GET.get('question', ''))
        models = body.get('models', request.GET.get('models', 'gpt-4o-mini'))
        use_playwright = body.get('use_playwright', 'false').lower() == 'true'
        use_unified = body.get('use_unified', 'true').lower() == 'true'

        if isinstance(models, str):
            models = models.split(',')

        if not question:
            return JsonResponse({'error': 'No question provided'}, status=400)

        logger.info(f"Agent request: models={models}, playwright={use_playwright}, unified={use_unified}")

        # Prepare context with THINKING mode
        messages, session_id = prepare_context_messages(
            request=request,
            question=question,
            use_unified=use_unified,
            endpoint="agent_chat_response"
        )

        # Update mode to THINKING
        if use_unified:
            integration = get_context_integration()
            integration.context_manager.update_metadata(
                session_id=session_id,
                mode=ContextMode.THINKING
            )

        responses = {}
        start_time = time.time()

        # Get response from each model
        for model in models:
            try:
                # Create agent response
                response = create_agent_response(
                    user_input=question,
                    message_list=messages,
                    model=model,
                    use_playwright=use_playwright,
                    restricted_domain=None,  # No restriction in agent mode
                    current_url=body.get('current_url')
                )

                responses[model] = response

                # Determine tools used
                tools_used = []
                if use_playwright:
                    tools_used.append("playwright")

                # Add response to context
                response_time_ms = int((time.time() - start_time) * 1000)
                add_response_to_context(
                    session_id=session_id,
                    response=response,
                    model=model,
                    tools_used=tools_used,
                    response_time_ms=response_time_ms
                )

            except Exception as e:
                logger.error(f"Error with model {model}: {e}")
                responses[model] = f"Error: {str(e)}"

        # Get context statistics
        stats = get_context_stats(session_id)

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
# Context Management Endpoints
# ============================================================================

@csrf_exempt
@require_http_methods(["POST"])
def input_webtext(request: HttpRequest) -> JsonResponse:
    """
    Receive web content from JS scraper.
    Adds to unified context as js_scraping source.
    """
    try:
        # Parse request body
        body = json.loads(request.body) if request.body else {}
        text_content = body.get('textContent', '')
        current_url = body.get('currentUrl', '')
        use_unified = body.get('use_unified', 'true').lower() == 'true'

        if not text_content:
            return JsonResponse({'error': 'No text content provided'}, status=400)

        logger.info(f"Receiving web content from {current_url}, length={len(text_content)}")

        # Add to context
        session_id = add_web_content(
            request=request,
            text_content=text_content,
            current_url=current_url,
            source_type="js_scraping"
        )

        # Get updated stats
        stats = get_context_stats(session_id)

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
@require_http_methods(["POST", "DELETE"])
def clear_messages_endpoint(request: HttpRequest) -> JsonResponse:
    """
    Clear conversation history and/or fetched context.
    """
    try:
        # Parse options
        preserve_web_content = request.GET.get('preserve_web_content', 'false').lower() == 'true'

        logger.info(f"Clearing messages, preserve_web={preserve_web_content}")

        # Clear messages
        session_id = clear_messages(
            request=request,
            preserve_web_content=preserve_web_content
        )

        return JsonResponse({
            'status': 'success',
            'session_id': session_id,
            'preserved_web_content': preserve_web_content
        })

    except Exception as e:
        logger.error(f"Clear messages error: {e}", exc_info=True)
        return JsonResponse({'error': str(e)}, status=500)


@csrf_exempt
@require_http_methods(["GET"])
def get_context_stats_endpoint(request: HttpRequest) -> JsonResponse:
    """
    Get detailed context statistics.
    """
    try:
        # Get session ID
        integration = get_context_integration()
        session_id = integration._get_session_id(request)

        # Get stats
        stats = get_context_stats(session_id)

        # Add full context if debug mode
        if request.GET.get('debug', 'false').lower() == 'true':
            stats['full_context'] = json.loads(
                integration.get_full_context_json(session_id)
            )

        return JsonResponse(stats)

    except Exception as e:
        logger.error(f"Get stats error: {e}", exc_info=True)
        return JsonResponse({'error': str(e)}, status=500)


@csrf_exempt
@require_http_methods(["GET"])
def export_context(request: HttpRequest) -> JsonResponse:
    """
    Export full context as JSON.
    Useful for debugging and analysis.
    """
    try:
        # Get session ID
        integration = get_context_integration()
        session_id = integration._get_session_id(request)

        # Get full context
        context_json = integration.get_full_context_json(session_id)
        context_dict = json.loads(context_json)

        # Format response
        pretty = request.GET.get('pretty', 'false').lower() == 'true'
        if pretty:
            return JsonResponse(context_dict, json_dumps_params={'indent': 2})
        else:
            return JsonResponse(context_dict)

    except Exception as e:
        logger.error(f"Export context error: {e}", exc_info=True)
        return JsonResponse({'error': str(e)}, status=500)


# ============================================================================
# Streaming Endpoints (SSE)
# ============================================================================

def _build_sse_message(data: Dict[str, Any]) -> str:
    """Build Server-Sent Event message"""
    return f"data: {json.dumps(data)}\n\n"


def _build_status_frame(label: str, detail: Optional[str] = None, url: Optional[str] = None) -> Dict[str, Any]:
    """Build status frame for streaming"""
    status = {"label": label}
    if detail:
        status["detail"] = detail
    if url:
        status["url"] = url
    return {"status": status}


async def _stream_response(
    question: str,
    messages: List[Dict[str, str]],
    model: str,
    session_id: str,
    mode: str = "normal",
    restricted_domain: Optional[str] = None,
    preferred_links: Optional[List[str]] = None
):
    """
    Async generator for streaming responses.
    Yields SSE-formatted messages.
    """
    try:
        # Send initial status
        yield _build_sse_message(_build_status_frame("Preparing context"))

        # Send mode-specific status
        if mode == "normal" and restricted_domain:
            yield _build_sse_message(_build_status_frame("Navigating site", restricted_domain))
        elif mode == "advanced":
            yield _build_sse_message(_build_status_frame("Searching web"))
        elif mode == "agent":
            yield _build_sse_message(_build_status_frame("Thinking"))

        # Start response generation
        start_time = time.time()
        accumulated_response = ""

        # Generate response based on mode
        if mode == "normal":
            # Use agent with Playwright
            response = await asyncio.to_thread(
                create_agent_response,
                user_input=question,
                message_list=messages,
                model=model,
                use_playwright=True,
                restricted_domain=restricted_domain,
                stream=False  # Can't stream agent responses yet
            )
            accumulated_response = response
            yield _build_sse_message({"content": response, "done": False})

        elif mode == "advanced":
            # Use web search
            response, sources = await asyncio.to_thread(
                create_advanced_response,
                user_input=question,
                message_list=messages,
                model=model,
                preferred_links=preferred_links,
                stream=False  # Would need to refactor for streaming
            )
            accumulated_response = response
            yield _build_sse_message({
                "content": response,
                "done": False,
                "used_sources": sources
            })

        else:
            # Regular response
            response = await asyncio.to_thread(
                create_response,
                user_input=question,
                message_list=messages,
                model=model,
                stream=False
            )
            accumulated_response = response
            yield _build_sse_message({"content": response, "done": False})

        # Add to context
        response_time_ms = int((time.time() - start_time) * 1000)
        await asyncio.to_thread(
            add_response_to_context,
            session_id=session_id,
            response=accumulated_response,
            model=model,
            response_time_ms=response_time_ms
        )

        # Send final status with stats
        stats = await asyncio.to_thread(get_context_stats, session_id)
        yield _build_sse_message({
            "content": "",
            "done": True,
            "context_stats": {
                'session_id': session_id,
                'message_count': stats['message_count'],
                'token_count': stats['token_count'],
                'response_time_ms': response_time_ms
            }
        })

    except Exception as e:
        logger.error(f"Streaming error: {e}", exc_info=True)
        yield _build_sse_message({"error": str(e), "done": True})


@csrf_exempt
@require_http_methods(["GET"])
def chat_response_stream(request: HttpRequest) -> StreamingHttpResponse:
    """
    Streaming version of chat_response.
    Returns Server-Sent Events stream.
    """
    try:
        # Extract parameters
        question = request.GET.get('question', '')
        model = request.GET.get('models', 'gpt-4o-mini').split(',')[0]  # Use first model for streaming
        current_url = request.GET.get('current_url', '')

        if not question:
            return JsonResponse({'error': 'No question provided'}, status=400)

        # Extract domain
        restricted_domain = None
        if current_url:
            from urllib.parse import urlparse
            parsed = urlparse(current_url)
            restricted_domain = parsed.netloc

        # Prepare context
        messages, session_id = prepare_context_messages(
            request=request,
            question=question,
            current_url=current_url,
            endpoint="chat_response_stream"
        )

        # Create async event loop for streaming
        async def event_stream():
            async for message in _stream_response(
                question=question,
                messages=messages,
                model=model,
                session_id=session_id,
                mode="normal",
                restricted_domain=restricted_domain
            ):
                yield message

        # Run async generator
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        def sync_generator():
            try:
                gen = event_stream()
                while True:
                    try:
                        yield loop.run_until_complete(gen.__anext__())
                    except StopAsyncIteration:
                        break
            finally:
                loop.close()

        response = StreamingHttpResponse(
            sync_generator(),
            content_type='text/event-stream'
        )
        response['Cache-Control'] = 'no-cache'
        response['X-Accel-Buffering'] = 'no'

        return response

    except Exception as e:
        logger.error(f"Stream error: {e}", exc_info=True)
        return JsonResponse({'error': str(e)}, status=500)