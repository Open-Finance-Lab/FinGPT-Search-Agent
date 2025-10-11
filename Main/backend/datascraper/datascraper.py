import time
import requests
import os
import re
import logging
import asyncio
# import torch

from dotenv import load_dotenv
from bs4 import BeautifulSoup

from openai import OpenAI
from anthropic import Anthropic

from urllib.parse import urljoin
# from transformers import AutoTokenizer, AutoModelForCausalLM
# from accelerate import init_empty_weights, load_checkpoint_and_dispatch

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

# Load .env from the backend root directory
from pathlib import Path
backend_dir = Path(__file__).resolve().parent.parent
load_dotenv(backend_dir / '.env')
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

req_headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/115.0.0.0 Safari/537.36"
}

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

# Helper
def remove_duplicate_sentences(text):
    """Remove duplicate consecutive sentences that often appear in scraped content."""
    sentences = re.split(r'(?<=[.!?])\s+', text)
    unique_sentences = []
    for sentence in sentences:
        if not unique_sentences or sentence != unique_sentences[-1]:
            unique_sentences.append(sentence)
    return ' '.join(unique_sentences)

def duckduckgo_search(query, num_results=10):
    """
    Primary search using DuckDuckGo HTML scraping.
    Returns a list of clean URLs from search results.
    """
    try:
        import urllib.parse
        encoded_query = urllib.parse.quote_plus(query)
        ddg_url = f"https://html.duckduckgo.com/html/?q={encoded_query}"

        # More comprehensive headers to avoid bot detection
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Cache-Control': 'max-age=0'
        }

        # Add a small delay to avoid rate limiting
        time.sleep(0.5)

        logging.info(f"Searching DuckDuckGo for: '{query}'")
        logging.info(f"URL: {ddg_url}")

        response = requests.get(ddg_url, headers=headers, timeout=15, allow_redirects=True)

        logging.info(f"Response status code: {response.status_code}")

        if response.status_code == 202:
            logging.warning(f"DuckDuckGo returned 202 (rate limited or bot detection). Waiting 2 seconds and retrying...")
            time.sleep(2)
            response = requests.get(ddg_url, headers=headers, timeout=15, allow_redirects=True)
            logging.info(f"Retry response status code: {response.status_code}")

        if response.status_code != 200:
            logging.error(f"DuckDuckGo search failed with status code: {response.status_code}")
            logging.error(f"Response content preview: {response.text[:500]}")
            return []

        soup = BeautifulSoup(response.text, 'html.parser')
        results = []

        # Extract search result URLs, ensuring they're clean external links
        for result in soup.find_all('a', class_='result__a', limit=num_results):
            url = result.get('href')
            if url and url.startswith('http'):
                # Filter out any DuckDuckGo internal URLs
                if 'duckduckgo.com' not in url:
                    results.append(url)
                    logging.debug(f"Found result URL: {url}")

        logging.info(f"DuckDuckGo search returned {len(results)} URLs")

        if len(results) == 0:
            logging.warning("No results found. Response HTML preview:")
            logging.warning(response.text[:1000])

        return results
    except Exception as e:
        logging.error(f"DuckDuckGo search failed: {e}")
        return []

