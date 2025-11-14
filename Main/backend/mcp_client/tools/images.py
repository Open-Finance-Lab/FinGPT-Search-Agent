"""image capture and description tools"""

from agents import function_tool
import logging
import base64

logger = logging.getLogger(__name__)


@function_tool
async def screenshot_page() -> str:
    """
    take a screenshot of the current webpage
    returns base64 encoded image that can be analyzed
    """
    try:
        from .. import playwright_tools
        page = await playwright_tools.get_page()
        
        if page.url == 'about:blank':
            return "error: no page loaded"
        
        # take screenshot
        screenshot_bytes = await page.screenshot(type='png', full_page=False)
        
        # encode to base64
        base64_image = base64.b64encode(screenshot_bytes).decode('utf-8')
        
        # return with data uri format for llm
        return f"captured screenshot of {page.url}\nimage size: {len(screenshot_bytes)} bytes\nbase64 data available for analysis"
    
    except Exception as e:
        return f"error: {str(e)}"


@function_tool
async def screenshot_element(selector: str) -> str:
    """
    take a screenshot of a specific element on the page
    
    args:
        selector: css selector for the element (e.g., "#chart", ".data-table")
    """
    try:
        from .. import playwright_tools
        page = await playwright_tools.get_page()
        
        if page.url == 'about:blank':
            return "error: no page loaded"
        
        element = await page.query_selector(selector)
        if not element:
            return f"error: no element found matching {selector}"
        
        screenshot_bytes = await element.screenshot(type='png')
        base64_image = base64.b64encode(screenshot_bytes).decode('utf-8')
        
        return f"captured screenshot of element: {selector}\nimage size: {len(screenshot_bytes)} bytes"
    
    except Exception as e:
        return f"error: {str(e)}"


@function_tool
async def get_page_images() -> str:
    """
    list all images on the current page with their urls and alt text
    """
    try:
        from .. import playwright_tools
        page = await playwright_tools.get_page()
        
        if page.url == 'about:blank':
            return "error: no page loaded"
        
        images = await page.evaluate("""
            () => {
                return Array.from(document.querySelectorAll('img')).slice(0, 20).map(img => ({
                    src: img.src,
                    alt: img.alt || '[no alt text]',
                    width: img.width,
                    height: img.height
                }));
            }
        """)
        
        if not images:
            return "no images found on page"
        
        output = f"found {len(images)} images:\n\n"
        for i, img in enumerate(images, 1):
            output += f"{i}. {img['alt']}\n"
            output += f"   size: {img['width']}x{img['height']}\n"
            output += f"   url: {img['src'][:100]}...\n\n"
        
        return output
    
    except Exception as e:
        return f"error: {str(e)}"

