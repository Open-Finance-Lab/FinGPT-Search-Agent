import requests
import json
import logging
import sys

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger('mcp_debug')

def debug_mcp_server(base_url="http://localhost:8000"):
    """
    Debug the MCP server by testing various endpoints and configurations.
    """
    # 1. Test the Django server itself
    try:
        logger.info("Testing Django server...")
        response = requests.get(base_url)
        logger.info(f"Django server response: {response.status_code}")
        logger.info(f"Response text: {response.text[:100]}")
    except Exception as e:
        logger.error(f"Error connecting to Django server: {e}")

    # 2. Test the MCP endpoint with different configurations
    mcp_paths = [
        "/mcp",            # Standard path from your config
        "/mcp/",           # With trailing slash
        "/api/mcp",        # Alternative common pattern
        "/api/mcp/"        # Alternative with trailing slash
    ]

    for path in mcp_paths:
        test_url = f"{base_url}{path}"
        logger.info(f"\nTesting MCP endpoint at: {test_url}")

        headers = {
            'Content-Type': 'application/json',
        }

        payload = {
            "tool": "hello_world",
            "params": {"name": "MCP Debugger"}
        }

        try:
            response = requests.post(test_url, headers=headers, json=payload)
            logger.info(f"Status: {response.status_code}")
            logger.info(f"Response: {response.text[:200]}")
        except Exception as e:
            logger.error(f"Error: {e}")

if __name__ == "__main__":
    debug_mcp_server()