#Browser automation with Gemini 2.0 Flash for vision + Tavily for web search
from langchain_nvidia_ai_endpoints import ChatNVIDIA
from langchain_core.messages import HumanMessage, AIMessage
from dotenv import load_dotenv
import logging
import os
from PIL import Image
from playwright.sync_api import sync_playwright, BrowserContext, Page, Playwright
from typing import Optional, Dict, Any
from concurrent.futures import ThreadPoolExecutor
import asyncio
import base64
import json
import google.generativeai as genai
from langchain_community.tools.tavily_search import TavilySearchResults

load_dotenv()

logger = logging.getLogger(__name__)

NVIDIA_API_KEY = os.getenv("NVIDIA_API_KEY")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")
BROWSER_USER_DATA_DIR = os.getenv("BROWSER_USER_DATA_DIR", os.path.join(os.getcwd(), "browser_data"))

# Global browser state
_playwright: Optional[Playwright] = None
_context: Optional[BrowserContext] = None
_page: Optional[Page] = None
_executor = ThreadPoolExecutor(max_workers=1)

# Initialize Gemini 2.0 Flash for complete browser automation control
gemini_model = None
if GOOGLE_API_KEY:
    try:
        genai.configure(api_key=GOOGLE_API_KEY)
        gemini_model = genai.GenerativeModel('gemini-2.5-flash')
        logger.info("Google Gemini 2.5 Flash initialized as MASTER browser automation controller")
    except Exception as e:
        logger.error(f"Failed to initialize Gemini: {e}")
        raise RuntimeError("Gemini is required for browser automation")
else:
    raise RuntimeError("GOOGLE_API_KEY not found - required for browser automation")

# Initialize Tavily Search for accurate web search results
tavily_search = None
if TAVILY_API_KEY:
    try:
        tavily_search = TavilySearchResults(
            api_key=TAVILY_API_KEY,
            max_results=5,
            search_depth="advanced",
            include_answer=True,
            include_raw_content=False,
            include_images=False
        )
        logger.info("Tavily Search initialized for Gemini's web search capabilities")
    except Exception as e:
        logger.error(f"Failed to initialize Tavily: {e}")
        logger.warning("Browser automation will work but web search may be limited")
else:
    logger.warning("TAVILY_API_KEY not found - web search capabilities limited")


def _ensure_browser() -> Page:
    """Ensure browser is initialized with persistent user data."""
    global _playwright, _context, _page
    
    if _page is None:
        logger.info(f"Initializing browser with persistent storage: {BROWSER_USER_DATA_DIR}")
        os.makedirs(BROWSER_USER_DATA_DIR, exist_ok=True)
        
        _playwright = sync_playwright().start()
        _context = _playwright.chromium.launch_persistent_context(
            user_data_dir=BROWSER_USER_DATA_DIR,
            headless=False,
            viewport={'width': 1280, 'height': 720},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            channel="chrome"
        )
        
        _page = _context.pages[0] if _context.pages else _context.new_page()
        logger.info("Browser launched successfully")
    
    return _page


def navigate_to_url(url: str) -> str:
    """Navigate to URL."""
    page = _ensure_browser()
    page.goto(url, wait_until='domcontentloaded', timeout=30000)
    return f"Navigated to: {page.url}"


def click_at_coordinates(x: int, y: int) -> str:
    """Click at coordinates."""
    page = _ensure_browser()
    page.mouse.click(x, y)
    return f"Clicked at ({x}, {y})"


def type_text(text: str) -> str:
    """Type text."""
    page = _ensure_browser()
    page.keyboard.type(text, delay=50)
    return f"Typed text"


def press_key(key: str) -> str:
    """Press key."""
    page = _ensure_browser()
    page.keyboard.press(key)
    return f"Pressed: {key}"


def scroll_page(direction: str, amount: int = 300) -> str:
    """Scroll page."""
    page = _ensure_browser()
    scroll_amount = amount if direction == "down" else -amount
    page.evaluate(f"window.scrollBy(0, {scroll_amount})")
    return f"Scrolled {direction}"


