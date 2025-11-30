"""
URL Tools - Simple web scraping via requests + BeautifulSoup
With smart compression using gpt-4o-mini
"""

import json
import logging
import requests
import os
import re
from pathlib import Path
from typing import Dict, Any, Optional
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from openai import OpenAI
from agents import function_tool

logger = logging.getLogger(__name__)

# Load environment variables
backend_dir = Path(__file__).resolve().parent.parent
load_dotenv(backend_dir / '.env')

SITE_MAP_PATH = Path(__file__).resolve().parent.parent / "data" / "site_map.json"
_site_map_cache: Optional[Dict] = None

# Initialize OpenAI client
client = None
if os.getenv("OPENAI_API_KEY"):
    try:
        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    except Exception as e:
        logger.warning(f"Failed to initialize OpenAI client: {e}")

# Simple headers to avoid bot detection
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.5',
}


def _load_site_map() -> Dict:
    """Load site map configuration."""
    global _site_map_cache
    if _site_map_cache is None:
        try:
            with open(SITE_MAP_PATH, 'r', encoding='utf-8') as f:
                _site_map_cache = json.load(f)
        except Exception as e:
            logger.error(f"Failed to load site map: {e}")
            _site_map_cache = {"routes": {}}
    return _site_map_cache


@function_tool
def resolve_url(route_id: str, params: str) -> str:
    """
    Build a URL from route_id and parameters.

    Args:
        route_id: Route name (e.g., 'yahoo_quote', 'yahoo_news', 'generic_url')
        params: JSON string with parameters (e.g., '{"ticker": "AAPL"}')

    Returns:
        JSON with the constructed URL
    """
    try:
        # Parse params
        if isinstance(params, str):
            try:
                params_dict = json.loads(params)
            except json.JSONDecodeError:
                params_dict = {"ticker": params.strip()}
        else:
            params_dict = params

        site_map = _load_site_map()
        routes = site_map.get("routes", {})

        if route_id not in routes:
            return json.dumps({"error": f"Route '{route_id}' not found", "available": list(routes.keys())[:10]})

        route = routes[route_id]
        url_pattern = route["url_pattern"]
        defaults = route.get("param_defaults", {})

        # Apply defaults
        for k, v in defaults.items():
            if k not in params_dict:
                params_dict[k] = v

        url = url_pattern.format(**params_dict)
        return json.dumps({"url": url})

    except Exception as e:
        return json.dumps({"error": str(e)})


def _clean_text(text: str) -> str:
    """Basic cleanup of raw text."""
    # Collapse multiple newlines
    text = re.sub(r'\n{3,}', '\n\n', text)
    # Collapse multiple spaces
    text = re.sub(r' {2,}', ' ', text)
    return text.strip()


def _smart_compress(text: str, url: str) -> str:
    """Compress content using gpt-4o-mini."""
    if not client:
        return text[:15000] + "\n[Truncated: No OpenAI Key]"

    try:
        # limit input to avoid token limits even for the compressor
        input_text = text[:60000] 
        
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system", 
                    "content": (
                        "You are a web content compressor. "
                        "Your task is to convert the provided raw web page text into a clear, concise Markdown summary. "
                        "RULES:\n"
                        "1. Preserve ALL specific facts, numbers, dates, tickers, and technical details.\n"
                        "2. Remove navigation menus, footers, ads, legal disclaimers, and 'read more' links.\n"
                        "3. Structure the output with Markdown headers.\n"
                        "4. If the content is an article, summarize the key points but keep the narrative flow.\n"
                        "5. Output MUST be significantly shorter than the input while retaining value."
                    )
                },
                {"role": "user", "content": f"URL: {url}\n\nRAW CONTENT:\n{input_text}"}
            ],
            max_tokens=6000, # Allow enough space for a detailed summary
            temperature=0.3
        )
        compressed_text = response.choices[0].message.content
        logger.info(f"[SMART COMPRESSION] Success for {url}. Reduced {len(text)} chars -> {len(compressed_text)} chars ({(len(compressed_text)/len(text))*100:.1f}%)")
        return compressed_text
    except Exception as e:
        logger.error(f"[SMART COMPRESSION] Failed for {url}: {e}")
        return text[:15000] + f"\n[Compression failed: {str(e)}]"



def scrape_with_playwright(url: str) -> str:
    """Fallback scraping using Playwright for SPAs."""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        logger.warning("Playwright not installed, skipping fallback")
        return ""

    try:
        with sync_playwright() as p:
            # Launch options compatible with the Docker environment
            browser = p.chromium.launch(headless=True, args=['--no-sandbox', '--disable-setuid-sandbox'])
            
            # Create context with user agent to avoid detection
            context = browser.new_context(
                user_agent=HEADERS['User-Agent'],
                viewport={'width': 1280, 'height': 800}
            )
            
            page = context.new_page()
            
            # Navigate with timeout
            logger.info(f"Playwright scraping: {url}")
            page.goto(url, timeout=30000, wait_until="domcontentloaded")
            
            # Wait a bit for JS to execute (simple heuristic)
            try:
                page.wait_for_load_state("networkidle", timeout=5000)
            except Exception:
                pass # Continue if network doesn't settle
                
            # Get text content
            # We use evaluate to get innerText which is closer to rendered text
            text = page.evaluate("document.body.innerText")
            
            browser.close()
            return _clean_text(text)
            
    except Exception as e:
        logger.error(f"Playwright scraping failed for {url}: {e}")
        return ""


@function_tool
def scrape_url(url: str) -> str:
    """
    Fetch a URL and return the visible text content.
    Uses requests first, falls back to Playwright for SPAs.
    Uses smart compression for long pages.

    Args:
        url: The URL to scrape

    Returns:
        JSON with page content or error
    """
    if not url.startswith(('http://', 'https://')):
        return json.dumps({"error": "Invalid URL"})

    text = ""
    used_method = "requests"

    try:
        response = requests.get(url, headers=HEADERS, timeout=15)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, 'html.parser')

        # Remove script and style elements
        for tag in soup(['script', 'style', 'noscript', 'iframe', 'svg', 'header', 'footer', 'nav', 'aside']):
            tag.decompose()

        # Get text
        text = soup.get_text(separator='\n', strip=True)
        text = _clean_text(text)
        
        # Check if content is suspicious (too short or JS required)
        is_suspicious = len(text) < 500 or "javascript" in text.lower() or "enable js" in text.lower()
        
        if is_suspicious:
            logger.info(f"Content suspicious (len={len(text)}), attempting Playwright fallback for {url}")
            pw_text = scrape_with_playwright(url)
            if len(pw_text) > len(text):
                text = pw_text
                used_method = "playwright"
                logger.info(f"Playwright fallback successful (len={len(text)})")

    except Exception as e:
        logger.warning(f"Requests scraping failed for {url}: {e}. Attempting Playwright fallback.")
        # Fallback to Playwright on error
        text = scrape_with_playwright(url)
        if text:
            used_method = "playwright"
        else:
            return json.dumps({"error": f"Failed to scrape {url}: {str(e)}", "url": url})

    # Smart compression threshold
    if len(text) > 4000:
        logger.info(f"Compressing content for {url} (Length: {len(text)})")
        text = _smart_compress(text, url)
    
    return json.dumps({
        "url": url, 
        "content": text, 
        "method": used_method,
        "length": len(text)
    })


def get_url_tools():
    """Return URL tools for agent."""
    return [resolve_url, scrape_url]
