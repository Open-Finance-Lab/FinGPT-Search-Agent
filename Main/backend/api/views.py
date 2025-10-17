"""
API Views for FinGPT Search Agent

SECURITY NOTE: CSRF Protection
-------------------------------
Most endpoints use @csrf_exempt because this backend serves a browser extension frontend.
Browser extensions cannot easily include CSRF tokens in their requests.

Security is provided through:
1. CORS_ALLOWED_ORIGINS restricting which origins can make requests
2. SESSION_COOKIE_SAMESITE='None' with SESSION_COOKIE_SECURE=True (in production)
3. Session-based authentication via Django sessions

PRODUCTION RECOMMENDATION:
For production deployments, consider implementing API token authentication
instead of relying solely on session cookies and CORS.
"""

import json
import os
import csv
import asyncio
import logging
import re
from datetime import datetime
from pathlib import Path
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse, StreamingHttpResponse
from django_ratelimit.decorators import ratelimit
from django.conf import settings
from datascraper import datascraper as ds
from datascraper import create_embeddings as ce
from datascraper.preferred_links_manager import get_manager

from django.views import View
from mcp_client.agent import create_fin_agent
from agents import Runner
from datascraper.r2c_context_manager import R2CContextManager
from datascraper.models_config import MODELS_CONFIG

# Constants
QUESTION_LOG_PATH = os.path.join(os.path.dirname(__file__), 'questionLog.csv')

# Helper function to get version from pyproject.toml
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

# Initial message list (kept for backward compatibility)
# This is a global message list
message_list = [
    {"role": "user",
     "content": "[SYSTEM MESSAGE]: You are a helpful financial assistant. Always answer questions to the best of your ability."}
]

# R2C
r2c_manager = R2CContextManager(
    max_tokens=20000,
    compression_ratio=0.5,
    rho=0.5,
    gamma=1.0
)

class MCPGreetView(View):
    def get(self, request):
        name = request.GET.get("name", "world")
        
        # Use the OpenAI Agents SDK to run MCP tools
        try:
            result = asyncio.run(self._run_mcp_agent(name))
            return JsonResponse({"reply": result})
        except Exception as e:
            logging.error(f"MCP Agent error: {e}")
            return JsonResponse({"error": f"MCP Agent error: {str(e)}"}, status=500)

    async def _run_mcp_agent(self, name: str) -> str:
        # Create the FinGPT agent with MCP server using async context manager
        async with create_fin_agent(model="o4-mini") as agent:
            # Run the agent with a greeting request
            prompt = f"Use the greet tool to say hello to '{name}'. Call the greet function with the name parameter."
            logging.info(f"[MCP DEBUG] Running agent with prompt: {prompt}")
            result = await Runner.run(agent, prompt)
            logging.info(f"[MCP DEBUG] Runner result: {result}")
            logging.info(f"[MCP DEBUG] Result type: {type(result)}")
            logging.info(f"[MCP DEBUG] Result attributes: {dir(result)}")
            logging.info(f"[MCP DEBUG] Result final_output: {result.final_output}")
            
            # Check if final_output is empty, try other attributes
            if not result.final_output:
                logging.warning(f"[MCP DEBUG] final_output is empty, checking other attributes")
                if hasattr(result, 'output'):
                    logging.info(f"[MCP DEBUG] Result output: {result.output}")
                if hasattr(result, 'content'):
                    logging.info(f"[MCP DEBUG] Result content: {result.content}")
                if hasattr(result, 'response'):
                    logging.info(f"[MCP DEBUG] Result response: {result.response}")
            
            return result.final_output or "No response generated"


# Helper functions
def _get_session_id(request):
    """Get or create session ID for R2C context management."""
    # custom session ID from frontend
    custom_session_id = request.GET.get('session_id')
    
    # For POST requests, check body data
    if not custom_session_id and request.method == 'POST':
        try:
            body_data = json.loads(request.body)
            custom_session_id = body_data.get('session_id')
        except:
            pass
    
    if custom_session_id:
        # logging.info(f"[R2C DEBUG] Using custom session ID: {custom_session_id}")
        return custom_session_id

    # Fall back to Django session
    if not request.session.session_key:
        request.session.create()
        # logging.info(f"[R2C DEBUG] Created new Django session: {request.session.session_key}")
    else:
        pass
        # logging.info(f"[R2C DEBUG] Using existing Django session: {request.session.session_key}")
    return request.session.session_key

