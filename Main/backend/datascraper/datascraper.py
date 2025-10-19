import os
import logging
import asyncio
from collections.abc import AsyncIterator
from typing import Any, Dict, Tuple

from dotenv import load_dotenv

from openai import OpenAI
from anthropic import Anthropic

from . import cdm_rag
from mcp_client.agent import create_fin_agent, USER_ONLY_MODELS, DEFAULT_PROMPT
from .models_config import (
    MODELS_CONFIG,
    PROVIDER_CONFIGS,
    get_model_config,
    get_provider_config,
    validate_model_support
)
from .preferred_links_manager import get_manager
from .openai_search import (
    create_responses_api_search,
    format_sources_for_frontend,
    is_responses_api_available
)

# Load .env from the backend root directory
from pathlib import Path
backend_dir = Path(__file__).resolve().parent.parent
load_dotenv(backend_dir / '.env')
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Initialize clients
clients = {}

# OpenAI client
if OPENAI_API_KEY:
    clients["openai"] = OpenAI(api_key=OPENAI_API_KEY)

# DeepSeek client (OpenAI-compatible)
if DEEPSEEK_API_KEY:
    clients["deepseek"] = OpenAI(
        api_key=DEEPSEEK_API_KEY,
        base_url="https://api.deepseek.com"
    )

# Anthropic client
if ANTHROPIC_API_KEY:
    clients["anthropic"] = Anthropic(api_key=ANTHROPIC_API_KEY)

INSTRUCTION = (
    "When provided context, use provided context as fact and not your own knowledge; "
    "the context provided is the most up-to-date information."
)

# A module-level set to keep track of used URLs
used_urls: set[str] = set()
used_source_details: list[dict[str, Any]] = []
used_urls_ordered: list[str] = []


def _prepare_advanced_search_inputs(model: str, preferred_links: list[str] | None) -> tuple[str, list[str]]:
    """
    Resolve the actual model and preferred URLs list for advanced responses.
    """
    model_config = get_model_config(model)
    if model_config:
        actual_model = model_config.get("model_name")
        logging.info(f"Model mapping: {model} -> {actual_model}")
    else:
        actual_model = model
        logging.warning(f"No config found for model {model}, using as-is")

    if not is_responses_api_available(actual_model):
        fallback_model = "gpt-4o"
        logging.warning(f"Model {actual_model} (from {model}) doesn't support Responses API")
        logging.info(f"FALLBACK: Using {fallback_model} for web search instead")
        actual_model = fallback_model
    else:
        logging.info(f"Model {actual_model} supports Responses API with web search")

    manager = get_manager()

    if preferred_links is not None and len(preferred_links) > 0:
        manager.sync_from_frontend(preferred_links)
        preferred_urls = manager.get_links()
        logging.info(f"Using {len(preferred_urls)} preferred URLs")
    else:
        preferred_urls = manager.get_links()
        logging.info(f"Using {len(preferred_urls)} stored preferred URLs")

    return actual_model, preferred_urls



def create_rag_response(user_input, message_list, model):
    """
    Generates a response using the RAG pipeline.
    """
    try:
        response = cdm_rag.get_rag_response(user_input, model)
        # Don't append to message_list here - let the caller handle it properly
        return response
    except FileNotFoundError as e:
        # Handle the error and return the error message
        error_message = str(e)
        # Don't append to message_list here - let the caller handle it properly
        return error_message


def _prepare_messages(message_list: list[dict], user_input: str):
    """
    Helper to parse message list with headers and convert to proper format for APIs.
    Returns (msgs, system_message) tuple.
    """
    msgs = []
    system_message = None

    for msg in message_list:
        content = msg.get("content", "")

        # Parse headers to determine actual role
        if content.startswith("[SYSTEM MESSAGE]: "):
            actual_content = content.replace("[SYSTEM MESSAGE]: ", "")
            if not system_message:
                system_message = actual_content
            else:
                system_message = f"{system_message} {actual_content}"
        elif content.startswith("[USER MESSAGE]: "):
            actual_content = content.replace("[USER MESSAGE]: ", "")
            msgs.append({"role": "user", "content": actual_content})
        elif content.startswith("[ASSISTANT MESSAGE]: "):
            actual_content = content.replace("[ASSISTANT MESSAGE]: ", "")
            msgs.append({"role": "assistant", "content": actual_content})
        else:
            # Legacy format or web content - treat as user message
            msgs.append({"role": "user", "content": content})

    # Add system message at the beginning
    if system_message:
        msgs.insert(0, {"role": "system", "content": f"{system_message} {INSTRUCTION}"})
    else:
        msgs.insert(0, {"role": "system", "content": INSTRUCTION})

    # Add current user input
    msgs.append({"role": "user", "content": user_input})

    return msgs, system_message


