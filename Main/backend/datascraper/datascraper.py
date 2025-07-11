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

from googlesearch import search
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

# Helper
def keyword_match(query, text):
    """
    Returns True if a sufficient number of significant words from the query appear in the text.
    Considers words longer than 3 characters as significant.
    """
    words = [w for w in query.lower().split() if len(w) > 3]
    if not words:
        return query.lower() in text.lower()
    count = sum(1 for w in words if w in text.lower())
    # Require at least one word or half of the significant words (whichever is higher) to match.
    return count >= max(1, len(words) // 2)

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
        if not main_content or len(main_content) < 200:
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


def get_preferred_urls():
    """
    Reads user-preferred URLs from a file and returns them as a list.
    """
    file_path = 'preferred_urls.txt'
    preferred_urls = []
    if os.path.exists(file_path):
        with open(file_path, 'r') as file:
            preferred_urls = [line.strip() for line in file.readlines()]
    logging.info(f"Preferred URLs: {preferred_urls}")
    return preferred_urls


def search_preferred_urls(query):
    """
    Searches within user-preferred URLs using the provided query.
    Only returns info dictionaries where the scraped content matches the query keywords.
    """
    preferred_urls = get_preferred_urls()
    info_list = []
    for url in preferred_urls:
        info = data_scrape(url)
        logging.info(f"Scraped preferred URL {url}: {info}")
        if info.get('status') == 'success' and keyword_match(query, info.get('content', '')):
            info_list.append(info)
        else:
            logging.info(f"Keyword '{query}' not sufficiently found in URL: {url}")
    return info_list


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
        model: str = "o4-mini"
) -> str:
    """
    Creates an advanced response by searching user-preferred URLs first, then
    falling back to a general web search if needed. Appends metadata and content
    from scraped results, and returns the final assistant reply.
    """
    logging.info("Starting advanced response creation...")

    # clear any previous used URLs
    used_urls.clear()
    context_messages: list[str] = []

    # Search in preferred URLs
    logging.info("Searching user-preferred URLs...")
    preferred_info_list = search_preferred_urls(user_input)
    for info in preferred_info_list:
        if info.get('status') == 'success' and keyword_match(user_input, info.get('content', '')):
            url = info['url']
            used_urls.add(url)
            meta = info.get('metadata', {})
            combined = (
                f"URL: {url}\n"
                f"Title: {meta.get('title', '')}\n"
                f"Description: {meta.get('description', '')}\n"
                f"Content: {info.get('content', '')}"
            )
            context_messages.append(combined)

    # Fallback to general web search
    if not context_messages:
        logging.info("No preferred results; falling back to general web search.")
        for url in search(user_input, num=5, stop=5, pause=0):
            info = data_scrape(url)
            if info.get('status') == 'success' and keyword_match(user_input, info.get('content', '')):
                used_urls.add(info['url'])
                meta = info.get('metadata', {})
                combined = (
                    f"URL: {info['url']}\n"
                    f"Title: {meta.get('title', '')}\n"
                    f"Description: {meta.get('description', '')}\n"
                    f"Content: {info.get('content', '')}"
                )
                context_messages.append(combined)
            else:
                logging.info(f"Failed for URL: {info.get('url')}")

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


def create_rag_advanced_response(user_input: str, message_list: list[dict], model: str = "o4-mini") -> str:
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
    
    # Fallback to advanced search if RAG fails
    return create_advanced_response(user_input, message_list, model)


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
    sources = [(url, get_website_icon(url)) for url in used_urls]
    print("DEBUG: Sources List:", sources)  # DEBUG
    return [(url, get_website_icon(url)) for url in used_urls]


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


# def search_websites_with_keyword(keyword):
#     """
#     Searches the web using Google and prioritizes user-preferred URLs.
#     """
#     # First, search within preferred URLs
#     message_list = search_preferred_urls(keyword)
#
#     # If no relevant information found in preferred URLs, fall back to Google search
#     if not message_list:
#         search_query = f"intitle:{keyword}"
#         search_url = f"https://www.google.com/search?q={search_query}"
#         headers = req_headers
#         response = requests.get(search_url, headers=headers)
#
#         if response.status_code == 200:
#             soup = BeautifulSoup(response.text, "html.parser")
#             search_results = soup.find_all("a")
#             for result in search_results:
#                 link = result.get("href")
#                 if link and link.startswith("/url?q="):
#                     url = link[7:]
#                     info = data_scrape(url)
#                     if info != -1:
#                         message_list.append({"role": "system", "content": info})
#         else:
#             print("Failed to retrieve search results.")
#
#     return message_list