def _prepare_context_messages(request, question, use_r2c=True, current_url=None):
    """
    Prepare context messages using R2C or legacy system.

    Args:
        request: Django request object
        question: User's question to add
        use_r2c: Whether to use R2C context management
        current_url: Current webpage URL (optional)

    Returns:
        tuple: (legacy_messages, session_id)
    """
    session_id = _get_session_id(request) if use_r2c else None

    if use_r2c and session_id:
        # Update current webpage if URL provided
        if current_url:
            r2c_manager.update_current_webpage(session_id, current_url)

        # Update user's timezone and time if provided
        user_timezone = request.GET.get('user_timezone')
        user_time = request.GET.get('user_time')
        if user_timezone or user_time:
            r2c_manager.update_user_time_info(session_id, user_timezone, user_time)

        r2c_manager.add_message(session_id, "user", question)

        context_messages = r2c_manager.get_context(session_id)

        # R2C already includes system prompt and handles compression
        # Just use the context messages directly
        legacy_messages = context_messages
    else:
        # Use legacy message_list - append the question with header
        message_list.append({"role": "user", "content": f"[USER MESSAGE]: {question}"})
        legacy_messages = message_list.copy()

    return legacy_messages, session_id

def _add_response_to_context(session_id, response, use_r2c=True):
    """Add assistant response to R2C manager if enabled."""
    if use_r2c and session_id:
        r2c_manager.add_message(session_id, "assistant", response)
    else:
        # Add to legacy message_list with header
        message_list.append({"role": "user", "content": f"[ASSISTANT MESSAGE]: {response}"})

def _prepare_response_with_stats(responses, session_id, use_r2c=True, single_response_mode=False):
    """
    Prepare JSON response with optional R2C stats.

    Args:
        responses: Dictionary of model responses or single response string
        session_id: Session ID for R2C
        use_r2c: Whether R2C is enabled
        single_response_mode: Whether to use 'reply' field for single response

    Returns:
        JsonResponse object
    """
    if use_r2c and session_id:
        stats = r2c_manager.get_session_stats(session_id)

        if single_response_mode and isinstance(responses, dict) and len(responses) == 1:
            # Single model - return as 'reply' for MCP frontend compatibility
            single_response = next(iter(responses.values()))
            return JsonResponse({
                'reply': single_response,
                'r2c_stats': stats
            })
        else:
            # Multiple models or not in single response mode
            response_key = 'resp' if isinstance(responses, dict) else 'reply'
            return JsonResponse({
                response_key: responses,
                'r2c_stats': stats
            })
    else:
        # No R2C stats
        if single_response_mode and isinstance(responses, dict) and len(responses) == 1:
            single_response = next(iter(responses.values()))
            return JsonResponse({'reply': single_response})
        else:
            response_key = 'resp' if isinstance(responses, dict) else 'reply'
            return JsonResponse({response_key: responses})

def _ensure_log_file_exists():
    """Create log file with headers if it doesn't exist, using UTF-8 encoding."""
    if not os.path.isfile(QUESTION_LOG_PATH):
        with open(QUESTION_LOG_PATH, 'w', newline='', encoding='utf-8') as log_file:
            writer = csv.writer(log_file)
            writer.writerow(['Button', 'URL', 'Question', 'Date', 'Time', 'Response_Preview'])

