"""
OpenAI-compatible API views for FinGPT.
Stateless adapter for the stateful UnifiedContextManager.
"""

import json
import time
import uuid
import logging
import asyncio
from typing import List, Dict, Any, Optional

from django.http import JsonResponse, StreamingHttpResponse, HttpRequest
from django.views.decorators.csrf import csrf_exempt

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

def _get_api_session_id(request: HttpRequest, user_id: Optional[str] = None) -> str:
    """
    Get a session ID. 
    If user_id is provided, use it to allow potential (but not guaranteed) continuity if needed in future,
    but for now we will be explicit about statelessness in the view.
    If no user_id, generate a random one for this request.
    """
    if user_id:
        return f"api_user_{user_id}"
    return f"api_req_{uuid.uuid4().hex}"

@csrf_exempt
def models_list(request: HttpRequest) -> JsonResponse:
    """
    List available models in OpenAI format.
    GET /v1/models
    """
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
    1. Accepts 'messages' list.
    2. Resets/Creates a session context.
    3. Populates context with history.
    4. Generates response using the last user message as prompt.
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)

    try:
        body = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON body'}, status=400)

    model = body.get('model', 'FinGPT')
    messages = body.get('messages', [])
    stream = body.get('stream', False)
    user_id = body.get('user')
    temperature = body.get('temperature', 0.7)
    
    # New required parameters for Agent API
    mode_str = body.get('mode')
    target_url = body.get('url')

    if not messages:
        return JsonResponse({'error': {'message': 'messages array is required', 'type': 'invalid_request_error'}}, status=400)
        
    if not mode_str:
        return JsonResponse({'error': {'message': "mode is required (e.g. 'thinking', 'research')", 'type': 'invalid_request_error'}}, status=400)

    # validate model
    if model not in MODELS_CONFIG:
        return JsonResponse({'error': {'message': f'Model {model} does not exist', 'type': 'invalid_request_error'}}, status=404)

    # 1. Setup Session
    session_id = _get_api_session_id(request, user_id)
    context_mgr = get_context_manager()
    integration = get_context_integration()

    # 2. Reset Context (Statelessness)
    if session_id in context_mgr.sessions:
        integration.clear_messages(request, session_id=session_id, preserve_web_content=False)
        context_mgr.sessions[session_id]["system_prompt"] = "You are a helpful financial assistant." 
    
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
            # We continue even if scraping fails? Or return error? 
            # Proceeding allows chat to continue, but maybe warn?
            pass

    # 3. Populate Context
    history_messages = messages[:-1]
    last_message = messages[-1]
    
    for msg in history_messages:
        role = msg.get('role')
        content = msg.get('content', '')
        if role == 'system':
            session = context_mgr._get_or_create_session(session_id)
            session["system_prompt"] = content
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
    context_mode = ContextMode.THINKING
    if mode_str.lower() == 'research':
        context_mode = ContextMode.RESEARCH
    elif mode_str.lower() == 'normal':
        context_mode = ContextMode.NORMAL

    # Prepare for execution
    context_mgr.update_metadata(
        session_id=session_id,
        mode=context_mode,
        current_url=target_url if target_url else ""
    )

    formatted_messages = context_mgr.get_formatted_messages_for_api(session_id)
    
    # DEBUG: Log the messages we are about to send
    logger.info(f"API Stateless Context build for session {session_id}:")
    for m in formatted_messages:
        logger.info(f" - {str(m)[:100]}...")
    
    # 4. Generate Response
    if stream:
        return _handle_streaming(context_mgr, session_id, last_user_content, formatted_messages, model)
    else:
        return _handle_sync(context_mgr, session_id, last_user_content, formatted_messages, model)


def _handle_sync(context_mgr, session_id, question, messages, model):
    try:
        start_time = time.time()
        
        mode = context_mgr.sessions[session_id]['metadata'].mode
        current_url = context_mgr.sessions[session_id]['metadata'].current_url

        if mode == ContextMode.RESEARCH:
             # Advanced / Research Mode
            response_content = ds.create_advanced_response(
                user_input=question,
                message_list=messages,
                model=model,
                preferred_links=[]
            )
        else:
            # Agent / Thinking Mode
            response_content = ds.create_agent_response(
                user_input=question,
                message_list=messages,
                model=model,
                current_url=current_url
            )
        
        # Record response
        response_time_ms = int((time.time() - start_time) * 1000)
        context_mgr.add_assistant_message(
            session_id=session_id,
            content=response_content,
            model=model,
            response_time_ms=response_time_ms
        )
        
        # Format OpenAI response
        completion_id = f"chatcmpl-{uuid.uuid4().hex}"
        created = int(time.time())
        stats = context_mgr.get_session_stats(session_id)
        
        return JsonResponse({
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
                "prompt_tokens": stats.get('token_count', 0), # Approx
                "completion_tokens": len(response_content) // 4, # Approx
                "total_tokens": stats.get('token_count', 0) + (len(response_content) // 4)
            }
        })
        
    except Exception as e:
        logger.error(f"API Sync Error: {e}", exc_info=True)
        return JsonResponse({'error': {'message': str(e), 'type': 'server_error'}}, status=500)


def _handle_streaming(context_mgr, session_id, question, messages, model):
    
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
        
        try:
            mode = context_mgr.sessions[session_id]['metadata'].mode
            current_url = context_mgr.sessions[session_id]['metadata'].current_url
            
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            full_content = []

            if mode == ContextMode.RESEARCH:
                # Advanced Stream: yield (text_chunk, sources)
                stream_generator, _ = ds.create_advanced_response_streaming(
                    user_input=question,
                    message_list=messages,
                    model=model,
                    preferred_links=[]
                )
                stream_iter = stream_generator.__aiter__()
                
                while True:
                    try:
                        chunk_tuple = loop.run_until_complete(stream_iter.__anext__())
                        text_chunk, sources = chunk_tuple
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
                    except StopAsyncIteration:
                        break

            else:
                # Agent Stream: yield text_chunk
                stream_generator, _ = ds.create_agent_response_stream(
                    user_input=question,
                    message_list=messages,
                    model=model,
                    current_url=current_url
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
            
            loop.close()
            
            # Final chunk
            final_chunk = {
                "id": completion_id,
                "object": "chat.completion.chunk",
                "created": created,
                "model": model,
                "choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}]
            }
            yield f"data: {json.dumps(final_chunk)}\n\n"
            yield "data: [DONE]\n\n"
            
            # Post-processing: save to context
            final_text = "".join(full_content)
            context_mgr.add_assistant_message(session_id, final_text, model=model)
            
        except Exception as e:
            logger.error(f"API Stream Error: {e}", exc_info=True)
            err_chunk = {
                "error": {"message": str(e), "type": "server_error"}
            }
            yield f"data: {json.dumps(err_chunk)}\n\n"

    response = StreamingHttpResponse(event_stream(), content_type='text/event-stream')
    response['Cache-Control'] = 'no-cache'
    return response

