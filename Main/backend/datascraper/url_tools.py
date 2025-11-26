"""
URL Tools - Simple web scraping via requests + BeautifulSoup
"""

import json
import logging
import requests
from pathlib import Path
from typing import Dict, Any, Optional
from bs4 import BeautifulSoup
from agents import function_tool

logger = logging.getLogger(__name__)

SITE_MAP_PATH = Path(__file__).resolve().parent.parent / "data" / "site_map.json"
_site_map_cache: Optional[Dict] = None

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


@function_tool
def scrape_url(url: str) -> str:
    """
    Fetch a URL and return the visible text content.

    Args:
        url: The URL to scrape

    Returns:
        JSON with page content or error
    """
    if not url.startswith(('http://', 'https://')):
        return json.dumps({"error": "Invalid URL"})

    try:
        response = requests.get(url, headers=HEADERS, timeout=15)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, 'html.parser')

        # Remove script and style elements
        for tag in soup(['script', 'style', 'noscript', 'iframe']):
            tag.decompose()

        # Get text (equivalent to document.body.innerText)
        text = soup.get_text(separator='\n', strip=True)

        # Truncate if too long
        if len(text) > 50000:
            text = text[:50000] + "\n[truncated]"

        return json.dumps({"url": url, "content": text})

    except Exception as e:
        return json.dumps({"error": str(e), "url": url})


def get_url_tools():
    """Return URL tools for agent."""
    return [resolve_url, scrape_url]