def _log_interaction(button_clicked, current_url, question, response=None):
    """
    Log interaction details with timestamp and response preview.
    Uses UTF-8 with `errors="replace"`
    """
    _ensure_log_file_exists()

    now = datetime.now()
    date_str = now.strftime('%Y-%m-%d')
    time_str = now.strftime('%H:%M:%S')

    # Handles invalid chars.
    def safe_str(s):
        return str(s).encode('utf-8', errors='replace').decode('utf-8')

    # Only record first 80 chars of the response
    response_preview = response[:80] if response else "N/A"

    # Clean each field before writing
    button_clicked = safe_str(button_clicked)
    current_url = safe_str(current_url)
    question = safe_str(question)
    response_preview = safe_str(response_preview)

    # Check if identical question from same URL exists
    question_exists = False
    # Read using UTF-8 and replace invalid bytes
    with open(QUESTION_LOG_PATH, 'r', encoding='utf-8', errors='replace') as file:
        reader = csv.reader(file)
        next(reader, None)  # Skip header
        for row in reader:
            # Make sure row is long enough to avoid index errors
            if len(row) >= 3:
                existing_url = row[1]
                existing_question = row[2]
                # Compare with sanitized inputs
                if existing_url == current_url and existing_question == question:
                    question_exists = True
                    break

    if not question_exists:
        with open(QUESTION_LOG_PATH, 'a', newline='', encoding='utf-8', errors='replace') as log_file:
            writer = csv.writer(log_file)
            writer.writerow([button_clicked, current_url, question, date_str, time_str, response_preview])

# View to handle appending the text from FRONT-END SCRAPER to the message list
@csrf_exempt
@ratelimit(key='ip', rate=lambda g, r: settings.API_RATE_LIMIT, method='POST')
def add_webtext(request):
    """Handle appending the site's text to the message list"""
    if request.method != 'POST':
        return JsonResponse({'error': 'Invalid request method; use POST.'}, status=405)
    
    try:
        body_data = json.loads(request.body)
        text_content = body_data.get('textContent', '')
        current_url = body_data.get('currentUrl', '')
        use_r2c = body_data.get('use_r2c', True)  # Default to using R2C
        session_id_from_body = body_data.get('session_id')

        # logging.info(f"[R2C DEBUG] add_webtext - URL: {current_url}, use_r2c: {use_r2c}, session_id: {session_id_from_body}, content_length: {len(text_content)}")

        if not text_content:
            # logging.warning("[R2C DEBUG] No text content provided")
            return JsonResponse({"error": "No textContent provided."}, status=400)

        message_list.append({
            "role": "user",
            "content": text_content
        })

        if use_r2c:
            session_id = _get_session_id(request)
            if session_id:
                # logging.info(f"[R2C DEBUG] Adding web content to session {session_id}, URL: {current_url}, content length: {len(text_content)}")
                r2c_manager.add_message(session_id, "user", f"[Web Content from {current_url}]: {text_content}")
                # Log session stats after adding
                stats = r2c_manager.get_session_stats(session_id)
                # logging.info(f"[R2C DEBUG] Session {session_id} stats after web content: {stats}")

        _log_interaction("add_webtext", current_url, f"Added web content: {text_content[:20]}...")
        
        return JsonResponse({"resp": "Text added successfully as user message"})
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)