def data_scrape(url, timeout=10, rate_limit=1):
    """
    Scrapes data from the given URL and returns a structured dictionary.
    Includes metadata extraction, duplicate removal, and rate limiting.
    """
    try:
        # Rate limiting to prevent rapid-fire requests
        time.sleep(rate_limit)
        start_time = time.time()
        response = requests.get(url, timeout=timeout, headers=req_headers)
        elapsed_time = time.time() - start_time

        if response.status_code != 200:
            logging.error(f"Failed to retrieve page ({response.status_code}): {url}")
            return {'url': url, 'status': 'error', 'error': f"Status code {response.status_code}"}

        logging.info(f"Successful response: {url} (Elapsed time: {elapsed_time:.2f}s)")
        soup = BeautifulSoup(response.text, 'html.parser')

        # Extract metadata: title and meta description
        metadata = {}
        if soup.title and soup.title.string:
            metadata['title'] = soup.title.string.strip()
        meta_desc = soup.find('meta', attrs={'name': 'description'})
        if meta_desc and meta_desc.get('content'):
            metadata['description'] = meta_desc.get('content').strip()

        # Remove non-content elements
        for element in soup.find_all(['script', 'style', 'nav', 'footer', 'aside']):
            element.decompose()

        main_content = ""
        # Try to find main content containers
        content_elements = soup.find_all(['article', 'main', 'div', 'section'],
                                         class_=lambda x: x and any(term in str(x).lower()
                                                                    for term in ['content', 'article', 'main', 'post', 'entry']))
        if content_elements:
            for element in content_elements:
                for tag in element.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'p']):
                    text = tag.get_text(strip=True)
                    if text:
                        main_content += (text + "\n") if tag.name.startswith('h') else (text + " ")

        # Fallback: If no content found via containers, scrape all headings and paragraphs
        if not main_content:
            for tag in soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'p']):
                text = tag.get_text(strip=True)
                if text and (tag.name.startswith('h') or len(text) > 50):
                    main_content += (text + "\n") if tag.name.startswith('h') else (text + " ")

        # Final fallback: extract all text if little content is gathered
        if not main_content or len(main_content) < 50:
            all_text = soup.get_text(separator=' ', strip=True)
            main_content = ' '.join(all_text.split())

        # Clean duplicate consecutive sentences
        cleaned_content = remove_duplicate_sentences(main_content)

        return {
            'url': url,
            'status': 'success',
            'metadata': metadata,
            'content': cleaned_content
        }

    except requests.exceptions.Timeout:
        logging.error(f"Request timed out after {timeout} seconds for URL: {url}")
        return {'url': url, 'status': 'error', 'error': f"Timeout after {timeout} seconds"}
    except Exception as e:
        logging.error(f"An error occurred for URL {url}: {str(e)}")
        return {'url': url, 'status': 'error', 'error': str(e)}


def search_preferred_urls(preferred_urls, max_urls=None):
    """
    Scrapes provided preferred URLs without keyword filtering.

    Args:
        preferred_urls: List of URLs to scrape
        max_urls: Maximum number of URLs to scrape (None = all)

    Returns:
        List of scraped information dictionaries
    """
    if not preferred_urls:
        logging.info("No preferred URLs to search")
        return []

    if max_urls:
        preferred_urls = preferred_urls[:max_urls]

    info_list = []
    for url in preferred_urls:
        info = data_scrape(url)
        logging.info(f"Scraped preferred URL {url}: status={info.get('status')}")
        if info.get('status') == 'success':
            info_list.append(info)
        else:
            logging.warning(f"Failed to scrape URL: {url}, error: {info.get('error')}")
    return info_list


def extract_search_keywords(user_query: str, model: str = "o4-mini") -> str:
    """
    Uses an LLM to extract optimal search keywords from a user query.

    Args:
        user_query: The user's question or prompt
        model: Model to use for keyword extraction

    Returns:
        Optimized search keywords as a string
    """
    try:
        model_config = get_model_config(model)
        if not model_config:
            logging.warning(f"Model {model} not found, using query as-is")
            return user_query

        provider = model_config["provider"]
        model_name = model_config["model_name"]
        client = clients.get(provider)

        if not client:
            logging.warning(f"No client for {provider}, using query as-is")
            return user_query

        extraction_prompt = (
            "You are a search keyword extraction assistant. "
            "Given a user's question or request, extract the most relevant keywords for a web search. "
            "Return ONLY the keywords, nothing else. Keep it concise (6 words maximum). "
            "Focus on the core topic, entities, and key terms.\n\n"
            f"User query: {user_query}\n\n"
            "Search keywords:"
        )

        if provider == "anthropic":
            response = client.messages.create(
                model=model_name,
                messages=[{"role": "user", "content": extraction_prompt}],
                max_tokens=50
            )
            keywords = response.content[0].text.strip()
        else:
            kwargs = {}
            if provider == "deepseek" and "recommended_temperature" in model_config:
                kwargs["temperature"] = model_config["recommended_temperature"]

            response = client.chat.completions.create(
                model=model_name,
                messages=[{"role": "user", "content": extraction_prompt}],
                **kwargs
            )
            keywords = response.choices[0].message.content.strip()

        logging.info(f"Extracted keywords from '{user_query}': '{keywords}'")
        return keywords

    except Exception as e:
        logging.error(f"Error extracting keywords: {e}, using query as-is")
        return user_query


