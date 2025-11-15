import sys
import asyncio

# CRITICAL: Set Windows event loop policy before any other imports
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

from langchain.tools import tool
from playwright.sync_api import sync_playwright, Browser, BrowserContext, Page, Playwright
from dotenv import load_dotenv
import logging
import os
import base64
from typing import Optional
import asyncio
from concurrent.futures import ThreadPoolExecutor
import requests
import google.generativeai as genai
from PIL import Image

load_dotenv()

logger = logging.getLogger(__name__)

NVIDIA_API_KEY = os.getenv("NVIDIA_API_KEY")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
BROWSER_USER_DATA_DIR = os.getenv("BROWSER_USER_DATA_DIR", os.path.join(os.getcwd(), "browser_data"))

# NVIDIA VLM endpoint (fallback)
NVIDIA_VLM_URL = "https://integrate.api.nvidia.com/v1/chat/completions"

# Initialize Google Gemini
gemini_model = None
if GOOGLE_API_KEY:
    try:
        genai.configure(api_key=GOOGLE_API_KEY)
        gemini_model = genai.GenerativeModel('gemini-2.5-flash')
        logger.info("Google Gemini 2.5 Flash initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize Gemini: {e}")
else:
    logger.warning("GOOGLE_API_KEY not found, will use NVIDIA VLM as fallback")

# Global sync browser state
_playwright: Optional[Playwright] = None
_context: Optional[BrowserContext] = None
_page: Optional[Page] = None
_executor = ThreadPoolExecutor(max_workers=1)  # Dedicated thread for browser


def _ensure_browser() -> Page:
    """Ensure browser is initialized with persistent user data and return page."""
    global _playwright, _context, _page
    
    if _page is None:
        logger.info(f"Initializing Playwright browser with persistent storage at: {BROWSER_USER_DATA_DIR}")
        
        # Create user data directory if it doesn't exist
        os.makedirs(BROWSER_USER_DATA_DIR, exist_ok=True)
        
        _playwright = sync_playwright().start()
        
        # Launch browser with persistent context (saves cookies, sessions, etc.)
        _context = _playwright.chromium.launch_persistent_context(
            user_data_dir=BROWSER_USER_DATA_DIR,
            headless=False,
            viewport={'width': 1280, 'height': 720},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            accept_downloads=True,
            bypass_csp=True,
            channel="chrome"
        )
        
        _page = _context.pages[0] if _context.pages else _context.new_page()
        logger.info("Browser launched successfully (persistent mode, visible)")
    
    return _page


@tool
async def navigate_browser(url: str) -> str:
    """
    Navigate the browser to a specific URL.
    
    Args:
        url: The URL to navigate to
        
    Returns:
        Success message with current URL
    """
    try:
        def navigate_sync():
            page = _ensure_browser()
            page.goto(url, wait_until='domcontentloaded', timeout=30000)
            return page.url
        
        current_url = await asyncio.get_event_loop().run_in_executor(_executor, navigate_sync)
        logger.info(f"Navigated to: {current_url}")
        return f"Successfully navigated to: {current_url}"
    
    except Exception as e:
        logger.error(f"Navigation failed: {e}", exc_info=True)
        return f"Error navigating to URL: {str(e)}"


@tool
async def get_current_url() -> str:
    """
    Get the current URL of the browser page.
    
    Returns:
        Current URL
    """
    try:
        def get_url_sync():
            page = _ensure_browser()
            return page.url
        
        current_url = await asyncio.get_event_loop().run_in_executor(_executor, get_url_sync)
        logger.info(f"Current URL: {current_url}")
        return current_url
    
    except Exception as e:
        logger.error(f"Failed to get current URL: {e}", exc_info=True)
        return f"Error getting current URL: {str(e)}"


@tool
async def take_screenshot() -> str:
    """
    Take a screenshot of the current browser page.
    
    Returns:
        Path to the saved screenshot file
    """
    try:
        def screenshot_sync():
            page = _ensure_browser()
            screenshot_path = os.path.join(os.getcwd(), f"screenshot_{os.urandom(4).hex()}.png")
            page.screenshot(path=screenshot_path, full_page=False)
            return screenshot_path
        
        screenshot_path = await asyncio.get_event_loop().run_in_executor(_executor, screenshot_sync)
        logger.info(f"Screenshot saved: {screenshot_path}")
        return screenshot_path  # Return the path, not just a message
    
    except Exception as e:
        logger.error(f"Screenshot failed: {e}", exc_info=True)
        return f"Error taking screenshot: {str(e)}"


