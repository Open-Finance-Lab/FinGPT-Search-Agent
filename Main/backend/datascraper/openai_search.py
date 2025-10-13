"""
OpenAI Responses API integration for web search functionality.

This module replaces the custom DuckDuckGo + BeautifulSoup scraping
with OpenAI's built-in web_search tool from the Responses API.
"""

import os
import logging
import asyncio
from typing import List, Dict, Tuple, Optional, Any
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


def extract_citations_from_response(response) -> List[Dict[str, str]]:
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
                                            'title': getattr(annotation, 'title', ''),
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
    preferred_links: List[str] = None
) -> Tuple[str, List[str]]:
    """
    Async version: Create a response using OpenAI Responses API with web search.

    Args:
        user_query: The user's question
        message_history: Previous conversation messages
        model: OpenAI model to use (must support Responses API)
        preferred_links: List of preferred URLs/domains to search

    Returns:
        Tuple of (response_text, list_of_source_urls)
    """
    try:
        # Extract domains from preferred links
        preferred_domains = []
        if preferred_links:
            for link in preferred_links:
                # Extract domain from URL
                from urllib.parse import urlparse
                domain = urlparse(link).netloc
                if domain and domain not in preferred_domains:
                    preferred_domains.append(domain)

        # Prepare enhanced prompt
        enhanced_prompt = prepare_search_prompt(user_query, preferred_domains)

        # Combine system instructions with the user prompt (Responses API doesn't accept system parameter)
        combined_input = (
            "Instructions: You are a helpful assistant with access to web search. "
            "Always search for current information when answering questions. "
            "Cite your sources inline and provide comprehensive, accurate answers. "
            "Focus on factual information from reputable sources.\n\n"
            f"{enhanced_prompt}"
        )

        logger.info(f"Calling OpenAI Responses API with model: {model}")
        logger.info(f"Web search enabled for query: {user_query[:100]}...")

        # Call the Responses API with web_search tool (no system parameter)
        response = await async_client.responses.create(
            model=model,
            input=combined_input,
            tools=[{"type": "web_search"}],  # Enable web search
            tool_choice="auto"  # Let model decide when to search
            # Note: modalities parameter removed - not needed for basic web search per docs
        )

        # Extract the response text
        # Based on documentation, the response structure is simpler
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
        source_urls = [c['url'] for c in citations if c['type'] == 'url_citation']

        # Remove duplicates while preserving order
        seen = set()
        unique_urls = []
        for url in source_urls:
            if url not in seen:
                seen.add(url)
                unique_urls.append(url)

        logger.info(f"Response generated successfully with {len(unique_urls)} unique source URLs")

        return response_text, unique_urls

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


def create_responses_api_search(
    user_query: str,
    message_history: List[Dict[str, str]],
    model: str = "gpt-4o-mini",
    preferred_links: List[str] = None
) -> Tuple[str, List[str]]:
    """
    Synchronous wrapper for create_responses_api_search_async.

    Args:
        user_query: The user's question
        message_history: Previous conversation messages
        model: OpenAI model to use
        preferred_links: List of preferred URLs/domains

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
                create_responses_api_search_async(user_query, message_history, model, preferred_links)
            )
            return asyncio.run_coroutine_threadsafe(task, loop).result()
        else:
            # If no loop is running, use asyncio.run
            return asyncio.run(
                create_responses_api_search_async(user_query, message_history, model, preferred_links)
            )
    except RuntimeError:
        # No event loop exists, create one
        return asyncio.run(
            create_responses_api_search_async(user_query, message_history, model, preferred_links)
        )


def format_sources_for_frontend(source_urls: List[str]) -> List[str]:
    """
    Format source URLs for frontend display.
    Maintains compatibility with existing frontend expectations.

    Args:
        source_urls: List of source URLs from citations

    Returns:
        List of URLs formatted for frontend
    """
    # The frontend expects a simple list of URLs
    # We can enhance this later to include titles if needed
    return source_urls


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