@ratelimit(key='ip', rate=lambda g, r: settings.API_RATE_LIMIT, method='POST')
def chat_response(request):
    """
    Normal Mode: Help user understand the CURRENT website using Playwright navigation.
    Agent stays within the current domain and navigates to find information.
    """
    question = request.GET.get('question', '')
    selected_models = request.GET.get('models', '')
    use_rag = request.GET.get('use_rag', 'false').lower() == 'true'
    current_url = request.GET.get('current_url', '')
    use_r2c = request.GET.get('use_r2c', 'true').lower() == 'true'
    user_timezone = request.GET.get('user_timezone')
    user_time = request.GET.get('user_time')

    # Validate and parse models
    if not selected_models:
        return JsonResponse({'error': 'No models specified'}, status=400)

    models = [model.strip() for model in selected_models.split(',') if model.strip()]
    if not models:
        return JsonResponse({'error': 'No valid models specified'}, status=400)

    # Extract domain from current_url for domain-restricted navigation
    from urllib.parse import urlparse
    restricted_domain = None
    if current_url:
        try:
            parsed = urlparse(current_url)
            restricted_domain = parsed.netloc or None
            if restricted_domain:
                logging.info(f"[NORMAL MODE] Domain restriction: {restricted_domain}")
        except Exception as e:
            logging.warning(f"Failed to parse current_url: {e}")

    responses = {}

    # Prepare context messages using R2C or legacy system
    legacy_messages, session_id = _prepare_context_messages(request, question, use_r2c, current_url)

    for model in models:
        try:
            if use_rag:
                # Use the RAG pipeline
                response = ds.create_rag_response(question, legacy_messages, model)
            else:
                # Normal mode always uses agent with Playwright (domain-restricted)
                response = ds.create_agent_response(
                    question,
                    legacy_messages,
                    model,
                    use_playwright=True,
                    restricted_domain=restricted_domain,
                    current_url=current_url,
                    user_timezone=user_timezone,
                    user_time=user_time
                )
                logging.info(f"[NORMAL MODE] Using Playwright within {restricted_domain or 'any domain'}")

            responses[model] = response

            # Add assistant response to R2C manager
            _add_response_to_context(session_id, response, use_r2c)

        except Exception as e:
            logging.error(f"Error processing model {model}: {e}")
            responses[model] = f"Error: {str(e)}"

    first_model_response = next(iter(responses.values())) if responses else "No response"
    _log_interaction("normal_mode", current_url, question, first_model_response)

    return _prepare_response_with_stats(responses, session_id, use_r2c)

@ratelimit(key='ip', rate=lambda g, r: settings.API_RATE_LIMIT, method='GET')
def chat_response_stream(request):
    """
    Normal Mode Streaming: Help user understand the CURRENT website using Playwright navigation.
    Agent stays within the current domain and navigates to find information.
    """
    question = request.GET.get('question', '')
    selected_models = request.GET.get('models', '')
    use_rag = request.GET.get('use_rag', 'false').lower() == 'true'
    current_url = request.GET.get('current_url', '')
    use_r2c = request.GET.get('use_r2c', 'true').lower() == 'true'
    user_timezone = request.GET.get('user_timezone')
    user_time = request.GET.get('user_time')

    # Validate and parse models
    if not selected_models:
        return JsonResponse({'error': 'No models specified'}, status=400)

    models = [model.strip() for model in selected_models.split(',') if model.strip()]
    if not models:
        return JsonResponse({'error': 'No valid models specified'}, status=400)

    model = models[0]

    # Extract domain from current_url for domain-restricted navigation
    from urllib.parse import urlparse
    restricted_domain = None
    if current_url:
        try:
            parsed = urlparse(current_url)
            restricted_domain = parsed.netloc or None
            if restricted_domain:
                logging.info(f"[NORMAL MODE STREAM] Domain restriction: {restricted_domain}")
        except Exception as e:
            logging.warning(f"Failed to parse current_url: {e}")

    # Prepare context messages using R2C
    legacy_messages, session_id = _prepare_context_messages(request, question, use_r2c, current_url)

    def event_stream():
        """Generator function for SSE streaming"""
        try:
            # Send initial connection event (as bytes for WSGI compatibility)
            yield b'event: connected\ndata: {"status": "connected"}\n\n'

            if use_rag:
                # RAG doesn't support streaming yet, return full response
                response = ds.create_rag_response(question, legacy_messages, model)
                sse_data = f'data: {json.dumps({"content": response, "done": True})}\n\n'
                yield sse_data.encode('utf-8')
                full_response = response
            else:
                # Normal mode always uses agent with Playwright (domain-restricted)
                logging.info(f"[NORMAL MODE STREAM] Using Playwright within {restricted_domain or 'any domain'}")

                full_response = ""
                stream_generator = None
                stream_state = {"final_output": ""}
                loop = None
                stream_iter = None

                try:
                    stream_generator, stream_state = ds.create_agent_response_stream(
                        question,
                        legacy_messages,
                        model,
                        use_playwright=True,
                        restricted_domain=restricted_domain,
                        current_url=current_url,
                        user_timezone=user_timezone,
                        user_time=user_time
                    )

                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    stream_iter = stream_generator.__aiter__()

                    while True:
                        try:
                            chunk = loop.run_until_complete(stream_iter.__anext__())
                        except StopAsyncIteration:
                            break

                        if chunk:
                            full_response += chunk
                            sse_payload = {"content": chunk, "done": False}
                            sse_data = f"data: {json.dumps(sse_payload)}\n\n"
                            yield sse_data.encode('utf-8')

                finally:
                    if stream_iter and loop:
                        try:
                            loop.run_until_complete(stream_iter.aclose())
                        except Exception:
                            pass
                    if loop:
                        try:
                            loop.run_until_complete(loop.shutdown_asyncgens())
                        except Exception:
                            pass
                        asyncio.set_event_loop(None)
                        loop.close()

                final_response = stream_state.get("final_output") or full_response
                full_response = final_response

                # Send completion event
                sse_data = f'data: {json.dumps({"content": "", "done": True})}\n\n'
                yield sse_data.encode('utf-8')

            _add_response_to_context(session_id, full_response, use_r2c)

            _log_interaction("normal_mode_stream", current_url, question, full_response)

            # Send R2C stats if enabled
            if use_r2c and session_id:
                stats = r2c_manager.get_session_stats(session_id)
                sse_data = f'data: {json.dumps({"r2c_stats": stats})}\n\n'
                yield sse_data.encode('utf-8')

        except Exception as e:
            logging.error(f"Error in streaming response: {e}")
            import traceback
            traceback.print_exc()
            sse_data = f'data: {json.dumps({"error": str(e), "done": True})}\n\n'
            yield sse_data.encode('utf-8')

    response = StreamingHttpResponse(
        event_stream(),
        content_type='text/event-stream'
    )
    response['Cache-Control'] = 'no-cache'
    response['X-Accel-Buffering'] = 'no'  # Disable Nginx buffering
    return response