def create_rag_response(user_input, message_list, model):
    """
    Generates a response using the RAG pipeline.
    """
    try:
        response = cdm_rag.get_rag_response(user_input, model)
        message_list.append({"role": "user", "content": response})
        return response
    except FileNotFoundError as e:
        # Handle the error and return the error message
        error_message = str(e)
        message_list.append({"role": "user", "content": error_message})
        return error_message


def create_response(
        user_input: str,
        message_list: list[dict],
        model: str = "o4-mini"
) -> str:
    """
    Creates a chat completion using the appropriate provider based on model configuration.
    """
    # Get model configuration
    model_config = get_model_config(model)
    if not model_config:
        raise ValueError(f"Unsupported model: {model}")
    
    provider = model_config["provider"]
    model_name = model_config["model_name"]
    
    # Get the appropriate client
    client = clients.get(provider)
    if not client:
        raise ValueError(f"No client available for provider: {provider}. Please check API key configuration.")
    
    # Prepare messages
    msgs = [msg for msg in message_list if msg.get("role") != "system"]
    msgs.insert(0, {"role": "system", "content": INSTRUCTION})
    msgs.append({"role": "user", "content": user_input})
    
    # Provider-specific handling
    if provider == "anthropic":
        # Anthropic uses a different API structure
        response = client.messages.create(
            model=model_name,
            messages=msgs[1:],  # Anthropic doesn't use system messages the same way
            system=INSTRUCTION,  # System message as separate parameter
            max_tokens=1024
        )
        return response.content[0].text
    else:
        # OpenAI and DeepSeek use the same API structure
        # Handle DeepSeek temperature recommendations
        kwargs = {}
        if provider == "deepseek" and "recommended_temperature" in model_config:
            kwargs["temperature"] = model_config["recommended_temperature"]
        
        response = client.chat.completions.create(
            model=model_name,
            messages=msgs,
            **kwargs
        )
        return response.choices[0].message.content