def take_screenshot() -> str:
    """Take screenshot and return path."""
    page = _ensure_browser()
    screenshot_path = os.path.join(os.getcwd(), f"browser_screenshot.png")
    page.screenshot(path=screenshot_path, full_page=False)
    return screenshot_path


async def gemini_web_search(query: str) -> str:
    """
    Use Tavily AI to search the web for accurate results (especially YouTube URLs).
    
    Args:
        query: Search query
        
    Returns:
        Search results with URLs from Tavily
    """
    try:
        if not tavily_search:
            logger.warning("Tavily not initialized, falling back to Gemini search")
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(None, lambda: gemini_model.generate_content(f"Search the web for: {query}"))
            return response.text
        
        # Use Tavily for accurate web search
        logger.info(f"Tavily searching for: {query}")
        
        # Enhance query for YouTube searches
        search_query = query
        if any(keyword in query.lower() for keyword in ['play', 'song', 'music', 'video', 'youtube']):
            # Add YouTube to query for better targeting
            if 'youtube' not in query.lower():
                search_query = f"{query} youtube"
        
        loop = asyncio.get_event_loop()
        results = await loop.run_in_executor(None, lambda: tavily_search.invoke({"query": search_query}))
        
        if not results:
            return "No search results found."
        
        # Format results for Gemini to use
        formatted_results = []
        youtube_url = None
        
        for idx, result in enumerate(results[:5], 1):
            title = result.get('title', 'No title')
            url = result.get('url', '')
            content = result.get('content', '')[:200]  # First 200 chars
            
            # Extract YouTube URL if found
            if 'youtube.com/watch' in url and not youtube_url:
                youtube_url = url
            
            formatted_results.append(f"{idx}. {title}\n   URL: {url}\n   Snippet: {content}...")
        
        result_text = "\n\n".join(formatted_results)
        
        # If YouTube URL found, highlight it
        if youtube_url:
            result_text = f"🎵 DIRECT YOUTUBE URL: {youtube_url}\n\n{result_text}"
            logger.info(f"Found YouTube URL: {youtube_url}")
        
        return f"Tavily Search Results for '{query}':\n\n{result_text}"
        
    except Exception as e:
        logger.error(f"Tavily search failed: {e}")
        # Fallback to Gemini search
        try:
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(None, lambda: gemini_model.generate_content(f"Search the web for: {query}"))
            return f"[Tavily failed, using Gemini backup] {response.text}"
        except Exception as fallback_e:
            logger.error(f"Fallback search also failed: {fallback_e}")
            return f"Search failed: {str(e)}"