@csrf_exempt
@ratelimit(key='ip', rate=lambda g, r: settings.API_RATE_LIMIT, method='POST')
def agent_chat_response(request):
    """Process chat response via Agent with optional tools (Playwright, etc.)"""
    question = request.GET.get('question', '')
    selected_models = request.GET.get('models', '')
    current_url = request.GET.get('current_url', '')
    use_r2c = request.GET.get('use_r2c', 'true').lower() == 'true'
    use_playwright = request.GET.get('use_playwright', 'false').lower() == 'true'
    user_timezone = request.GET.get('user_timezone')
    user_time = request.GET.get('user_time')

    # Validate and parse models
    if not selected_models:
        return JsonResponse({'error': 'No models specified'}, status=400)

    models = [model.strip() for model in selected_models.split(',') if model.strip()]
    if not models:
        return JsonResponse({'error': 'No valid models specified'}, status=400)

    responses = {}

    # Prepare context messages using R2C or legacy system
    legacy_messages, session_id = _prepare_context_messages(request, question, use_r2c, current_url)

    for model in models:
        try:
            # Use the Agent path with tools
            response = ds.create_agent_response(
                question,
                legacy_messages,
                model,
                use_playwright=use_playwright,
                user_timezone=user_timezone,
                user_time=user_time
            )
            if use_playwright:
                logging.info(f"[AGENT DEBUG] Model {model} response with Playwright tools")
            responses[model] = response

            _add_response_to_context(session_id, response, use_r2c)

        except Exception as e:
            logging.error(f"Error processing agent model {model}: {e}")
            responses[model] = f"Error: {str(e)}"

    # Log with a distinct tag allowing filtering later
    first_model_response = next(iter(responses.values())) if responses else "No response"
    _log_interaction("agent_chat", current_url, question, first_model_response)

    # Return response with optional R2C stats, using single response mode
    return _prepare_response_with_stats(responses, session_id, use_r2c, single_response_mode=True)

