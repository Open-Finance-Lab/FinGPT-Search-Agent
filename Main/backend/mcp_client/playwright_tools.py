"""
Playwright browser automation tools for OpenAI Agents SDK.
Direct integration without MCP server overhead.
"""

from agents import function_tool
from playwright.async_api import async_playwright, Page, Browser, Playwright
from typing import Optional
from urllib.parse import urlparse
import logging
import asyncio

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global browser state - single browser instance per process
# TODO Add session management
_playwright: Optional[Playwright] = None
_browser: Optional[Browser] = None
_page: Optional[Page] = None
_lock = asyncio.Lock()

# Domain restriction state (set by agent)
_RESTRICTED_DOMAIN: Optional[str] = None
_CURRENT_URL: Optional[str] = None


async def get_page() -> Page:
    """
    Lazy initialization of browser with proper error handling.
    Returns the active page instance, creating it if necessary.
    """
    global _playwright, _browser, _page

    async with _lock:  # Prevent race conditions
        if _page is None:
            try:
                logger.info("Initializing Playwright browser...")
                _playwright = await async_playwright().start()

                # Launch with reasonable defaults for financial data scraping
                _browser = await _playwright.chromium.launch(
                    headless=True,  # Run headless for server deployment
                    args=[
                        '--disable-dev-shm-usage',  # Prevent shared memory issues
                        '--no-sandbox',  # Required for some environments
                        '--disable-setuid-sandbox',
                        '--disable-blink-features=AutomationControlled',  # Avoid detection
                    ]
                )

                # Create page with proper viewport and user agent
                context = await _browser.new_context(
                    viewport={'width': 1920, 'height': 1080},
                    user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                )
                _page = await context.new_page()

                # Timeouts
                _page.set_default_timeout(30000)  # 30 seconds
                _page.set_default_navigation_timeout(30000)

                logger.info("Browser initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize browser: {e}")
                raise

        return _page


@function_tool
async def navigate_to_url(url: str) -> str:
    """Navigate to a URL and return status information.

    Args:
        url: The URL to navigate to (must include protocol like https://)

    Returns:
        Status message with page title and final URL
    """
    if not url.startswith(('http://', 'https://')):
        return f"Error: URL must start with http:// or https://. Got: {url}"

    # Check domain restriction if set
    if _RESTRICTED_DOMAIN:
        try:
            parsed = urlparse(url)
            target_domain = parsed.netloc

            if target_domain != _RESTRICTED_DOMAIN:
                logger.warning(f"Domain restriction: {target_domain} != {_RESTRICTED_DOMAIN}")
                return (
                    f"Error: Cannot navigate to {url}\n"
                    f"You can only navigate within {_RESTRICTED_DOMAIN}.\n"
                    f"The user is asking about the current website, not external sites."
                )
        except Exception as e:
            logger.error(f"Error parsing URL {url}: {e}")
            return f"Error: Invalid URL format: {url}"

    try:
        page = await get_page()

        # Navigate with wait for network idle
        response = await page.goto(url, wait_until='domcontentloaded')

        # Wait a bit for dynamic content
        await page.wait_for_timeout(1000)

        title = await page.title()
        current_url = page.url
        status = response.status if response else 'unknown'

        logger.info(f"Navigated to {current_url} - Status: {status}")
        return f"Successfully navigated to {current_url}\nPage title: {title}\nHTTP Status: {status}"

    except asyncio.TimeoutError:
        return f"Timeout: Page took too long to load: {url}"
    except Exception as e:
        logger.error(f"Navigation error: {e}")
        return f"Failed to navigate to {url}: {str(e)}"


@function_tool
async def get_page_text() -> str:
    """Extract all visible text content from the current page.

    Returns:
        The text content of the page body (limited to 10,000 characters)
    """
    try:
        page = await get_page()

        if page.url == 'about:blank':
            return "Error: No page loaded. Use navigate_to_url first."

        text = await page.inner_text('body')
        text = ' '.join(text.split())

        # Limit response size to avoid token overflow
        if len(text) > 40000:
            text = text[:40000] + "... [truncated]"

        return text

    except Exception as e:
        logger.error(f"Error extracting text: {e}")
        return f"Error extracting text: {str(e)}"