def create_advanced_response(
        user_input: str,
        message_list: list[dict],
        model: str = "o4-mini",
        preferred_links: list[str] = None
) -> str:
    """
    Creates an advanced response by searching and scraping web content using DuckDuckGo.

    Search Strategy:
    1. Search preferred URLs first (if any provided)
    2. Use DuckDuckGo to find additional relevant URLs
    3. Scrape and process at least 5 URLs total for context
    4. Generate response using the gathered web content
    """
    logging.info("Starting advanced response creation...")

    # Clear any previous used URLs
    used_urls.clear()
    context_messages: list[str] = []

    TARGET_LINKS = 5

    # Get the preferred links manager
    manager = get_manager()

    # Sync and get preferred links
    if preferred_links is not None and len(preferred_links) > 0:
        # Frontend provided links - sync them to storage (which also deduplicates)
        manager.sync_from_frontend(preferred_links)
        # Get the deduplicated links from the manager
        preferred_urls = manager.get_links()
        logging.info(f"Synced {len(preferred_links)} links from frontend, using {len(preferred_urls)} deduplicated links")
    else:
        # No frontend links - use stored ones
        preferred_urls = manager.get_links()
        logging.info(f"Using {len(preferred_urls)} preferred links from storage")

    num_preferred = len(preferred_urls)
    logging.info(f"Found {num_preferred} preferred URLs")

    # Search preferred URLs first (if any)
    if num_preferred > 0:
        logging.info(f"Scraping {num_preferred} preferred URLs...")
        preferred_info_list = search_preferred_urls(preferred_urls)

        for info in preferred_info_list:
            url = info['url']
            content = info.get('content', '')
            content_length = len(content)

            # Check if content has at least 50 characters
            if content_length < 50:
                logging.info(f"Skipping preferred URL {url} (content too short: {content_length} chars < 50)")
                continue

            used_urls.add(url)
            meta = info.get('metadata', {})
            combined = (
                f"URL: {url}\n"
                f"Title: {meta.get('title', '')}\n"
                f"Description: {meta.get('description', '')}\n"
                f"Content: {content}"
            )
            context_messages.append(combined)
            logging.info(f"Added preferred URL to context: {url} (content: {content_length} chars)")

    # Determine how many additional links to search
    links_found = len(context_messages)
    additional_needed = max(0, TARGET_LINKS - links_found)

    # Search for additional links using DuckDuckGo
    if additional_needed > 0:
        logging.info(f"Need {additional_needed} more links. Searching via DuckDuckGo...")

        # Extract optimized search keywords using LLM
        logging.info("Extracting search keywords via LLM...")
        search_query = extract_search_keywords(user_input, model)
        logging.info(f"Using keywords: '{search_query}'")

        # Perform DuckDuckGo search
        try:
            links_scraped = 0
            url_index = 0

            # Search DuckDuckGo - request extra results to ensure we get enough valid ones
            logging.info(f"Searching DuckDuckGo with query: '{search_query}'")
            logging.info(f"Requesting {additional_needed + 5} results to ensure sufficient valid URLs...")

            search_urls = duckduckgo_search(search_query, num_results=additional_needed + 5)

            logging.info(f"DuckDuckGo returned {len(search_urls)} URLs")
            for idx, url in enumerate(search_urls, 1):
                logging.info(f"  [{idx}] {url}")

            # Scrape each URL from search results
            for url in search_urls:
                url_index += 1

                # Skip if already scraped from preferred URLs
                if url in used_urls:
                    logging.info(f"[{url_index}/{len(search_urls)}] Skipping {url} (already scraped from preferred URLs)")
                    continue

                logging.info(f"[{url_index}/{len(search_urls)}] Fetching {url}...")

                try:
                    info = data_scrape(url)
                    content = info.get('content', '')
                    content_length = len(content)

                    logging.info(f"  -> Status: {info.get('status')}, Content length: {content_length} chars")

                    if info.get('status') == 'success':
                        # Check if content has at least 50 characters
                        if content_length < 50:
                            logging.info(f"  -> ✗ SKIPPED (content too short: {content_length} chars < 50)")
                        else:
                            # Accept successful fetch with sufficient content
                            used_urls.add(info['url'])
                            meta = info.get('metadata', {})
                            combined = (
                                f"URL: {info['url']}\n"
                                f"Title: {meta.get('title', '')}\n"
                                f"Description: {meta.get('description', '')}\n"
                                f"Content: {content}"
                            )
                            context_messages.append(combined)
                            links_scraped += 1
                            logging.info(f"  -> ✓ ADDED to context (total sources: {len(context_messages)})")

                            # Stop if we've reached our target
                            if links_scraped >= additional_needed:
                                logging.info(f"Reached target of {additional_needed} additional links")
                                break
                    else:
                        logging.info(f"  -> ✗ FAILED ({info.get('error', 'unknown error')})")

                except Exception as e:
                    logging.error(f"  -> ✗ EXCEPTION: {e}")
                    continue

        except Exception as e:
            logging.error(f"DuckDuckGo search failed: {e}")
            if not context_messages:
                # If no context at all, raise error
                raise RuntimeError(f"Failed to gather any search results: {e}")

    logging.info(f"Gathered {len(context_messages)} sources for advanced response")

    # Get model configuration
    model_config = get_model_config(model)
    if not model_config:
        raise ValueError(f"Unsupported model: {model}")
    
    provider = model_config["provider"]
    model_name = model_config["model_name"]
    
    # Get the appropriate client
    client = clients.get(provider)
    if not client:
        raise ValueError(f"No client available for provider: {provider}. Please check API key configuration.")
    
    # construct messages
    msgs = [msg for msg in message_list if msg.get('role') != 'system']
    msgs.insert(0, {"role": "system", "content": INSTRUCTION})
    for snippet in context_messages:
        msgs.append({"role": "user", "content": snippet})
    msgs.append({"role": "user", "content": user_input})

    # Provider-specific handling
    if provider == "anthropic":
        # Anthropic uses a different API structure
        response = client.messages.create(
            model=model_name,
            messages=msgs[1:],  # Anthropic doesn't use system messages the same way
            system=INSTRUCTION,  # System message as separate parameter
            max_tokens=4096  # Longer for advanced responses
        )
        answer = response.content[0].text
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
        answer = response.choices[0].message.content
    
    logging.info(f"Generated advanced answer: {answer}")
    return answer


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