@csrf_exempt
@ratelimit(key='ip', rate=lambda g, r: settings.API_RATE_LIMIT, method='POST')
def adv_response(request):
    """
    Extensive Mode: Search for information ANYWHERE on the web using web_search.
    Uses OpenAI Responses API with built-in web_search tool (no domain restrictions).
    """
    question = request.GET.get('question', '')
    selected_models = request.GET.get('models', '')
    use_rag = request.GET.get('use_rag', 'false').lower() == 'true'
    current_url = request.GET.get('current_url', '')
    use_r2c = request.GET.get('use_r2c', 'true').lower() == 'true'
    preferred_links_json = request.GET.get('preferred_links', '')
    user_timezone = request.GET.get('user_timezone')
    user_time = request.GET.get('user_time')

    # Parse preferred links from frontend
    preferred_links = []
    if preferred_links_json:
        try:
            preferred_links = json.loads(preferred_links_json)
            logging.info(f"[EXTENSIVE MODE] Received {len(preferred_links)} preferred links")
        except json.JSONDecodeError:
            logging.error(f"Failed to parse preferred links JSON: {preferred_links_json}")

    if not selected_models:
        return JsonResponse({'error': 'No models specified'}, status=400)

    models = [model.strip() for model in selected_models.split(',') if model.strip()]
    if not models:
        return JsonResponse({'error': 'No valid models specified'}, status=400)

    responses = {}

    # Prepare context messages using R2C or legacy system
    legacy_messages, session_id = _prepare_context_messages(request, question, use_r2c, current_url)

    for model in models:
        try:
            if use_rag:
                # Use the RAG pipeline for advanced response
                response = ds.create_rag_advanced_response(question, legacy_messages, model, preferred_links)
            else:
                # Extensive mode uses OpenAI Responses API with web_search (no Playwright for now)
                # TODO combine Playwright, web_search and even more tools in the future for the ultimate intelligent web search UX
                logging.info(f"[EXTENSIVE MODE] Using web_search for external research")
                response = ds.create_advanced_response(question, legacy_messages, model, preferred_links, user_timezone=user_timezone, user_time=user_time)

            responses[model] = response

            _add_response_to_context(session_id, response, use_r2c)

        except Exception as e:
            logging.error(f"Error processing extensive mode model {model}: {e}")
            responses[model] = f"Error: {str(e)}"

    first_model_response = next(iter(responses.values())) if responses else "No response"
    _log_interaction("extensive_mode", current_url, question, first_model_response)

    # Get the used URLs from datascraper
    used_urls_list = list(ds.used_urls_ordered) if getattr(ds, "used_urls_ordered", None) else list(ds.used_urls)

    logging.info(f"[EXTENSIVE MODE] Sending {len(used_urls_list)} source URLs to frontend:")
    for idx, url in enumerate(used_urls_list, 1):
        logging.info(f"  [{idx}] {url}")

    # Return response with optional R2C stats and used URLs
    response_data = _prepare_response_with_stats(responses, session_id, use_r2c)
    response_json = json.loads(response_data.content)
    response_json['used_urls'] = used_urls_list
    return JsonResponse(response_json)