@tool
async def analyze_screenshot(screenshot_path: str, query: str) -> str:
    """
    Analyze a screenshot using Google Gemini 2.5 Flash (primary) or NVIDIA Nemotron VLM (fallback).
    
    Args:
        screenshot_path: Path to the screenshot file
        query: Question to ask about the screenshot
        
    Returns:
        Analysis result from VLM
    """
    try:
        if not os.path.exists(screenshot_path):
            return f"Error: Screenshot file not found: {screenshot_path}"
        
        logger.info(f"Analyzing screenshot: {query[:100]}...")
        
        # Try Google Gemini first
        if gemini_model:
            try:
                logger.info("Using Google Gemini 2.0 Flash for analysis")
                
                def analyze_with_gemini():
                    # Open image
                    img = Image.open(screenshot_path)
                    
                    # Prepare prompt with instructions
                    prompt = f"""{query}

IMPORTANT INSTRUCTIONS:
- If asked for coordinates, provide exact (x, y) pixel positions from top-left corner (0, 0)
- Be very precise with coordinate locations
- Do not be chatty
- If you cannot find something, say so clearly"""
                    
                    # Generate content with image
                    response = gemini_model.generate_content([prompt, img])
                    return response.text
                
                loop = asyncio.get_event_loop()
                analysis = await loop.run_in_executor(None, analyze_with_gemini)
                
                logger.info(f"Gemini Analysis: {analysis[:200]}...")
                
                # Clean up screenshot
                try:
                    os.remove(screenshot_path)
                    logger.info(f"Cleaned up screenshot: {screenshot_path}")
                except Exception as e:
                    logger.warning(f"Could not delete screenshot: {e}")
                
                return analysis
            
            except Exception as e:
                logger.warning(f"Gemini analysis failed, falling back to NVIDIA VLM: {e}")
        
        # Fallback to NVIDIA VLM
        logger.info("Using NVIDIA Nemotron VLM (fallback)")
        
        # Read and encode screenshot to base64
        with open(screenshot_path, 'rb') as img_file:
            image_data = base64.b64encode(img_file.read()).decode('utf-8')
        
        # Prepare the request for NVIDIA VLM
        headers = {
            "Authorization": f"Bearer {NVIDIA_API_KEY}",
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        
        # Build content array with query and image
        content = [
            {
                "type": "text",
                "text": f"""{query}

IMPORTANT INSTRUCTIONS:
- If asked for coordinates, provide exact (x, y) pixel positions from top-left corner (0, 0)
- Be very precise with coordinate locations
- Describe what you see clearly and concisely
- If you cannot find something, say so clearly"""
            },
            {
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/png;base64,{image_data}"
                }
            }
        ]
        
        # Prepare messages for the VLM
        messages = [
            {
                "role": "system",
                "content": "/think"
            },
            {
                "role": "user",
                "content": content
            }
        ]
        
        payload = {
            "max_tokens": 4096,
            "temperature": 0.3,
            "top_p": 1,
            "frequency_penalty": 0,
            "presence_penalty": 0,
            "messages": messages,
            "stream": False,
            "model": "nvidia/nemotron-nano-12b-v2-vl"
        }
        
        # Make the API call
        def call_nvidia_vlm():
            response = requests.post(NVIDIA_VLM_URL, headers=headers, json=payload, timeout=60)
            response.raise_for_status()
            return response.json()
        
        loop = asyncio.get_event_loop()
        vlm_response = await loop.run_in_executor(None, call_nvidia_vlm)
        
        # Extract the analysis from response
        analysis = vlm_response.get("choices", [{}])[0].get("message", {}).get("content", "")
        
        if not analysis:
            return "Error: VLM returned empty response"
        
        logger.info(f"NVIDIA VLM Analysis: {analysis[:200]}...")
        
        # Clean up screenshot
        try:
            os.remove(screenshot_path)
            logger.info(f"Cleaned up screenshot: {screenshot_path}")
        except Exception as e:
            logger.warning(f"Could not delete screenshot: {e}")
        
        return analysis
    
    except Exception as e:
        logger.error(f"Screenshot analysis failed: {e}", exc_info=True)
        return f"Error analyzing screenshot: {str(e)}"