def create_mcp_response(user_input: str, message_list: list[dict], model: str = "o4-mini") -> str:
    """
    Creates a response using the MCP-enabled Agent.
    """
    try:
        # Check if model supports MCP
        if not validate_model_support(model, "mcp"):
            logging.warning(f"Model {model} doesn't support MCP, falling back to regular response")
            return create_response(user_input, message_list, model)
        
        # Run the MCP agent asynchronously
        return asyncio.run(_create_mcp_response_async(user_input, message_list, model))
        
    except Exception as e:
        logging.error(f"MCP response failed: {e}, falling back to regular response")
        return create_response(user_input, message_list, model)

async def _create_mcp_response_async(user_input: str, message_list: list[dict], model: str) -> str:
    """
    Async helper for creating MCP response.
    """
    from mcp_client.agent import create_fin_agent
    from agents import Runner
    
    # Convert message list to context
    context = ""
    for msg in message_list:
        if msg.get("role") == "user":
            context += f"User: {msg.get('content', '')}\n"
        elif msg.get("role") == "assistant":
            context += f"Assistant: {msg.get('content', '')}\n"
    
    # Combine context with current input
    full_prompt = f"{context}User: {user_input}"
    
    # Create MCP agent using async context manager
    async with create_fin_agent(model) as agent:
        # Run the agent with the full prompt
        logging.info(f"[MCP DEBUG] Running agent with prompt: {full_prompt}")
        result = await Runner.run(agent, full_prompt)
        logging.info(f"[MCP DEBUG] Runner result: {result}")
        logging.info(f"[MCP DEBUG] Result type: {type(result)}")
        logging.info(f"[MCP DEBUG] Result final_output: {result.final_output}")
        return result.final_output


def get_sources(query):
    """
    Returns the URLs that were used in the most recent 'create_advanced_response' call,
    along with their icons or placeholders for front-end display.
    """
    logging.info(f"get_sources called with query: '{query}'")
    logging.info(f"Current used_urls contains {len(used_urls)} URLs:")
    for idx, url in enumerate(used_urls, 1):
        logging.info(f"  [{idx}] {url}")

    sources = [(url, get_website_icon(url)) for url in used_urls]
    logging.info(f"Returning {len(sources)} source URLs with icons")
    return sources


def get_website_icon(url):
    """
    Retrieves the website icon (favicon) for a given URL.
    """
    response = requests.get(url, headers=req_headers)
    soup = BeautifulSoup(response.text, 'html.parser')
    favicon_tag = soup.find('link', rel='icon') or soup.find('link', rel='shortcut icon')
    if favicon_tag:
        favicon_url = favicon_tag.get('href')
        favicon_url = urljoin(url, favicon_url)
        return favicon_url
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