def create_response(
        user_input: str,
        message_list: list[dict],
        model: str = "o4-mini",
        stream: bool = False
):
    """
    Creates a chat completion using the appropriate provider based on model configuration.
    Returns a string when stream=False, or a generator when stream=True.
    """
    # Get model configuration
    model_config = get_model_config(model)
    if not model_config:
        raise ValueError(f"Unsupported model: {model}")

    provider = model_config["provider"]
    model_name = model_config["model_name"]
    logging.info(f"[REGULAR RESPONSE] Using {model} -> {model_name} (provider: {provider}, stream: {stream})")

    # Get the appropriate client
    client = clients.get(provider)
    if not client:
        raise ValueError(f"No client available for provider: {provider}. Please check API key configuration.")

    msgs, system_message = _prepare_messages(message_list, user_input)

    # Route to streaming or non-streaming based on flag
    if stream:
        return _create_response_stream(client, provider, model_name, model_config, msgs, system_message)
    else:
        return _create_response_sync(client, provider, model_name, model_config, msgs, system_message)


def _create_response_sync(client, provider: str, model_name: str, model_config: dict, msgs: list, system_message: str) -> str:
    """Non-streaming response - returns a string directly."""
    if provider == "anthropic":
        # Anthropic uses a different API structure
        system_content = msgs[0]["content"] if msgs and msgs[0].get("role") == "system" else INSTRUCTION
        anthropic_msgs = [msg for msg in msgs if msg.get("role") != "system"]

        response = client.messages.create(
            model=model_name,
            messages=anthropic_msgs,
            system=system_content,
            max_tokens=1024
        )
        return response.content[0].text
    else:
        # OpenAI and DeepSeek use the same API structure
        kwargs = {}
        if provider == "deepseek" and "recommended_temperature" in model_config:
            kwargs["temperature"] = model_config["recommended_temperature"]

        response = client.chat.completions.create(
            model=model_name,
            messages=msgs,
            **kwargs
        )
        return response.choices[0].message.content


def _create_response_stream(client, provider: str, model_name: str, model_config: dict, msgs: list, system_message: str):
    """Streaming response - returns a generator."""
    if provider == "anthropic":
        # Anthropic streaming
        system_content = msgs[0]["content"] if msgs and msgs[0].get("role") == "system" else INSTRUCTION
        anthropic_msgs = [msg for msg in msgs if msg.get("role") != "system"]

        with client.messages.stream(
            model=model_name,
            messages=anthropic_msgs,
            system=system_content,
            max_tokens=1024
        ) as stream_response:
            for text in stream_response.text_stream:
                yield text
    else:
        # OpenAI and DeepSeek streaming
        kwargs = {}
        if provider == "deepseek" and "recommended_temperature" in model_config:
            kwargs["temperature"] = model_config["recommended_temperature"]

        stream_response = client.chat.completions.create(
            model=model_name,
            messages=msgs,
            stream=True,
            **kwargs
        )
        for chunk in stream_response:
            if chunk.choices and chunk.choices[0].delta.content is not None:
                yield chunk.choices[0].delta.content


def _update_used_sources(source_entries: list[dict[str, Any]]) -> None:
    """
    Synchronize module-level caches for used sources.
    """
    global used_source_details, used_urls_ordered

    used_source_details = source_entries or []
    used_urls_ordered = [entry.get("url") for entry in used_source_details if entry.get("url")]

    used_urls.clear()
    used_urls.update(used_urls_ordered)