@function_tool
async def click_element(selector: str) -> str:
    """Click an element on the page using a CSS selector.

    Args:
        selector: CSS selector for the element to click (e.g., 'button.submit', '#search-button')

    Returns:
        Success or error message
    """
    try:
        page = await get_page()

        if page.url == 'about:blank':
            return "Error: No page loaded. Use navigate_to_url first."

        element = await page.query_selector(selector)
        if not element:
            return f"Error: No element found matching selector: {selector}"

        is_visible = await element.is_visible()
        if not is_visible:
            return f"Error: Element exists but is not visible: {selector}"

        await page.click(selector, timeout=10000)

        # Wait for potential navigation or dynamic updates
        await page.wait_for_timeout(700)

        return f"Successfully clicked element: {selector}"

    except asyncio.TimeoutError:
        return f"Timeout: Element not clickable within 10 seconds: {selector}"
    except Exception as e:
        logger.error(f"Click error: {e}")
        return f"Failed to click {selector}: {str(e)}"


@function_tool
async def fill_form_field(selector: str, value: str) -> str:
    """Fill a form field with text.

    Args:
        selector: CSS selector for the input field (e.g., 'input[name="search"]', '#username')
        value: Text to enter into the field

    Returns:
        Success or error message
    """
    try:
        page = await get_page()

        if page.url == 'about:blank':
            return "Error: No page loaded. Use navigate_to_url first."

        element = await page.query_selector(selector)
        if not element:
            return f"Error: No element found matching selector: {selector}"

        await page.fill(selector, value, timeout=10000)

        return f"Successfully filled {selector} with: {value}"

    except asyncio.TimeoutError:
        return f"Timeout: Could not fill field within 10 seconds: {selector}"
    except Exception as e:
        logger.error(f"Fill error: {e}")
        return f"Failed to fill {selector}: {str(e)}"


@function_tool
async def press_enter() -> str:
    """Press the Enter key on the current page.

    Useful for submitting forms after filling fields.

    Returns:
        Success message
    """
    try:
        page = await get_page()

        if page.url == 'about:blank':
            return "Error: No page loaded. Use navigate_to_url first."

        await page.keyboard.press('Enter')

        # Wait for potential navigation
        await page.wait_for_timeout(1000)

        return "Successfully pressed Enter key"

    except Exception as e:
        logger.error(f"Keyboard error: {e}")
        return f"Failed to press Enter: {str(e)}"


@function_tool
async def get_current_url() -> str:
    """Get the current page URL.

    Returns:
        The current URL or error message
    """
    try:
        page = await get_page()
        url = page.url

        if url == 'about:blank':
            return "No page loaded yet. Use navigate_to_url to visit a website."

        return url

    except Exception as e:
        logger.error(f"Error getting URL: {e}")
        return f"Error getting URL: {str(e)}"


@function_tool
async def wait_for_element(selector: str, timeout: int = 10) -> str:
    """Wait for an element to appear on the page.

    Args:
        selector: CSS selector for the element to wait for
        timeout: Maximum time to wait in seconds (default: 10)

    Returns:
        Success or timeout message
    """
    try:
        page = await get_page()

        if page.url == 'about:blank':
            return "Error: No page loaded. Use navigate_to_url first."

        await page.wait_for_selector(selector, timeout=timeout * 1000)
        return f"Element appeared: {selector}"

    except asyncio.TimeoutError:
        return f"Timeout: Element did not appear within {timeout} seconds: {selector}"
    except Exception as e:
        logger.error(f"Wait error: {e}")
        return f"Error waiting for element: {str(e)}"


@function_tool
async def extract_links() -> str:
    """Extract all links from the current page.

    Returns:
        A list of links with their text and URLs
    """
    try:
        page = await get_page()

        if page.url == 'about:blank':
            return "Error: No page loaded. Use navigate_to_url first."

        # Extract all links
        links = await page.evaluate("""
            () => {
                const links = Array.from(document.querySelectorAll('a[href]'));
                return links.slice(0, 50).map(link => ({  // Limit to 50 links
                    text: link.innerText.trim().substring(0, 100),
                    href: link.href
                })).filter(link => link.href && link.href !== '#');
            }
        """)

        if not links:
            return "No links found on the page"

        # Formatting
        result = "Links found on page:\n"
        for i, link in enumerate(links, 1):
            text = link['text'] or '[No text]'
            href = link['href']
            result += f"{i}. {text}\n   URL: {href}\n"

        return result

    except Exception as e:
        logger.error(f"Error extracting links: {e}")
        return f"Error extracting links: {str(e)}"


async def cleanup_browser():
    """
    Cleanup browser resources.
    Should be called when the agent is done.
    """
    global _playwright, _browser, _page

    try:
        if _page:
            await _page.close()
            _page = None
        if _browser:
            await _browser.close()
            _browser = None
        if _playwright:
            await _playwright.stop()
            _playwright = None
        logger.info("Browser cleanup completed")
    except Exception as e:
        logger.error(f"Error during cleanup: {e}")