@csrf_exempt
@ratelimit(key='ip', rate=lambda g, r: settings.API_RATE_LIMIT, method='POST')
def adv_response_stream(request):
    """Process streaming advanced chat response from selected models using SSE"""
    question = request.GET.get('question', '')
    selected_models = request.GET.get('models', '')
    use_rag = request.GET.get('use_rag', 'false').lower() == 'true'
    current_url = request.GET.get('current_url', '')
    use_r2c = request.GET.get('use_r2c', 'true').lower() == 'true'
    preferred_links_json = request.GET.get('preferred_links', '')
    user_timezone = request.GET.get('user_timezone')
    user_time = request.GET.get('user_time')

    # Parse preferred links from frontend
    preferred_links = []
    if preferred_links_json:
        try:
            preferred_links = json.loads(preferred_links_json)
            logging.info(f"Received {len(preferred_links)} preferred links for streaming")
        except json.JSONDecodeError:
            logging.error(f"Failed to parse preferred links JSON: {preferred_links_json}")

    # Validate and parse models
    if not selected_models:
        return JsonResponse({'error': 'No models specified'}, status=400)

    models = [model.strip() for model in selected_models.split(',') if model.strip()]
    if not models:
        return JsonResponse({'error': 'No valid models specified'}, status=400)

    model = models[0]

    # Prepare context messages using R2C
    legacy_messages, session_id = _prepare_context_messages(request, question, use_r2c, current_url)

    def event_stream():
        """Generator function for SSE streaming"""
        try:
            # Send initial connection event
            yield b'event: connected\ndata: {"status": "connected"}\n\n'

            if use_rag:
                # RAG doesn't support streaming yet, can't be bothered to mock streaming
                response = ds.create_rag_advanced_response(question, legacy_messages, model, preferred_links)
                sse_data = f'data: {json.dumps({"content": response, "done": True})}\n\n'
                yield sse_data.encode('utf-8')

                _add_response_to_context(session_id, response, use_r2c)
            else:
                # Stream response from advanced model
                full_response = ""
                source_urls: list[str] = []
                stream_generator = None
                stream_state = {"final_output": "", "used_urls": []}
                loop = None
                stream_iter = None

                import asyncio

                try:
                    stream_generator, stream_state = ds.create_advanced_response_streaming(
                        question,
                        legacy_messages,
                        model,
                        preferred_links,
                        user_timezone=user_timezone,
                        user_time=user_time
                    )

                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    stream_iter = stream_generator.__aiter__()

                    while True:
                        try:
                            text_chunk, urls = loop.run_until_complete(stream_iter.__anext__())
                        except StopAsyncIteration:
                            break

                        if text_chunk:
                            full_response += text_chunk
                            sse_data = f'data: {json.dumps({"content": text_chunk, "done": False})}\n\n'
                            yield sse_data.encode('utf-8')
                        if urls:
                            source_urls = urls

                finally:
                    if stream_iter and loop:
                        try:
                            loop.run_until_complete(stream_iter.aclose())
                        except Exception:
                            pass
                    if loop:
                        try:
                            loop.run_until_complete(loop.shutdown_asyncgens())
                        except Exception:
                            pass
                        asyncio.set_event_loop(None)
                        loop.close()

                final_response = stream_state.get("final_output") or full_response
                final_urls = stream_state.get("used_urls") or source_urls

                _add_response_to_context(session_id, final_response, use_r2c)
                _log_interaction("advanced_stream", current_url, question, final_response)

                final_payload = {
                    "content": "",
                    "done": True
                }

                if final_urls:
                    final_payload["used_urls"] = final_urls
                if use_r2c and session_id:
                    stats = r2c_manager.get_session_stats(session_id)
                    final_payload["r2c_stats"] = stats

                sse_data = f'data: {json.dumps(final_payload)}\n\n'
                yield sse_data.encode('utf-8')

        except Exception as e:
            logging.error(f"Error in advanced streaming response: {e}")
            import traceback
            traceback.print_exc()
            sse_data = f'data: {json.dumps({"error": str(e), "done": True})}\n\n'
            yield sse_data.encode('utf-8')

    # Return streaming response
    response = StreamingHttpResponse(
        event_stream(),
        content_type='text/event-stream'
    )
    response['Cache-Control'] = 'no-cache'
    response['X-Accel-Buffering'] = 'no'  # Disable Nginx buffering
    return response


@csrf_exempt
def clear(request):
    """Clear conversation messages but preserve scraped web content"""
    use_r2c = request.GET.get('use_r2c', 'true').lower() == 'true'

    # For legacy system, only clear non-web content messages
    if message_list:
        # Keep only the system message and web content
        preserved_messages = [message_list[0]]
        for msg in message_list[1:]:
            if "[Web Content from" in msg.get("content", "") or msg.get("content", "").startswith("Yahoo Finance") or msg.get("content", "").startswith("<!DOCTYPE"):
                preserved_messages.append(msg)

        message_list.clear()
        message_list.extend(preserved_messages)

    # Clear only conversation in R2C if enabled
    if use_r2c:
        session_id = _get_session_id(request)
        if session_id:
            r2c_manager.clear_conversation_only(session_id)
            message = 'Conversation cleared (web content preserved)'
        else:
            message = 'Conversation cleared (no R2C session found)'
    else:
        message = 'Conversation cleared'

    current_url = request.GET.get('current_url', 'N/A')
    _log_interaction("clear", current_url, "Cleared conversation history")

    return JsonResponse({'resp': message})