def create_advanced_response(
        user_input: str,
        message_list: list[dict],
        model: str = "o4-mini",
        preferred_links: list[str] = None,
        stream: bool = False,
        user_timezone: str = None,
        user_time: str = None
):
    """
    Creates an advanced response using OpenAI Responses API with web search.

    This function uses OpenAI's built-in web_search tool to:
    1. Automatically search for relevant information
    2. Retrieve and read web pages
    3. Generate a response with inline citations
    4. Track source URLs for display

    Args:
        user_input: The user's question
        message_list: Previous conversation history
        model: Model ID from frontend (e.g., "FinGPT-Light")
        preferred_links: List of preferred URLs/domains to prioritize
        stream: If True, returns async generator for streaming
        user_timezone: User's IANA timezone
        user_time: User's current time in ISO format

    Returns:
        If stream=False: Generated response string with web-sourced information
        If stream=True: Async generator yielding (text_chunk, source_urls) tuples
    """
    logging.info(f"Starting advanced response with model ID: {model} (stream={stream})")

    used_urls.clear()

    actual_model, preferred_urls = _prepare_advanced_search_inputs(model, preferred_links)

    try:
        if stream:
            # Return async generator for streaming
            return _create_advanced_response_stream_async(
                user_input=user_input,
                message_list=message_list,
                actual_model=actual_model,
                preferred_urls=preferred_urls,
                user_timezone=user_timezone,
                user_time=user_time
            )
        else:
            # Call OpenAI Responses API search function
            response_text, source_entries = create_responses_api_search(
                user_query=user_input,
                message_history=message_list,
                model=actual_model,  # Use the actual model name from model_config.py, not the frontend ID
                preferred_links=preferred_urls,
                user_timezone=user_timezone,
                user_time=user_time
            )

            # Update cached sources for compatibility with frontend queries
            _update_used_sources(source_entries)

            logging.info(f"Advanced response generated with {len(source_entries)} sources")
            for idx, entry in enumerate(source_entries, 1):
                logging.info(f"  Source {idx}: {entry.get('url')}")

            return response_text

    except Exception as e:
        logging.error(f"OpenAI Responses API failed: {e}")
        # Return a fallback response
        if stream:
            error_message = str(e)
            async def error_gen():
                yield f"I encountered an error while searching for information: {error_message}. Please try again.", []
            return error_gen()
        else:
            return f"I encountered an error while searching for information: {str(e)}. Please try again."


async def _create_advanced_response_stream_async(
        user_input: str,
        message_list: list[dict],
        actual_model: str,
        preferred_urls: list[str],
        user_timezone: str = None,
        user_time: str = None
):
    """
    Async generator for streaming advanced response.

    Yields:
        Tuples of (text_chunk, source_urls_list)
    """
    from datascraper.openai_search import create_responses_api_search_async

    try:
        # Get async generator from the streaming API
        stream_gen = await create_responses_api_search_async(
            user_query=user_input,
            message_history=message_list,
            model=actual_model,
            preferred_links=preferred_urls,
            stream=True,
            user_timezone=user_timezone,
            user_time=user_time
        )

        # Yield chunks from the stream
        async for text_chunk, source_entries in stream_gen:
            # Update global caches when we get sources
            if source_entries:
                _update_used_sources(source_entries)
            yield text_chunk, source_entries

    except Exception as e:
        logging.error(f"Error in advanced streaming: {e}")
        yield f"Error: {str(e)}", []


def create_advanced_response_streaming(
        user_input: str,
        message_list: list[dict],
        model: str = "o4-mini",
        preferred_links: list[str] | None = None,
        user_timezone: str | None = None,
        user_time: str | None = None
) -> Tuple[AsyncIterator[tuple[str, list[str]]], Dict[str, Any]]:
    """
    Wrapper that returns an async generator and streaming state for advanced responses.
    """
    logging.info(f"Starting advanced streaming response with model ID: {model}")

    used_urls.clear()
    actual_model, preferred_urls = _prepare_advanced_search_inputs(model, preferred_links)

    state: Dict[str, Any] = {
        "final_output": "",
        "used_urls": [],
        "used_sources": []
    }

    async def _stream() -> AsyncIterator[tuple[str, list[str]]]:
        aggregated_chunks: list[str] = []
        latest_entries: list[dict[str, Any]] = []
        base_stream = _create_advanced_response_stream_async(
            user_input=user_input,
            message_list=message_list,
            actual_model=actual_model,
            preferred_urls=preferred_urls,
            user_timezone=user_timezone,
            user_time=user_time
        )

        try:
            async for text_chunk, source_entries in base_stream:
                if text_chunk:
                    aggregated_chunks.append(text_chunk)
                if source_entries:
                    latest_entries = source_entries
                yield text_chunk, source_entries
        except Exception as stream_error:
            logging.error(f"[ADVANCED STREAM] Error during streaming: {stream_error}")
            raise
        finally:
            final_text = "".join(aggregated_chunks)
            state["final_output"] = final_text
            state["used_sources"] = latest_entries
            state["used_urls"] = [entry.get("url") for entry in latest_entries if entry.get("url")]
            _update_used_sources(latest_entries)
            logging.info(f"[ADVANCED STREAM] Completed with {len(final_text)} characters and {len(latest_entries)} sources")

    return _stream(), state