async def gemini_analyze_and_decide(screenshot_path: str, task: str, context: str = "") -> Dict[str, Any]:
    """
    Gemini analyzes screenshot and decides the next action.
    
    Args:
        screenshot_path: Path to screenshot
        task: Overall task description
        context: Context from previous actions
        
    Returns:
        Action dictionary with Gemini's decision
    """
    try:
        img = Image.open(screenshot_path)
        
        prompt = f"""You are controlling a web browser to complete this task: {task}

{f"Previous context: {context}" if context else ""}

Analyze this screenshot carefully (1280x720 pixels, top-left is 0,0).

Your response MUST be ONLY a JSON object with one of these actions:

1. **SEARCH WEB** (if you need to find a YouTube link):
{{"action": "search_web", "query": "exact search query"}}

2. **NAVIGATE** (open a URL):
{{"action": "navigate", "url": "https://example.com"}}

3. **CLICK** (click an element - provide CENTER coordinates):
{{"action": "click", "x": 640, "y": 360, "reason": "clicking the search button"}}

4. **TYPE** (type text in focused field):
{{"action": "type", "text": "text to type", "reason": "typing search query"}}

5. **PRESS KEY**:
{{"action": "press_key", "key": "Enter", "reason": "submitting search"}}

6. **WAIT** (wait for page to load):
{{"action": "wait", "seconds": 2, "reason": "waiting for video to load"}}

7. **COMPLETE** (task finished - use this when you can SEE the task is done):
{{"action": "complete", "message": "Video is playing successfully", "success": true}}

CRITICAL RULES:
- Provide EXACT pixel coordinates (x, y) for center of elements
- Screen dimensions: 1280x720
- Be extremely precise with coordinates
- Include "reason" for clicks, types, and key presses
- Respond with ONLY valid JSON, no other text
- **IMPORTANT**: If you can SEE in the screenshot that the YouTube video is playing (video player visible, no errors), use "complete" action immediately - do NOT use "verify"
- Only use "verify" if you're truly uncertain and need to double-check
- For YouTube: If you see a video playing with controls visible, that means SUCCESS - use "complete"

Example responses:
{{"action": "click", "x": 640, "y": 65, "reason": "clicking YouTube search bar"}}
{{"action": "type", "text": "timeless song", "reason": "entering song name"}}
{{"action": "verify", "question": "Is video playing without errors?", "expected": "yes"}}
{{"action": "complete", "message": "YouTube video playing successfully", "success": true}}
"""

        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(None, lambda: gemini_model.generate_content([prompt, img]))
        response_text = response.text.strip()
        
        logger.info(f"Gemini decision: {response_text[:200]}...")
        
        # Extract JSON
        if "```json" in response_text:
            json_str = response_text.split("```json")[1].split("```")[0].strip()
        elif "```" in response_text:
            json_str = response_text.split("```")[1].split("```")[0].strip()
        elif "{" in response_text and "}" in response_text:
            start = response_text.index("{")
            end = response_text.rindex("}") + 1
            json_str = response_text[start:end]
        else:
            raise ValueError(f"No JSON found in response: {response_text}")
        
        return json.loads(json_str)
    
    except Exception as e:
        logger.error(f"Gemini analysis failed: {e}")
        return {"action": "error", "message": str(e)}


# Map function names to actual functions
function_map = {
    "navigate_to_url": navigate_to_url,
    "click_at_coordinates": click_at_coordinates,
    "type_text": type_text,
    "press_key": press_key,
    "scroll_page": scroll_page
}