# gemma_model_path = os.path.join(os.path.dirname(__file__), 'gemma-2-2b-it')
# tokenizer = AutoTokenizer.from_pretrained(gemma_model_path)
#
# # Initialization
# with init_empty_weights():
#     model = AutoModelForCausalLM.from_pretrained(
#         gemma_model_path,
#         low_cpu_mem_usage=True,
#         torch_dtype=torch.bfloat16  # model weights use bfloat16
#     )
#
# # tie the model weights before dispatching
# model.tie_weights()
#
# # Load the model with CPU offloading and layer dispatch to handle limited memory
# model = load_checkpoint_and_dispatch(
#     model,
#     gemma_model_path,
#     device_map={"": "cpu"},
#     offload_state_dict=True
# )


# Gemma 2B - Modified response generation to work on CPU
# def generate_gemma_response(message_list):
#     # concatenated_input = " ".join([msg["content"] for msg in message_list])
#     #
#     # print(concatenated_input)
#     #
#     # # keep input_ids as LongTensor
#     # inputs = tokenizer(concatenated_input, return_tensors="pt")
#     # inputs = {key: value.to("cpu") for key, value in inputs.items()}
#     #
#     # # model weights are in bfloat16
#     # outputs = model.generate(**inputs, max_length=6000)
#     #
#     # # Decode the generated output
#     # full_output = tokenizer.decode(outputs[0], skip_special_tokens=True)
#     #
#     # print("Output prior to stripping: " + full_output)
#     full_output = "This is a mock output."
#
#     # response = full_output.replace(concatenated_input, "").strip()
#
#     return full_output
#
#
# # Gemma 2B
# def create_gemma_response(user_input, message_list):
#     """
#     Generates a response from the locally run Gemma 2B model.
#     """
#
#     message_list.append({"role": "user", "content": user_input})
#
#     print("The received message list for response generation:", message_list)
#
#     response = generate_gemma_response(message_list)
#     message_list.append({"role": "system", "content": response})
#
#     print(response)
#     return response
#
#
# # Gemma 2B
# def create_gemma_advanced_response(user_input, message_list):
#     """
#     Generates an advanced response from the locally run Gemma 2B model,
#     searching URLs before generating a response.
#     """
#
#     message_list.append({"role": "user",
#                          "content": "Answer the following question with the context provided below: " + user_input + "\n" + "Below is context: " + "\n"})
#
#     # Search in preferred URLs first
#     print("Searching user preferred URLs")
#     preferred_message_list = search_preferred_urls(user_input)  # URL searching logic
#     message_list.extend(preferred_message_list)
#
#     # If no relevant information found, fall back to Gemma 2B response
#     if not preferred_message_list:
#         for url in search(user_input, num=10, stop=10, pause=0):
#             info = data_scrape(url)
#             if info != -1:
#                 message_list.append({"role": "system", "content": "url: " + str(url) + " info: " + info})
#
#     print(message_list)
#     response = generate_gemma_response(message_list)
#
#     message_list.append({"role": "system", "content": response})
#
#     return response

# def create_advanced_response(user_input, message_list, model="o1-preview"):
#     """
#     Creates an advanced response by searching through user-preferred URLs first,
#     and then falling back to a general web search using the specified model.
#     """
#     print(f"msg list: {message_list}")
#     openai.api_key = api_key
#     print("starting creation")
#
#     # Search in preferred URLs first
#     print("Searching user preferred URLs")
#     preferred_message_list = search_preferred_urls(user_input)
#     message_list.extend(preferred_message_list)
#
#     # If no relevant information found, fall back to general web search
#     if not preferred_message_list:
#         for url in search(user_input, num=5, stop=5, pause=0):
#             info = data_scrape(url)
#             if info != -1:
#                 message_list.append({"role": "system", "content": "url: " + str(url) + " info: " + info})
#
#     message_list.append({"role": "user", "content": user_input})
#     completion = openai.ChatCompletion.create(
#         model=model,
#         messages=message_list,
#     )
#     print(completion.choices[0].message.content)
#
#     return completion.choices[0].message.content