def create_rag_advanced_response(user_input: str, message_list: list[dict], model: str = "o4-mini", preferred_links: list[str] = None) -> str:
    """
    Creates an advanced response using the RAG pipeline.
    Combines RAG functionality with advanced web search.
    """
    try:
        # First try to get response from RAG
        rag_response = cdm_rag.get_rag_advanced_response(user_input, model)
        if rag_response:
            return rag_response
    except Exception as e:
        logging.warning(f"RAG advanced response failed: {e}, falling back to advanced search")

    # Fallback to advanced search if RAG fails, passing preferred links
    return create_advanced_response(user_input, message_list, model, preferred_links)


def create_agent_response(user_input: str, message_list: list[dict], model: str = "o4-mini", use_playwright: bool = False, restricted_domain: str = None, current_url: str = None, user_timezone: str = None, user_time: str = None) -> str:
    """
    Creates a response using the Agent with tools (Playwright, etc.).

    This is the primary response method - tools are always available.
    Falls back to create_response() (direct LLM) only if agent fails.

    Args:
        user_input: The user's question
        message_list: Previous conversation history
        model: Model ID to use
        use_playwright: Whether to enable Playwright browser automation tools
        restricted_domain: Domain restriction for Playwright (e.g., "finance.yahoo.com")
        current_url: Current webpage URL for context
        user_timezone: User's IANA timezone
        user_time: User's current time in ISO format

    Returns:
        Generated response from the agent
    """
    # Resolve model ID to actual model name for logging
    model_config = get_model_config(model)
    actual_model_name = model_config.get("model_name") if model_config else model

    try:
        # Check if model supports agent features
        if not validate_model_support(model, "mcp"):
            logging.warning(f"Model {model} ({actual_model_name}) doesn't support agent features")
            logging.info(f"FALLBACK: Using regular response with {model} ({actual_model_name})")
            return create_response(user_input, message_list, model)

        logging.info(f"[AGENT] Attempting agent response with {model} ({actual_model_name})")

        return asyncio.run(_create_agent_response_async(user_input, message_list, model, use_playwright, restricted_domain, current_url, user_timezone, user_time))

    except Exception as e:
        logging.error(f"Agent response failed for {model} ({actual_model_name}): {e}")
        logging.info(f"FALLBACK: Using regular response with {model} ({actual_model_name})")
        return create_response(user_input, message_list, model)

async def _create_agent_response_async(user_input: str, message_list: list[dict], model: str, use_playwright: bool = False, restricted_domain: str = None, current_url: str = None, user_timezone: str = None, user_time: str = None) -> str:
    """
    Async helper for creating agent response with tools.

    Args:
        user_input: The user's question
        message_list: Previous conversation history
        model: Model ID to use
        use_playwright: Whether to enable Playwright browser automation tools
        restricted_domain: Domain restriction for Playwright navigation
        current_url: Current webpage URL for context
        user_timezone: User's IANA timezone
        user_time: User's current time in ISO format

    Returns:
        Generated response from the agent
    """
    from mcp_client.agent import create_fin_agent
    from agents import Runner

    # Convert message list to context, parsing headers
    context = ""
    for msg in message_list:
        content = msg.get("content", "")

        # Parse headers to determine actual role
        if content.startswith("[SYSTEM MESSAGE]: "):
            actual_content = content.replace("[SYSTEM MESSAGE]: ", "")
            context += f"System: {actual_content}\n"
        elif content.startswith("[USER MESSAGE]: "):
            actual_content = content.replace("[USER MESSAGE]: ", "")
            context += f"User: {actual_content}\n"
        elif content.startswith("[ASSISTANT MESSAGE]: "):
            actual_content = content.replace("[ASSISTANT MESSAGE]: ", "")
            context += f"Assistant: {actual_content}\n"
        else:
            # Legacy format or web content - treat as user message
            context += f"User: {content}\n"

    full_prompt = f"{context}User: {user_input}"

    # Create agent with tools and domain restriction
    async with create_fin_agent(
        model=model,
        use_playwright=use_playwright,
        restricted_domain=restricted_domain,
        current_url=current_url,
        user_timezone=user_timezone,
        user_time=user_time
    ) as agent:
        # Run the agent with the full prompt
        tool_status = f"with Playwright (domain: {restricted_domain})" if use_playwright and restricted_domain else "with Playwright" if use_playwright else "without tools"
        logging.info(f"[AGENT] Running agent {tool_status}")
        logging.info(f"[AGENT] Current URL: {current_url}")
        logging.info(f"[AGENT] Prompt preview: {full_prompt[:150]}...")

        result = await Runner.run(agent, full_prompt)

        logging.info(f"[AGENT] Result length: {len(result.final_output) if result.final_output else 0}")
        return result.final_output