async def execute_browser_task(task_description: str) -> str:
    """
    Execute browser automation with Gemini 2.0 Flash as the MASTER controller.
    Gemini handles: web search, planning, visual analysis, coordination, and verification.
    
    Args:
        task_description: What to do (e.g., "Play timeless song on YouTube")
        
    Returns:
        Result message
    """
    try:
        logger.info(f"🤖 Gemini taking control of browser automation: {task_description}")
        
        loop = asyncio.get_event_loop()
        max_iterations = 20
        iteration = 0
        context_history = []
        
        # Check if this is a simple YouTube direct link request
        import re
        youtube_url_pattern = r'https?://(?:www\.)?(?:youtube\.com/watch\?v=|youtu\.be/)([a-zA-Z0-9_-]+)'
        url_match = re.search(youtube_url_pattern, task_description)
        
        # Simple task detection: if user says "play X on youtube" without other complex instructions
        simple_youtube_task = (
            ("play" in task_description.lower() or "open" in task_description.lower()) and
            "youtube" in task_description.lower() and
            not any(word in task_description.lower() for word in ["search", "find", "look for", "then", "after"])
        )
        
        # If it's a simple YouTube task and no URL provided, ask Gemini to find it
        if simple_youtube_task and not url_match:
            logger.info("🔍 Simple YouTube task detected - Gemini searching for direct link...")
            
            # Extract song/video name from task
            search_query = task_description.lower()
            for remove in ["play", "on youtube", "youtube", "open", "show me", "find"]:
                search_query = search_query.replace(remove, "")
            search_query = search_query.strip() + " youtube"
            
            logger.info(f"🔍 Gemini searching: {search_query}")
            search_result = await gemini_web_search(search_query)
            logger.info(f"🔍 Gemini search result: {search_result[:200]}...")
            
            # Extract URL from Gemini's response
            url_match = re.search(youtube_url_pattern, search_result)
            if url_match:
                youtube_url = url_match.group(0)
                logger.info(f"✅ Gemini found YouTube URL: {youtube_url}")
                
                # Navigate directly
                await loop.run_in_executor(_executor, lambda: navigate_to_url(youtube_url))
                await asyncio.sleep(3)
                
                # Take screenshot and verify with Gemini
                screenshot_path = await loop.run_in_executor(_executor, take_screenshot)
                
                verification = await gemini_analyze_and_decide(
                    screenshot_path,
                    task_description,
                    f"Navigated to {youtube_url}"
                )
                
                if verification.get("action") == "complete" and verification.get("success"):
                    return verification.get("message", "YouTube video opened successfully")
                else:
                    # Continue with complex workflow if simple approach failed
                    logger.info("⚠️ Simple approach incomplete, switching to complex workflow...")
            else:
                logger.warning("⚠️ Gemini couldn't find direct URL, using complex workflow...")
        
        # Complex workflow: Gemini-controlled step-by-step automation
        logger.info("🎯 Starting Gemini-controlled complex browser automation...")
        
        # Track consecutive verify actions to prevent loops
        consecutive_verifies = 0
        
        while iteration < max_iterations:
            iteration += 1
            logger.info(f"🔄 Iteration {iteration}/{max_iterations}")
            
            # Take screenshot
            screenshot_path = await loop.run_in_executor(_executor, take_screenshot)
            logger.info(f"📸 Screenshot taken: {screenshot_path}")
            
            # Build context from history
            context = "\n".join(context_history[-5:]) if context_history else ""
            
            # Ask Gemini to analyze and decide next action
            decision = await gemini_analyze_and_decide(screenshot_path, task_description, context)
            action = decision.get("action")
            
            logger.info(f"🧠 Gemini decided: {action} - {decision}")
            
            # Track consecutive verify actions
            if action == "verify":
                consecutive_verifies += 1
                if consecutive_verifies > 2:
                    logger.warning("⚠️ Too many consecutive verify actions, forcing completion")
                    return "Task appears complete (verification loop detected, assuming success)"
            else:
                consecutive_verifies = 0
            
            # Execute Gemini's decision
            if action == "search_web":
                # Gemini wants to search for information
                query = decision.get("query", "")
                logger.info(f"🔍 Gemini searching web: {query}")
                result = await gemini_web_search(query)
                context_history.append(f"Searched web for '{query}': {result[:100]}")
                
                # Check if Gemini found a URL to navigate to
                url_match = re.search(r'https?://[^\s]+', result)
                if url_match:
                    url = url_match.group(0)
                    logger.info(f"🌐 Auto-navigating to found URL: {url}")
                    await loop.run_in_executor(_executor, lambda: navigate_to_url(url))
                    await asyncio.sleep(2)
                    context_history.append(f"Navigated to {url}")
            
            elif action == "navigate":
                url = decision.get("url", "")
                logger.info(f"🌐 Gemini navigating to: {url}")
                await loop.run_in_executor(_executor, lambda: navigate_to_url(url))
                await asyncio.sleep(2)
                context_history.append(f"Navigated to {url}")
            
            elif action == "click":
                x = decision.get("x", 0)
                y = decision.get("y", 0)
                reason = decision.get("reason", "")
                logger.info(f"🖱️  Gemini clicking ({x}, {y}): {reason}")
                await loop.run_in_executor(_executor, lambda: click_at_coordinates(x, y))
                await asyncio.sleep(1)
                context_history.append(f"Clicked at ({x}, {y}): {reason}")
            
            elif action == "type":
                text = decision.get("text", "")
                reason = decision.get("reason", "")
                logger.info(f"⌨️  Gemini typing: '{text}' - {reason}")
                await loop.run_in_executor(_executor, lambda: type_text(text))
                await asyncio.sleep(0.5)
                context_history.append(f"Typed: {text}")
            
            elif action == "press_key":
                key = decision.get("key", "Enter")
                reason = decision.get("reason", "")
                logger.info(f"⏎ Gemini pressing key: {key} - {reason}")
                await loop.run_in_executor(_executor, lambda: press_key(key))
                await asyncio.sleep(1)
                context_history.append(f"Pressed: {key}")
            
            elif action == "wait":
                seconds = decision.get("seconds", 2)
                reason = decision.get("reason", "")
                logger.info(f"⏳ Gemini waiting {seconds}s: {reason}")
                await asyncio.sleep(seconds)
                context_history.append(f"Waited {seconds}s")
            
            elif action == "verify":
                question = decision.get("question", "")
                expected = decision.get("expected", "yes")
                logger.info(f"✓ Gemini wants to verify: {question}")
                
                # Take a fresh screenshot and ask Gemini to answer the verification question
                screenshot_path = await loop.run_in_executor(_executor, take_screenshot)
                
                # Create a simple yes/no verification prompt
                img = Image.open(screenshot_path)
                verification_prompt = f"""{question}

Analyze this screenshot and answer with ONLY a JSON response:
{{"answer": "yes"}} - if the answer is yes
{{"answer": "no"}} - if the answer is no

Expected answer: {expected}

Be concise. Respond ONLY with JSON."""

                verify_response = await loop.run_in_executor(
                    None, 
                    lambda: gemini_model.generate_content([verification_prompt, img])
                )
                verify_text = verify_response.text.strip()
                
                logger.info(f"📋 Gemini verification response: {verify_text}")
                
                # Parse verification answer
                try:
                    if "yes" in verify_text.lower():
                        answer = "yes"
                    elif "no" in verify_text.lower():
                        answer = "no"
                    else:
                        # Try to parse JSON
                        verify_json = json.loads(verify_text.replace("```json", "").replace("```", "").strip())
                        answer = verify_json.get("answer", "unknown")
                    
                    logger.info(f"✅ Verification result: {answer}")
                    
                    # If verification passed, complete the task
                    if answer.lower() == expected.lower():
                        logger.info(f"✅ Verification PASSED: {question}")
                        return f"Task completed successfully. Verification: {question} - {answer}"
                    else:
                        logger.warning(f"⚠️ Verification FAILED: Expected {expected}, got {answer}")
                        context_history.append(f"Verification failed: {question} - expected {expected}, got {answer}")
                        # Continue to let Gemini fix the issue
                
                except Exception as e:
                    logger.error(f"Failed to parse verification: {e}")
                    context_history.append(f"Verification check: {question}")
            
            elif action == "complete":
                message = decision.get("message", "Task completed")
                success = decision.get("success", True)
                logger.info(f"✅ Gemini reports: {message} (success={success})")
                return message
            
            elif action == "error":
                error_msg = decision.get("message", "Unknown error")
                logger.error(f"❌ Gemini encountered error: {error_msg}")
                return f"Error: {error_msg}"
            
            else:
                logger.warning(f"⚠️  Unknown action from Gemini: {action}")
                context_history.append(f"Unknown action: {action}")
            
            # Prevent infinite loops
            if iteration >= max_iterations - 1:
                logger.warning("⚠️  Max iterations reached")
                return f"Task incomplete after {max_iterations} steps. Last action: {action}"
        
        return "Browser automation completed"
    
    except Exception as e:
        logger.error(f"❌ Browser automation failed: {e}", exc_info=True)
        return f"Browser automation error: {str(e)}"


def close_browser():
    """Close browser and save session."""
    global _playwright, _context, _page
    if _context:
        _context.close()
        _context = None
        _page = None
    if _playwright:
        _playwright.stop()
        _playwright = None
    logger.info("Browser closed, session saved")