@tool
async def click_at(x: int, y: int) -> str:
    """
    Click at specific pixel coordinates on the page.
    
    Args:
        x: X coordinate (pixels from left)
        y: Y coordinate (pixels from top)
        
    Returns:
        Success message
    """
    try:
        def click_sync():
            page = _ensure_browser()
            page.mouse.click(x, y)
        
        await asyncio.get_event_loop().run_in_executor(_executor, click_sync)
        logger.info(f"Clicked at coordinates: ({x}, {y})")
        return f"Successfully clicked at ({x}, {y})"
    
    except Exception as e:
        logger.error(f"Click failed: {e}", exc_info=True)
        return f"Error clicking at coordinates: {str(e)}"


@tool
async def type_text(text: str) -> str:
    """
    Type text into the currently focused element.
    
    Args:
        text: Text to type
        
    Returns:
        Success message
    """
    try:
        def type_sync():
            page = _ensure_browser()
            page.keyboard.type(text, delay=50)
        
        await asyncio.get_event_loop().run_in_executor(_executor, type_sync)
        logger.info(f"Typed text: {text[:50]}...")
        return f"Successfully typed text"
    
    except Exception as e:
        logger.error(f"Type text failed: {e}", exc_info=True)
        return f"Error typing text: {str(e)}"


@tool
async def press_key(key: str) -> str:
    """
    Press a keyboard key (e.g., 'Enter', 'Escape', 'Tab').
    
    Args:
        key: Key name to press
        
    Returns:
        Success message
    """
    try:
        def press_sync():
            page = _ensure_browser()
            page.keyboard.press(key)
        
        await asyncio.get_event_loop().run_in_executor(_executor, press_sync)
        logger.info(f"Pressed key: {key}")
        return f"Successfully pressed key: {key}"
    
    except Exception as e:
        logger.error(f"Press key failed: {e}", exc_info=True)
        return f"Error pressing key: {str(e)}"


@tool
async def scroll_page(direction: str = "down", amount: int = 300) -> str:
    """
    Scroll the page up or down.
    
    Args:
        direction: 'up' or 'down'
        amount: Number of pixels to scroll
        
    Returns:
        Success message
    """
    try:
        def scroll_sync():
            page = _ensure_browser()
            scroll_amount = amount if direction == "down" else -amount
            page.evaluate(f"window.scrollBy(0, {scroll_amount})")
        
        await asyncio.get_event_loop().run_in_executor(_executor, scroll_sync)
        logger.info(f"Scrolled {direction} by {amount}px")
        return f"Successfully scrolled {direction}"
    
    except Exception as e:
        logger.error(f"Scroll failed: {e}", exc_info=True)
        return f"Error scrolling page: {str(e)}"


@tool
async def go_back() -> str:
    """
    Navigate back to the previous page.
    
    Returns:
        Success message with new URL
    """
    try:
        def back_sync():
            page = _ensure_browser()
            page.go_back(wait_until='domcontentloaded')
            return page.url
        
        current_url = await asyncio.get_event_loop().run_in_executor(_executor, back_sync)
        logger.info(f"Navigated back to: {current_url}")
        return f"Navigated back to: {current_url}"
    
    except Exception as e:
        logger.error(f"Go back failed: {e}", exc_info=True)
        return f"Error going back: {str(e)}"


@tool
async def close_browser() -> str:
    """
    Close the browser instance (saves all session data).
    
    Returns:
        Success message
    """
    global _playwright, _context, _page
    
    try:
        def close_sync():
            global _playwright, _context, _page
            if _context:
                _context.close()
                _context = None
                _page = None
            if _playwright:
                _playwright.stop()
                _playwright = None
        
        await asyncio.get_event_loop().run_in_executor(_executor, close_sync)
        logger.info("Browser closed successfully (session data saved)")
        return "Browser closed successfully"
    
    except Exception as e:
        logger.error(f"Close browser failed: {e}", exc_info=True)
        return f"Error closing browser: {str(e)}"


# Export browser tools
browser_tools_list = [
    navigate_browser,
    get_current_url,
    take_screenshot,
    analyze_screenshot,
    click_at,
    type_text,
    press_key,
    scroll_page,
    go_back,
    close_browser
]