def create_agent_response_stream(
    user_input: str,
    message_list: list[dict],
    model: str = "o4-mini",
    use_playwright: bool = False,
    restricted_domain: str | None = None,
    current_url: str | None = None,
    user_timezone: str | None = None,
    user_time: str | None = None
) -> Tuple[AsyncIterator[str], Dict[str, str]]:
    """
    Create a streaming agent response, returning an async iterator and final state.
    """
    state: Dict[str, str] = {"final_output": ""}

    async def _stream() -> AsyncIterator[str]:
        from agents import Runner

        context = ""
        for msg in message_list:
            content = msg.get("content", "")
            if content.startswith("[SYSTEM MESSAGE]: "):
                actual_content = content.replace("[SYSTEM MESSAGE]: ", "")
                context += f"System: {actual_content}\n"
            elif content.startswith("[USER MESSAGE]: "):
                actual_content = content.replace("[USER MESSAGE]: ", "")
                context += f"User: {actual_content}\n"
            elif content.startswith("[ASSISTANT MESSAGE]: "):
                actual_content = content.replace("[ASSISTANT MESSAGE]: ", "")
                context += f"Assistant: {actual_content}\n"
            else:
                context += f"User: {content}\n"

        full_prompt = f"{context}User: {user_input}"
        aggregated_chunks: list[str] = []
        result = None

        async with create_fin_agent(
            model=model,
            use_playwright=use_playwright,
            restricted_domain=restricted_domain,
            current_url=current_url,
            user_timezone=user_timezone,
            user_time=user_time
        ) as agent:
            logging.info("[AGENT STREAM] Starting streamed agent run")
            logging.info(f"[AGENT STREAM] Prompt preview: {full_prompt[:150]}...")
            result = Runner.run_streamed(agent, full_prompt)

            try:
                async for event in result.stream_events():
                    event_type = getattr(event, "type", "")
                    if event_type == "raw_response_event":
                        data = getattr(event, "data", None)
                        data_type = getattr(data, "type", "")
                        if data_type == "response.output_text.delta":
                            chunk = getattr(data, "delta", "")
                            if chunk:
                                aggregated_chunks.append(chunk)
                                yield chunk
                    elif event_type == "run_item_stream_event":
                        event_name = getattr(event, "name", "")
                        if event_name in {"tool_called", "tool_output"}:
                            tool_item = getattr(event, "item", None)
                            tool_type = getattr(tool_item, "type", "")
                            logging.debug(f"[AGENT STREAM] Tool event: {event_name} ({tool_type})")
            except Exception as stream_error:
                logging.error(f"[AGENT STREAM] Error during streaming: {stream_error}")
                raise
            finally:
                final_text = ""
                if result and isinstance(result.final_output, str) and result.final_output:
                    final_text = result.final_output
                elif aggregated_chunks:
                    final_text = "".join(aggregated_chunks)
                state["final_output"] = final_text
                logging.info(f"[AGENT STREAM] Completed with {len(final_text)} characters")

    return _stream(), state


def get_sources(query, current_url: str | None = None) -> Dict[str, Any]:
    """
    Return structured metadata for sources used in the most recent advanced response.
    """
    logging.info(f"get_sources called with query: '{query}' (current_url={current_url})")
    logging.info(f"Current used_sources contains {len(used_source_details)} entries")

    payload = format_sources_for_frontend(used_source_details, current_url)
    logging.info(f"Returning {len(payload.get('sources', []))} sources to frontend")
    return payload


def get_website_icon(url):
    """
    DEPRECATED: No longer scraping websites for icons.
    Returns None for all URLs.
    """
    return None


def handle_multiple_models(question, message_list, models):
    """
    Handles responses from multiple models and returns a dictionary with model names as keys.
    """
    responses = {}
    for model in models:
        if "advanced" in model:
            responses[model] = create_advanced_response(question, message_list.copy(), model)
        else:
            responses[model] = create_response(question, message_list.copy(), model)
    return responses