@csrf_exempt
def get_sources(request):
    """Get sources for a query"""
    query = request.GET.get('query', '')
    current_url = request.GET.get('current_url')
    sources = ds.get_sources(query, current_url=current_url)
    
    # Log the source request
    _log_interaction("sources", current_url or 'N/A', f"Source request: {query}")
    
    return JsonResponse({'resp': sources})

@csrf_exempt
def get_logo(request):
    """Get website logo"""
    url = request.GET.get('url', '')
    
    try:
        logo_src = ds.get_website_icon(url)
        return JsonResponse({'resp': logo_src})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

# Legacy log_question function maintained for compatibility
def log_question(request):
    """Legacy question logging (redirects to enhanced logging)"""
    question = request.GET.get('question', '')
    button_clicked = request.GET.get('button', '')
    current_url = request.GET.get('current_url', '')
    
    if question and button_clicked and current_url:
        _log_interaction(button_clicked, current_url, question)
    
    return JsonResponse({'status': 'success'})

def get_preferred_urls(request):
    """Retrieve preferred URLs from storage"""
    manager = get_manager()
    urls = manager.get_links()
    return JsonResponse({'urls': urls})

@csrf_exempt
def add_preferred_url(request):
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
                    _log_interaction("add_url", new_url, f"Added preferred URL: {new_url}")
                    return JsonResponse({'status': 'success'})
                else:
                    return JsonResponse({'status': 'exists'})
        except Exception as e:
            logging.error(f"Error adding preferred URL: {e}")
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

    return JsonResponse({'status': 'failed'}, status=400)

@csrf_exempt
def sync_preferred_urls(request):
    """Sync preferred URLs from frontend to backend storage"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            urls = data.get('urls', [])

            manager = get_manager()
            manager.set_links(urls)

            return JsonResponse({'status': 'success', 'synced': len(urls)})
        except Exception as e:
            logging.error(f"Error syncing preferred URLs: {e}")
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

    return JsonResponse({'status': 'failed'}, status=400)

def get_r2c_stats(request):
    """Get R2C context statistics for current session"""
    session_id = _get_session_id(request)
    if session_id:
        stats = r2c_manager.get_session_stats(session_id)
        return JsonResponse({'stats': stats})
    else:
        return JsonResponse({'error': 'No session found'}, status=404)

def get_available_models(request):
    """Get list of available models with their configurations"""
    models = []
    for model_id, config in MODELS_CONFIG.items():
        models.append({
            'id': model_id,
            'provider': config['provider'],
            'description': config['description'],
            'supports_rag': config['supports_rag'],
            'supports_mcp': config['supports_mcp'],
            'supports_advanced': config['supports_advanced'],
            'display_name': f"{model_id} - {config['description']}"
        })
    return JsonResponse({'models': models})

@csrf_exempt
def folder_path(request):
    """
    Upload the folder path for the RAG.
    """
    # print("[DEBUG] arrived in view with request:", request)
    if request.method == 'POST':
        try:

            if 'json_data' not in request.FILES :
                return JsonResponse({'error': 'No JSON file received'}, status=400)

            file = request.FILES['json_data']

            # Read the JSON data from the file
            json_data = json.loads(file.read())
            # print("[DEBUG] json_data: ", json_data)

            # Create embeddings for files
            response_data, status_code = ce.upload_folder(json_data)
            # print("[DEBUG] Flask API response:", response_data)
            # print("[DEBUG] Response status code:", status_code)

            return JsonResponse(response_data, status=status_code)

        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    else:
        return JsonResponse({'error': 'Only POST requests allowed'}, status=405)

def health(request):
    """
    Health check endpoint for load balancers and monitoring.
    Returns 200 OK if the service is running.
    """
    return JsonResponse({
        'status': 'healthy',
        'service': 'fingpt-backend',
        'timestamp': datetime.now().isoformat(),
        'version': _get_version()
    })
