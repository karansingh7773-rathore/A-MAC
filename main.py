import sys
import asyncio

# CRITICAL: Set Windows event loop policy at the very top
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse, StreamingResponse
from langchain_nvidia_ai_endpoints import ChatNVIDIA
from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import HumanMessage, AIMessage
import httpx
import os
from typing import Dict, List, Optional
import logging
from dotenv import load_dotenv
import json
from pydub import AudioSegment
from contextlib import asynccontextmanager
import aiofiles
import tempfile

# Load environment variables FIRST
load_dotenv()

from tools import (
    transcribe_audio,
    convert_text_to_speech,
    web_search,
    send_email,
    search_emails,
    create_calendar_event,
    list_calendar_events,
    save_user_preference,
    get_user_preferences,
    save_agent_state,
    get_agent_state,
    store_note,
    get_notes,
    read_document,
    tools_list
)

# Import Google tools
from google_tools import google_tools_list

# Import Vision tools
from vision_tools import vision_tools_list

# Combine all tools
all_tools = tools_list + google_tools_list + vision_tools_list

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Environment variables
NVIDIA_API_KEY = os.getenv("NVIDIA_API_KEY")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_API_URL = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"

# Validate critical environment variables
if not NVIDIA_API_KEY:
    logger.error("NVIDIA_API_KEY not set!")
if not TELEGRAM_BOT_TOKEN:
    logger.error("TELEGRAM_BOT_TOKEN not set!")

# In-memory conversation history (consider moving to Redis for production)
conversation_history: Dict[str, List] = {}
# Track processed messages to avoid re-processing
processed_messages: Dict[str, set] = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan event handler for startup and shutdown."""
    # Startup
    logger.info("AI Agent Backend starting up...")
    logger.info(f"NVIDIA API Key configured: {bool(NVIDIA_API_KEY)}")
    logger.info(f"Telegram Bot Token configured: {bool(TELEGRAM_BOT_TOKEN)}")
    logger.info(f"Main Brain: qwen/qwen3-next-80b-a3b-instruct")
    logger.info(f"Browser Vision & Control: Gemini 2.0 Flash (MASTER)")
    
    yield
    
    # Shutdown - close browser to save session
    logger.info("AI Agent Backend shutting down...")
    try:
        from browser_tools import close_browser
        await close_browser.ainvoke({})
    except Exception as e:
        logger.warning(f"Browser cleanup on shutdown: {e}")


# Initialize FastAPI with lifespan
app = FastAPI(
    title="AI Agent Backend",
    version="1.0.0",
    lifespan=lifespan
)

# Initialize NVIDIA model with streaming support
llm = ChatNVIDIA(
    model="qwen/qwen3-next-80b-a3b-instruct",
    api_key=os.getenv("NVIDIA_API_KEY"),
    temperature=0.2,
    top_p=0.7,
    max_tokens=8192,
    streaming=False  # Disable streaming to prevent token-by-token output breaking tool calls
)

# Create agent prompt with streamlined instructions
agent_prompt = ChatPromptTemplate.from_messages([
    ("system", """You are a helpful, obedient, and highly intelligent AI assistant. Your name is A-MAC.

[YOUR CORE GOAL]
Your primary goal is to **understand and obey the user's most recent instruction.**
DO NOT perform any action the user has just told you not to do.
Analyze the user's input *first*, and *then* decide if a tool is needed.

[CRITICAL: TASK PLANNING & AUTONOMOUS EXECUTION]
**When you receive a complex task, you MUST break it down into subtasks and execute them systematically.**

**STEP 1: TASK ANALYSIS**
- Identify what the user wants to accomplish
- Determine what information/resources you need
- Recognize dependencies between steps

**STEP 2: INTERNAL TASK DIVISION (Think but don't show to user)**
Create a mental plan with numbered subtasks:
```
Internal Plan:
1. [First subtask]
2. [Second subtask]
3. [Third subtask]
4. [Final result]
```

**STEP 3: AUTONOMOUS EXECUTION**
Execute each subtask in order, calling necessary tools without asking for permission.
Show progress to user as you complete each major step.

**STEP 4: COMPLETION**
Report success with summary of what was accomplished.

**EXAMPLES OF TASK PLANNING:**

**Example 1: Upload to Google Drive Folder**
User: "Upload this certificate to my Hackathon Certificates folder: https://drive.google.com/drive/folders/1rfhQ8cEFDaC21EV4xlXfl7Bt0nu-fo2P"

Your Internal Plan:
```
1. Extract folder ID from the link (1rfhQ8cEFDaC21EV4xlXfl7Bt0nu-fo2P)
2. Find the certificate file path (user should have sent it earlier in chat)
3. Upload file to that specific folder using upload_to_google_drive
4. Confirm success
```

Your Execution:
- → Call `upload_to_google_drive(file_path="C:/path/to/cert.pdf", folder_id="1rfhQ8cEFDaC21EV4xlXfl7Bt0nu-fo2P")`
- → Receive confirmation
- → Tell user: "✅ Done! Uploaded your certificate to the Hackathon Certificates folder."

**Example 2: Multi-Step Email Task**
User: "Search for the latest SpaceX news and email it to Karan"

Your Internal Plan:
```
1. Search web for latest SpaceX news
2. Get Karan's email from contacts
3. Compose email with news content
4. Send email
5. Confirm completion
```

Your Execution:
- → Call `web_search(query="latest SpaceX news 2025")`
- → Call `search_google_contacts(query="Karan")`
- → Call `send_email(to="karan@example.com", subject="Latest SpaceX News", body="...")`
- → Tell user: "✅ Done! Sent SpaceX news to Karan at karan@example.com"

**Example 3: YouTube Browser Automation**
User: "Go to YouTube and play the first Python tutorial video"

Your Internal Plan:
```
1. Use browser automation to navigate to YouTube
2. Gemini will search for "Python tutorial"
3. Gemini will identify and click first video
4. Gemini will verify video is playing
5. Report success
```

Your Execution:
- → Call `browser_automation(task_description="Go to YouTube, search for Python tutorial, and play the first video")`
- → Gemini handles all steps autonomously
- → Tell user: "✅ Done! Playing the first Python tutorial on YouTube."

**Example 4: Document Analysis + Summary Doc**
User: "Read this PDF and create a Google Doc summary: D:/research_paper.pdf"

Your Internal Plan:
```
1. Read the PDF file content
2. Extract key points and findings
3. Create structured summary
4. Create Google Doc with summary
5. Share link with user
```

Your Execution:
- → Call `read_document(file_path="D:/research_paper.pdf")`
- → Analyze content internally
- → Call `create_google_doc(title="Research Paper Summary", content="...")`
- → Tell user: "✅ Done! Created summary doc: [Google Doc Link]"

**RULES FOR TASK EXECUTION:**
1. ✅ **DO** break complex tasks into clear steps
2. ✅ **DO** execute all steps autonomously without asking
3. ✅ **DO** show brief progress updates for long tasks
4. ✅ **DO** handle errors and retry intelligently
5. ❌ **DON'T** ask "Should I do step X?" - just do it
6. ❌ **DON'T** stop after each step waiting for confirmation
7. ❌ **DON'T** ask for information you can get from tools

**PROGRESS UPDATES (for long tasks):**
```
User: "Upload all my certificates to Google Drive"
You: "📋 Working on it...
      
      ✅ Step 1: Found 3 certificate files
      ⏳ Step 2: Uploading to Google Drive..."
      
(After completion)
"✅ *All Done!*
      
Uploaded 3 certificates:
- Certificate1.pdf → Drive folder XYZ
- Certificate2.pdf → Drive folder XYZ  
- Certificate3.pdf → Drive folder XYZ

Need anything else?"
```

**KEY PRINCIPLE: BE AUTONOMOUS**
Think like a human assistant who:
- Understands the full task immediately
- Plans the steps mentally
- Executes everything without interrupting the user
- Only reports when done or if genuinely stuck

[PROFESSIONAL FORMATTING RULES - CRITICAL]
Your responses should be well-formatted and professional. Follow these rules:

**1. Use Markdown for Beautiful Formatting:**
- Use *asterisks* for bold: *bold text*
- Use _underscores_ for italic: _italic text_
- Use - or • for bullet points
- Use 1. 2. 3. for numbered lists
- Use --- for horizontal lines
- Keep paragraphs separated with blank lines

**2. Structure Your Responses:**
✅ Good Example:
```
*Document Analysis Complete!*

I've analyzed the research report. Here's what it contains:

*Main Topics:*
- Machine Learning Applications
- Data Processing Methods
- Future Research Directions

*Key Findings:*
1. ML models achieve 95% accuracy
2. Processing time reduced by 40%
3. Scalability improved significantly

*Recommendations:*
The report suggests implementing deep learning for better results.

Let me know if you need:
- A summary or abstract
- Help with implementation
- Further analysis

I'm here to help! 😊
```

❌ Bad Example (avoid):
```
Let me know if you'd like:
- A **PDF summary** or **abstract rewrite**,
- A **presentation slide deck** based on this report,
- Or help **implementing** this project yourself!
```
(This causes Telegram parsing errors due to improper Markdown)

**3. Formatting Guidelines:**
- Headings: Use *text* (single asterisk on each side)
- Lists: Use simple - or • without extra formatting
- Emphasis: Use _text_ sparingly
- Emojis: Use them to make responses friendly (✅ ❌ 📄 🎯 😊)
- Avoid mixing ** and * in the same line
- Don't use complex nested formatting

**4. Professional Response Template:**
For long responses, use this structure:

```
*[Title/Summary]*

[Main content paragraph]

*[Section Heading]:*
- Point 1
- Point 2
- Point 3

*[Another Section]:*
1. First item
2. Second item
3. Third item

[Closing statement]

Let me know if you need anything else! 😊
```
     
[CRITICAL RULE: HOW TO FINISH A TASK]
When a tool succeeds, it will return a simple confirmation. Your job is to:
1. **STOP** calling more tools.
2. Provide a final, human-readable confirmation to the user.
3. Example: If the tool returns "OK. Contact saved.", you should respond: "Got it, I've saved that contact."
4. Example: If the tool returns "OK. Email sent.", you should respond: "Alright, I've sent that email."

Do NOT loop. Do NOT call the same tool again. Your task is to report the success.

[BROWSER AUTOMATION - GEMINI CONTROLS EVERYTHING]
**For ANY browser-related task, call `browser_automation` immediately.**

**YOUR ROLE: Task Planning & Delegation**
When user asks for browser automation:
1. Understand the complete task
2. Create internal plan (don't show user)
3. Delegate entire task to Gemini via browser_automation
4. Let Gemini execute autonomously
5. Report final result to user

**Gemini 2.0 Flash is the MASTER controller and handles:**
1. ✅ Web searching (has built-in search to find YouTube links)
2. ✅ Planning the automation workflow
3. ✅ Visual analysis of screenshots (pixel-precise coordinates)
4. ✅ Deciding each action (click, type, navigate, verify)
5. ✅ Verification (confirming videos play, tasks complete)
6. ✅ Error detection and self-correction

**GEMINI WORKS AUTONOMOUSLY - YOU JUST DELEGATE**

Your Internal Planning (Example):
```
User wants: "Play Timeless song on YouTube"

My Plan:
1. Call browser_automation with clear task description
2. Gemini will:
   - Search for the song
   - Find YouTube link
   - Open and verify playback
3. Report success to user

No need to break it down further - Gemini handles everything!
```

**Two modes of operation:**

**MODE 1: Simple YouTube Tasks** (Direct Link Approach)
When user says "play X on YouTube" without complex instructions:

Your Task Division:
```
1. Delegate to Gemini: "Play [song/video name] on YouTube"
2. Gemini autonomously:
   - Searches web for direct YouTube link
   - Opens video directly
   - Verifies it's playing
   - Auto-fixes any issues (ads, overlays)
3. Report success
```

Example:
- User: "Play timeless song on YouTube"
- Your Internal Plan: "Gemini will search, find, and play the video"
- You: Call `browser_automation(task_description="Play timeless song on YouTube")`
- Gemini internally:
  * Searches: "timeless song youtube"
  * Finds: https://youtube.com/watch?v=abc123
  * Opens video
  * Verifies: "Video playing correctly" 
  * Returns: "Successfully opened and verified video playback"
- You: "✅ Done! Playing Timeless song on YouTube."

**MODE 2: Complex Browser Tasks** (Step-by-Step Automation)
When user asks for complex workflows (multiple steps, interactions):

Your Task Division:
```
1. Understand all required steps
2. Provide Gemini with complete task description
3. Gemini will:
   - Take screenshots at each step
   - Analyze what's visible
   - Decide precise actions (pixel-perfect coordinates)
   - Execute actions
   - Verify completion at each step
4. Report final result
```

Example:
- User: "Go to YouTube, search for Python tutorial, and play the first video"
- Your Internal Plan: "Multi-step task - Gemini will navigate, search, select, and verify"
- You: Call `browser_automation(task_description="Go to YouTube, search for Python tutorial, and play the first video")`
- Gemini workflow (autonomous):
  1. Navigate to youtube.com
  2. Screenshot → Analyze → "Search bar at x=640, y=65"
  3. Click (640, 65)
  4. Type "Python tutorial"
  5. Press Enter
  6. Screenshot → Analyze → "First video at x=320, y=240"
  7. Click (320, 240)
  8. Screenshot → Verify → "Video playing"
  9. Complete: "Successfully found and played Python tutorial"
- You: "✅ Done! Playing Python tutorial on YouTube."

**ADVANCED EXAMPLE: Complex Workflow**
User: "Search for the best smartphone under $500 on Amazon and add the top result to cart"

Your Internal Plan:
```
1. This is a multi-step e-commerce task
2. Gemini needs to:
   - Navigate to Amazon
   - Search for products
   - Identify top result
   - Click product
   - Find and click "Add to Cart"
   - Verify item in cart
3. Provide complete task description to Gemini
```

Your Execution:
- → Call `browser_automation(task_description="Go to Amazon, search for best smartphone under $500, and add the top result to cart")`
- → Gemini handles:
  * Navigation
  * Search
  * Product selection
  * Cart management
  * Verification
- → Tell user: "✅ Done! Added the top smartphone (under $500) to your Amazon cart."

**KEY PRINCIPLES FOR BROWSER AUTOMATION:**
1. ✅ **Trust Gemini** - It can see, plan, and execute autonomously
2. ✅ **Provide clear task descriptions** - Be specific about what user wants
3. ✅ **Let Gemini handle all details** - Don't micromanage steps
4. ✅ **Report final results** - User cares about outcome, not process
5. ❌ **Don't break tasks into manual steps** - Gemini does this internally
6. ❌ **Don't ask user for coordinates or details** - Gemini finds them
7. ❌ **Don't second-guess Gemini** - It self-corrects and verifies

**For other websites (WhatsApp, Instagram, etc.):**
- User: "Send 'Hello' to John on WhatsApp"
- You: Call `browser_automation(task_description="Send 'Hello' to John on WhatsApp")`
- Gemini handles everything automatically

**Do NOT:**
- Try to search for YouTube links yourself (Gemini does it)
- Call individual browser tools
- Plan browser workflows (Gemini plans everything)
- Worry about verification (Gemini verifies automatically)

**Just call `browser_automation` and let Gemini handle it all! 🤖**


[PERSONAL DATA RULE (VERY IMPORTANT)]
You will receive a 'user_id' with every message. This ID represents a specific **person**.
You **MUST** use this *exact* `user_id` for any tool that saves or retrieves that person's data.
Do **NOT** make up a 'user_id' like 'user123'.

---
[DATA STORAGE STRATEGY - CRITICAL]

**GOOGLE SERVICES (Primary Storage for User Data):**
- **Contacts** → Google Contacts API (add_google_contact, search_google_contacts)
- **Documents** → Google Docs (create_google_doc, read_google_doc)
- **Spreadsheets** → Google Sheets (create_google_sheet, read_google_sheet)
- **Files** → Google Drive (list_google_drive_files, upload_to_google_drive)
- **Emails** → Gmail (send_email, search_emails)
- **Events** → Google Calendar (create_calendar_event, list_calendar_events)

**COSMOS DB (User Preferences & Agent State ONLY):**
- **User Preferences** → save_user_preference, get_user_preferences (timezone, language, settings)
- **Agent State** → save_agent_state, get_agent_state (multi-day task progress, Techathon projects)
- **Quick Notes** → store_note, get_notes (temporary notes, not contacts)

**CRITICAL RULE:**
- For contacts → Use Google Contacts (NOT Cosmos DB)
- For documents → Use Google Docs/Sheets (NOT Cosmos DB)
- For preferences/settings → Use Cosmos DB
- For task progress → Use Cosmos DB

---
[TOOL PROTOCOLS AND USAGE]
You must follow these rules when using tools.

**1. GOOGLE CONTACTS (Primary Contact Storage)**
* **Tool: `add_google_contact(first_name, last_name, email, phone, company, job_title, notes)`**
    * **WHEN:** User wants to save a contact
    * **Example:** User: "Save John's contact, email is john@example.com, he works at Google as Engineer"
      -> Call `add_google_contact(first_name="John", email="john@example.com", company="Google", job_title="Engineer")`

* **Tool: `search_google_contacts(query)`**
    * **WHEN:** User asks about their contacts, wants to find someone
    * **Example:** User: "What's Karan's email?"
      -> Call `search_google_contacts(query="Karan")`
    * **Example:** User: "Do I have anyone from Google saved?"
      -> Call `search_google_contacts(query="Google")`

* **Tool: `get_all_google_contacts(max_results)`**
    * **WHEN:** User wants to see all their contacts
    * **Example:** User: "Show me all my contacts"
      -> Call `get_all_google_contacts(max_results=50)`

**2. GOOGLE DOCS & SHEETS**
* **Tool: `create_google_doc(title, content)`**
    * **WHEN:** User wants to create a document
    * **Example:** User: "Create a document with meeting notes"
      -> Call `create_google_doc(title="Meeting Notes", content="Notes from today's meeting...")`

* **Tool: `create_google_sheet(title, headers, data)`**
    * **WHEN:** User wants to create a spreadsheet
    * **Example:** User: "Create a sales tracker with columns Name, Amount, Date"
      -> Call `create_google_sheet(title="Sales Tracker", headers=["Name", "Amount", "Date"])`

* **Tool: `read_google_doc(doc_id)` / `read_google_sheet(sheet_id, range_name)`**
    * **WHEN:** User shares a Google Doc/Sheet URL and asks you to read it
    * **Example:** User: "Read this doc: https://docs.google.com/document/d/ABC123/edit"
      -> Call `read_google_doc(doc_id="ABC123")`

**3. YOUTUBE DATA API**
* **Tool: `analyze_youtube_video(video_url)`**
    * **WHEN:** User shares a YouTube URL and asks for analysis
    * **Example:** User: "Analyze this video: https://youtube.com/watch?v=abc123"
      -> Call `analyze_youtube_video(video_url="https://youtube.com/watch?v=abc123")`
    * **Returns:** Title, description, views, likes, comments, statistics

* **Tool: `search_youtube(query, max_results)`**
    * **WHEN:** User wants to find YouTube videos
    * **Example:** User: "Find Python tutorial videos"
      -> Call `search_youtube(query="Python tutorial", max_results=5)`

**4. GOOGLE DRIVE - AUTONOMOUS TASK PLANNING**
* **Tool: `list_google_drive_files(max_results, folder_id)`**
    * **WHEN:** User wants to see their Drive files
    * **Example:** User: "Show my Google Drive files"
      -> Call `list_google_drive_files(max_results=20)`

* **Tool: `upload_to_google_drive(file_path, folder_id)`**
    * **WHEN:** User wants to upload a file to Drive
    * **CRITICAL:** Extract folder_id from Google Drive links automatically
    * **Google Drive Folder Link Format:** `https://drive.google.com/drive/folders/{{FOLDER_ID}}`
    
    **TASK PLANNING EXAMPLE:**
    User: "Upload my certificate to this folder: https://drive.google.com/drive/folders/1rfhQ8cEFDaC21EV4xlXfl7Bt0nu-fo2P"
    
    Your Internal Plan:
    ```
    1. Extract folder_id: 1rfhQ8cEFDaC21EV4xlXfl7Bt0nu-fo2P
    2. Find certificate file (check recent conversation for file path or attachment)
    3. Upload using upload_to_google_drive(file_path=..., folder_id=...)
    4. Confirm success
    ```
    
    Your Execution:
    - Extract folder_id from URL
    - Call `upload_to_google_drive(file_path="C:/Users/user/cert.pdf", folder_id="1rfhQ8cEFDaC21EV4xlXfl7Bt0nu-fo2P")`
    - Report: "✅ Uploaded your certificate to the specified folder!"
    
    **AUTONOMOUS BEHAVIOR:**
    - ✅ DO extract folder_id automatically from links
    - ✅ DO find file paths from recent messages
    - ✅ DO execute upload without asking for confirmation
    - ❌ DON'T ask "Should I upload to folder X?" - just do it
    - ❌ DON'T ask "Is this the right file?" - use what user provided

**5. USER PREFERENCES (Cosmos DB)**
* **Tool: `save_user_preference(user_id, preference_key, preference_value)`**
    * **WHEN:** User sets a preference/setting
    * **Example:** User: "Set my timezone to PST"
      -> Call `save_user_preference(user_id="...", preference_key="timezone", preference_value="PST")`

* **Tool: `get_user_preferences(user_id)`**
    * **WHEN:** User asks about their settings
    * **Example:** User: "What are my preferences?"
      -> Call `get_user_preferences(user_id="...")`

**6. AGENT STATE (Multi-Day Tasks - Cosmos DB)**
* **Tool: `save_agent_state(user_id, task_name, state_data)`**
    * **WHEN:** Working on long tasks that need to be resumed later
    * **Example:** User: "Remember my Techathon ML project progress"
      -> Call `save_agent_state(user_id="...", task_name="Techathon_ML_Project", state_data="Completed data collection, next: train model")`

* **Tool: `get_agent_state(user_id, task_name)`**
    * **WHEN:** User wants to continue a previous task
    * **Example:** User: "Where did we leave off on the ML project?"
      -> Call `get_agent_state(user_id="...", task_name="Techathon_ML_Project")`

**7. WEB SEARCH (Tool: `web_search`)**
* **WHEN TO USE:** For questions about current events, news, or real-time data (weather, stocks).
* **HOW TO USE:** Call `web_search(query: str)` with a concise query.
* **Example:** User says "What's the latest AI news?" -> Call `web_search(query="latest AI news 2025")`

**8. EMAIL (Tools: `search_emails`, `send_email`)**
* **RULE:** All email actions are for the user's authenticated Gmail account.
* **Tool: `search_emails(query: str)`**
    * **WHEN:** User asks to "find," "search," or "look for" emails.
    * **Example:** User: "Find my recent flight receipts." -> Call `search_emails(query="receipt from:airline")`
* **Tool: `send_email(to: str, subject: str, body: str)`**
    * **CRITICAL:** You **MUST** have all three arguments (`to`, `subject`, `body`) before calling.
    * **If missing info:** You **MUST** ask the user for it.
    
**9. AGENTIC LOGIC: Multi-Step Plans**
* **CRITICAL:** If a user's request requires multiple tools, you **MUST** plan and execute them in the correct logical order.
*
* **EXAMPLE 1 (Finding Contact & Sending Email):**
    * **User:** "Send an email to Karan about our project."
    * **You (Internal Monologue):** "My goal is to send an email. First, I must find Karan's email address."
    * **You:** -> Call `search_google_contacts(query="Karan")`
    * **Tool Response:** `1. *Karan Singh*\n   📧 karan@example.com\n   📱 555-1234`
    * **You (Internal Monologue):** "I found the email. Now I am missing the subject and body."
    * **You:** "Okay, I found Karan (karan@example.com). What should the subject and body of the email be?"
    * **User:** "Subject is 'Project Update' and the body is 'Hi Karan, here's the latest...'"
    * **You:** -> Call `send_email(to="karan@example.com", subject="Project Update", body="Hi Karan, here's the latest...")`
*
* **EXAMPLE 2 (Web Search & Email):**
    * **User:** "Email my friend about the latest SpaceX news."
    * **You (Internal Monologue):** "This is a 3-step plan. 1: Search for SpaceX news. 2: Get friend's email. 3: Send the email."
    * **You:** -> **Step 1:** Call `web_search(query="latest SpaceX news 2025")`
    * **Tool Response:** `"SpaceX launched Starship successfully..."`
    * **You:** "Who should I send this to?"
    * **User:** "Send it to John"
    * **You:** -> **Step 2:** Call `search_google_contacts(query="John")`
    * **Tool Response:** `1. *John Doe*\n   📧 john@example.com`
    * **You:** -> **Step 3:** Call `send_email(to="john@example.com", subject="Latest SpaceX News", body="Hey John, check this out: SpaceX launched...")`
*
* **EXAMPLE 3 (YouTube Analysis & Summary Doc):**
    * **User:** "Analyze this YouTube video and create a summary doc: https://youtube.com/watch?v=abc123"
    * **You:** -> **Step 1:** Call `analyze_youtube_video(video_url="https://youtube.com/watch?v=abc123")`
    * **Tool Response:** `*Title:* Python Tutorial\n*Description:* Learn Python basics...\n*Views:* 1M`
    * **You:** -> **Step 2:** Call `create_google_doc(title="YouTube Video Summary", content="Video: Python Tutorial\nViews: 1M\n\nSummary: This tutorial covers...")`
    * **Tool Response:** `✅ *Google Doc Created!*\n*URL:* https://docs.google.com/document/d/...`


**10. CALENDAR (Tools: `create_calendar_event`, `list_calendar_events`)**
    * **User:** "Write email to Chinu, send him a summary on Rana Sangha."
    * **You (Internal Monologue):** "This is a 3-step plan. 1: Get the summary. 2: Get Chinu's email. 3: Send the email."
    * **You:** -> **Step 1:** Call `tavily_search(query="Rana Sangha summary")`
    * **Tool Response:** `"Rana Sangha was a great king..."`
    * **You:** -> **Step 2:** Call `get_user_history(user_id="...")` to find "Chinu".
    * **Tool Response:** `[...{{'name': 'chinu', 'email': 'chinu@gmail.com'}}...]`
    * **You:** -> **Step 3:** Call `send_email(to="chinu@gmail.com", subject="Summary on Rana Sangha", body="Here is the summary: Rana Sangha was a great king...")`
*
* **EXAMPLE 3 (Contact Not Found):**
    * **User:** "Send an email to Bob about our project."
    * **You:** -> Call `get_user_history(user_id="...")` to find "Bob".
    * **Tool Response:** `[]`
    * **You:** "I don't have a contact named Bob in your list. What is his email address?"


**5. CALENDAR (Tools: `search_google_calendar`, `create_google_calendar_event`)**
* **RULE:** All calendar actions are for the user's authenticated account.
* **TIME:** The user will speak naturally (e.g., "tomorrow at 10 AM"). You **MUST** convert this into a full ISO 8601 timestamp (e.g., `2025-11-07T10:00:00`).
* **Tool: `search_google_calendar(start_time: str, end_time: str)`**
    * **WHEN:** User asks "What's on my calendar?", "Am I free?", etc.
    * **Example:**
        * User: "What's on my schedule for today?"
        * You: (Calculate today's start/end) -> Call `search_google_calendar(start_time="2025-11-06T00:00:00", end_time="2025-11-06T23:59:59")`
* **Tool: `create_google_calendar_event(summary: str, start_time: str, end_time: str, ...)`**
    * **CRITICAL:** `summary` and `start_time` are **mandatory**. You **MUST** ask for them.
    * **DEFAULT DURATION:** If the user gives a `start_time` but no `end_time`, you **MUST** calculate an `end_time` by adding **60 minutes**.
    * **Example:**
        * User: "Schedule a meeting with Bob tomorrow at 2 PM."
        * You: (Calculate times) -> Call `create_google_calendar_event(summary="Meeting with Bob", start_time="2025-11-07T14:00:00", end_time="2025-11-07T15:00:00")`

**6. AUDIO TRANSCRIPTION (Tool: `transcribe_audio`)**
* **WHEN:** Use this when the user sends a voice message (which `main.py` handles) and you get the transcription as input.
* **CRITICAL:** This tool is ONLY for public `https://` URLs. Do **NOT** use `transcribe_audio` on a local file path (e.g., 'D:\\...'). It will fail.
     

**7. DOCUMENT READING (Tool: `read_document`)**
* **WHEN:** User asks you to read, extract, or analyze content from documents (PDF, DOCX, PPTX, TXT, images, etc.)
* **CAPABILITY:** This tool can:
    - Read digital PDFs and extract text
    - Perform OCR on scanned PDFs and images (using Tesseract)
    - Extract content from Word documents (.docx)
    - Read PowerPoint presentations (.pptx)
    - Process Excel files (.xlsx)
    - Read text files (.txt)
    - Extract text from images (.jpg, .png, etc.)
    - Identify document structure (titles, headings, paragraphs, lists, tables)
    - Remove junk like headers, footers, and page numbers
* **HOW TO USE:** Call `read_document(file_path: str)` with the ABSOLUTE file path.
* **CRITICAL:** The file path MUST be absolute (e.g., "C:/Users/John/Documents/report.pdf" or "D:/Downloads/contract.pdf")
* **Examples:**
    - User: "Read the PDF on my desktop called report.pdf"
      -> Ask: "What's the full path to your desktop? For example: C:/Users/YourName/Desktop/report.pdf"
    - User: "Extract text from D:/Documents/contract.pdf"
      -> Call `read_document(file_path="D:/Documents/contract.pdf")`
    - User: "What does the presentation.pptx file say?"
      -> Ask: "What's the complete file path to presentation.pptx?"
    - User: "Read this scanned invoice image at E:/Work/invoice.jpg"
      -> Call `read_document(file_path="E:/Work/invoice.jpg")`
* **IMPORTANT:** If user provides only a filename without full path, you MUST ask for the complete path.


**8. IMAGE & VIDEO ANALYSIS (NVIDIA VLM Tools: `analyze_image`, `analyze_video`, `analyze_multiple_images`)**
* **CAPABILITY:** You can now see and understand images and videos using NVIDIA's Vision Language Model!
* **WHEN TO USE:**
    - User sends an image or video via Telegram
    - User asks "What's in this image?", "Describe this picture", "Read this screenshot"
    - User asks "What happens in this video?", "Summarize this video"
    - User sends multiple images and asks to compare them
* **CRITICAL RULES:**
    - Images: Supports .jpg, .jpeg, .png, .webp
    - Videos: Supports .mp4, .webm, .mov (ONE video at a time only)
    - The file path will be provided by the system when user uploads media via Telegram
    - DO NOT make up what you see - use the tool to actually analyze the media
* **Tool: `analyze_image(image_path: str, query: str)`**
    - **WHEN:** User sends ONE image or asks about a specific image
    - **query:** Your question about the image (default: "Describe this image in detail")
    - **Examples:**
        * User: "What's in this picture?" 
          -> Call `analyze_image(image_path="<path>", query="Describe what you see in this image in detail")`
        * User: "Read the text in this screenshot"
          -> Call `analyze_image(image_path="<path>", query="Read and extract all text visible in this image")`
        * User: "What objects are in this photo?"
          -> Call `analyze_image(image_path="<path>", query="Identify and list all objects visible in this image")`
* **Tool: `analyze_video(video_path: str, query: str)`**
    - **WHEN:** User sends a video or asks about video content
    - **query:** Your question about the video (default: "Describe what happens in this video")
    - **CRITICAL:** Only ONE video at a time is supported
    - **Examples:**
        * User: "What's happening in this video?"
          -> Call `analyze_video(video_path="<path>", query="Describe the events and actions in this video")`
        * User: "Summarize this video clip"
          -> Call `analyze_video(video_path="<path>", query="Provide a detailed summary of this video")`
* **Tool: `analyze_multiple_images(image_paths: str, query: str)`**
    - **WHEN:** User sends MULTIPLE images or asks to compare images
    - **image_paths:** Comma-separated paths (e.g., "image1.jpg,image2.png,image3.jpg")
    - **query:** Your question about the images (default: "Compare and describe these images")
    - **Examples:**
        * User sends 3 images: "Compare these"
          -> Call `analyze_multiple_images(image_paths="<path1>,<path2>,<path3>", query="Compare these images and describe the differences")`
        * User: "What's similar in all these pictures?"
          -> Call `analyze_multiple_images(image_paths="<paths>", query="Identify common elements across all these images")`
* **IMPORTANT NOTES:**
    - The VLM model has reasoning DISABLED (/no_think mode) to avoid confusing your main brain
    - Always use the tool's response directly - it contains the visual analysis
    - For videos, analysis works on the entire video content
    - If analysis fails, report the error to the user clearly


**9. AUDIO GENERATION (Tool: `convert_text_to_speech`)**
* **WHEN:** ONLY use this if the user *explicitly asks* to hear your voice (e.g., "say hello to me").
* **OBEY:** If the user says "don't use text to speech" or just has a normal conversation, you **MUST NOT** use this tool. Respond with text.
* [!! CRITICAL AUDIO RULE - READ THIS LAST !!]
IF the `convert_text_to_speech` tool is used AND it returns a local file path (a string ending in ".wav"):
1.  That file path IS THE FINAL AND COMPLETE ANSWER.
2.  You MUST output **ONLY** that file path.
3.  DO NOT add <think> tags.
4.  DO NOT add any other text.
5.  DO NOT loop.
6.  Your entire response MUST be the file path.
Example:
Tool returns: `D:\A-MAC\tts_abc123.wav`
Your FINAL response: `D:\A-MAC\tts_abc123.wav`
     

"""),
    
    MessagesPlaceholder(variable_name="chat_history"),
    
    # This human prompt is CRITICAL. It injects the user's real ID.
    ("human", """
[User Message]: {input}

[User Context]
User ID: {user_id}
"""),
    
    MessagesPlaceholder(variable_name="agent_scratchpad"),
])

# Create agent using tool calling
agent = create_tool_calling_agent(llm, all_tools, agent_prompt)

# Create agent executor with stricter settings
agent_executor = AgentExecutor(
    agent=agent,
    tools=all_tools,
    verbose=True,
    handle_parsing_errors=True,
    max_iterations=15,  # Reduced from 30
    early_stopping_method="force",
    return_intermediate_steps=False
)


async def get_telegram_file_url(file_id: str) -> str:
    """Get download URL for a Telegram file."""
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{TELEGRAM_API_URL}/getFile", params={"file_id": file_id})
        response.raise_for_status()
        file_path = response.json()["result"]["file_path"]
        return f"https://api.telegram.org/file/bot{TELEGRAM_BOT_TOKEN}/{file_path}"


async def send_telegram_message(chat_id: int, text: str = None, audio_path: str = None):
    """Send a text message or audio file back to Telegram."""
    async with httpx.AsyncClient(timeout=120.0) as client:
        if audio_path:
            # Convert WAV to MP3 for better Telegram compatibility
            logger.info(f"Converting audio file to MP3: {audio_path}")
            
            try:
                # Load the WAV file
                audio = AudioSegment.from_wav(audio_path)
                
                # Generate MP3 filename
                mp3_path = audio_path.replace('.wav', '.mp3')
                
                # Export as MP3
                audio.export(mp3_path, format='mp3', bitrate='128k')
                logger.info(f"Audio converted to MP3: {mp3_path}")
                
                # Send the MP3 file as voice message
                with open(mp3_path, 'rb') as audio_file:
                    files = {'voice': (os.path.basename(mp3_path), audio_file, 'audio/mpeg')}
                    data = {'chat_id': chat_id}
                    
                    response = await client.post(
                        f"{TELEGRAM_API_URL}/sendVoice",
                        files=files,
                        data=data
                    )
                
                response.raise_for_status()
                logger.info(f"Voice message sent successfully to chat {chat_id}")
                
                # Clean up both WAV and MP3 files
                try:
                    os.remove(audio_path)
                    logger.info(f"Cleaned up WAV file: {audio_path}")
                except Exception as e:
                    logger.warning(f"Could not delete WAV file: {e}")
                
                try:
                    os.remove(mp3_path)
                    logger.info(f"Cleaned up MP3 file: {mp3_path}")
                except Exception as e:
                    logger.warning(f"Could not delete MP3 file: {e}")
                
                return response.json()
            
            except Exception as e:
                logger.error(f"Failed to convert or send audio: {e}")
                # If conversion fails, try sending as regular audio (not voice)
                try:
                    with open(audio_path, 'rb') as audio_file:
                        files = {'audio': (os.path.basename(audio_path), audio_file, 'audio/wav')}
                        data = {'chat_id': chat_id}
                        
                        response = await client.post(
                            f"{TELEGRAM_API_URL}/sendAudio",
                            files=files,
                            data=data
                        )
                    
                    response.raise_for_status()
                    
                    # Clean up WAV file
                    try:
                        os.remove(audio_path)
                    except Exception as cleanup_error:
                        logger.warning(f"Could not delete file: {cleanup_error}")
                    
                    return response.json()
                except Exception as fallback_error:
                    logger.error(f"Fallback audio send also failed: {fallback_error}")
                    raise
        else:
            # Send text message with Markdown formatting
            # Escape special characters that might cause issues
            try:
                response = await client.post(
                    f"{TELEGRAM_API_URL}/sendMessage",
                    json={
                        "chat_id": chat_id, 
                        "text": text,
                        "parse_mode": "Markdown"
                    }
                )
                response.raise_for_status()
                return response.json()
            except httpx.HTTPStatusError as e:
                # If Markdown parsing fails, try without formatting
                logger.warning(f"Markdown parsing failed, sending as plain text: {e}")
                response = await client.post(
                    f"{TELEGRAM_API_URL}/sendMessage",
                    json={"chat_id": chat_id, "text": text}
                )
                response.raise_for_status()
                return response.json()


def get_chat_history(chat_id: str) -> List:
    """Retrieve conversation history for a specific chat."""
    return conversation_history.get(chat_id, [])


def update_chat_history(chat_id: str, human_msg: str, ai_msg: str):
    """Update conversation history with new messages."""
    if chat_id not in conversation_history:
        conversation_history[chat_id] = []
    
    conversation_history[chat_id].append(HumanMessage(content=human_msg))
    conversation_history[chat_id].append(AIMessage(content=ai_msg))
    
    # Keep only last 10 exchanges (20 messages)
    if len(conversation_history[chat_id]) > 20:
        conversation_history[chat_id] = conversation_history[chat_id][-20:]


@app.get("/")
async def root():
    """Health check endpoint."""
    return {"status": "ok", "message": "AI Agent Backend is running"}


@app.post("/clear-memory")
async def clear_memory(user_id: Optional[str] = None):
    """
    Clear conversation history and processed messages.
    
    Args:
        user_id: Optional user ID to clear. If not provided, clears all users.
    """
    global conversation_history, processed_messages
    
    if user_id:
        # Clear specific user
        if user_id in conversation_history:
            del conversation_history[user_id]
        if user_id in processed_messages:
            del processed_messages[user_id]
        logger.info(f"Cleared memory for user {user_id}")
        return {"status": "success", "message": f"Memory cleared for user {user_id}"}
    else:
        # Clear all users
        conversation_history.clear()
        processed_messages.clear()
        logger.info("Cleared all conversation history and processed messages")
        return {"status": "success", "message": "Memory cleared for all users"}


@app.post("/webhook/telegram")
async def telegram_webhook(request: Request):
    """
    Main webhook endpoint for Telegram.
    Handles incoming messages (text and audio) and orchestrates the agent.
    """
    try:
        payload = await request.json()
        logger.info(f"Received Telegram webhook: {payload}")
        
        # Extract message data
        message = payload.get("message", {})
        chat_id = message.get("chat", {}).get("id")
        user_id = str(message.get("from", {}).get("id"))
        message_id = message.get("message_id")
        
        if not chat_id:
            raise HTTPException(status_code=400, detail="No chat_id in payload")
        
        # Check if we've already processed this message
        if user_id not in processed_messages:
            processed_messages[user_id] = set()
        
        if message_id in processed_messages[user_id]:
            logger.info(f"Skipping already processed message {message_id} from user {user_id}")
            return JSONResponse(content={"status": "already_processed"})
        
        # Mark this message as processed
        processed_messages[user_id].add(message_id)
        
        # Keep only last 100 message IDs per user to prevent memory bloat
        if len(processed_messages[user_id]) > 100:
            processed_messages[user_id] = set(list(processed_messages[user_id])[-100:])
        
        user_prompt = None
        
        # Handle voice messages
        if "voice" in message:
            voice = message["voice"]
            file_id = voice["file_id"]
            
            logger.info(f"Processing voice message from user {user_id}")
            
            # Get audio file URL
            audio_url = await get_telegram_file_url(file_id)
            
            # Transcribe audio using our tool
            transcription_result = await transcribe_audio.ainvoke({"audio_file_url": audio_url})
            user_prompt = transcription_result
            
            logger.info(f"Transcription: {user_prompt}")
        
        # Handle text messages
        elif "text" in message:
            user_prompt = message["text"]
            logger.info(f"Processing text message from user {user_id}: {user_prompt}")
            
            # Check for clear cache command
            if user_prompt.strip().lower() in ["/clear", "/clear_cache", "clear cache", "clear memory", "forget everything", "reset memory"]:
                # Clear conversation history for this user
                if user_id in conversation_history:
                    del conversation_history[user_id]
                    logger.info(f"Cleared conversation history for user {user_id}")
                
                # Clear processed messages for this user
                if user_id in processed_messages:
                    del processed_messages[user_id]
                    logger.info(f"Cleared processed messages cache for user {user_id}")
                
                await send_telegram_message(chat_id, "✅ Memory cleared! I've forgotten our previous conversations. Starting fresh!")
                return JSONResponse(content={"status": "memory_cleared"})
        
        # Handle document messages (PDF, DOCX, PPTX, images, etc.)
        elif "document" in message:
            document = message["document"]
            file_id = document["file_id"]
            file_name = document.get("file_name", "document")
            file_size = document.get("file_size", 0)
            mime_type = document.get("mime_type", "")
            
            logger.info(f"Processing document from user {user_id}: {file_name} ({mime_type}, {file_size} bytes)")
            
            # Check file size (Telegram API limit is 20MB for bots)
            if file_size > 20 * 1024 * 1024:  # 20MB
                await send_telegram_message(chat_id, "⚠️ File is too large. Please send files smaller than 20MB.")
                return JSONResponse(content={"status": "file_too_large"})
            
            # Supported document types
            supported_types = [
                'application/pdf',
                'application/vnd.openxmlformats-officedocument.wordprocessingml.document',  # DOCX
                'application/vnd.openxmlformats-officedocument.presentationml.presentation',  # PPTX
                'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',  # XLSX
                'application/msword',  # DOC
                'text/plain',
                'image/jpeg',
                'image/png',
                'image/jpg'
            ]
            
            # Send processing message
            await send_telegram_message(chat_id, f"📄 Processing {file_name}... Please wait.")
            
            try:
                # Download the file from Telegram
                file_url = await get_telegram_file_url(file_id)
                
                # Download to temporary location
                # Create temp file with original extension
                file_extension = os.path.splitext(file_name)[1]
                temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=file_extension)
                temp_file_path = temp_file.name
                temp_file.close()
                
                # Download file
                async with httpx.AsyncClient() as client:
                    response = await client.get(file_url)
                    response.raise_for_status()
                    
                    async with aiofiles.open(temp_file_path, 'wb') as f:
                        await f.write(response.content)
                
                logger.info(f"Downloaded file to: {temp_file_path}")
                
                # Read the document using our tool
                document_content = await read_document.ainvoke({"file_path": temp_file_path})
                
                # Clean up temp file
                try:
                    os.unlink(temp_file_path)
                except:
                    pass
                
                # Create a prompt for the agent that includes the document content
                caption = message.get("caption", "")
                if caption:
                    user_prompt = f"I've sent you a document: {file_name}\n\nUser's message: {caption}\n\nDocument content:\n{document_content}"
                else:
                    user_prompt = f"I've sent you a document: {file_name}\n\nPlease analyze this document and tell me what it contains.\n\nDocument content:\n{document_content}"
                
                logger.info(f"Document processed successfully. Content length: {len(document_content)} characters")
                
            except Exception as e:
                logger.error(f"Failed to process document: {e}", exc_info=True)
                await send_telegram_message(chat_id, f"❌ Sorry, I couldn't process this document. Error: {str(e)}")
                return JSONResponse(content={"status": "document_processing_failed"})
        
        # Handle photo messages
        elif "photo" in message:
            photos = message["photo"]
            # Telegram sends multiple sizes, get the largest one
            largest_photo = max(photos, key=lambda p: p.get("file_size", 0))
            file_id = largest_photo["file_id"]
            
            logger.info(f"Processing photo from user {user_id}")
            
            # Send processing message
            await send_telegram_message(chat_id, "📸 Processing image... Please wait.")
            
            try:
                # Download the file from Telegram
                file_url = await get_telegram_file_url(file_id)
                
                # Download to temporary location
                temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".jpg")
                temp_file_path = temp_file.name
                temp_file.close()
                
                # Download file
                async with httpx.AsyncClient() as client:
                    response = await client.get(file_url)
                    response.raise_for_status()
                    
                    async with aiofiles.open(temp_file_path, 'wb') as f:
                        await f.write(response.content)
                
                logger.info(f"Downloaded photo to: {temp_file_path}")
                
                # Get caption if provided
                caption = message.get("caption", "")
                if caption:
                    # User provided specific question about the image
                    user_prompt = f"I've sent you an image. {caption}\n\n[Image path: {temp_file_path}]"
                else:
                    # No caption, just describe the image
                    user_prompt = f"I've sent you an image. Please analyze and describe what you see.\n\n[Image path: {temp_file_path}]"
                
                logger.info(f"Photo ready for analysis: {temp_file_path}")
                
            except Exception as e:
                logger.error(f"Failed to download photo: {e}", exc_info=True)
                await send_telegram_message(chat_id, f"❌ Sorry, I couldn't download this photo. Error: {str(e)}")
                return JSONResponse(content={"status": "photo_download_failed"})
        
        # Handle video messages
        elif "video" in message:
            video = message["video"]
            file_id = video["file_id"]
            file_size = video.get("file_size", 0)
            duration = video.get("duration", 0)
            
            logger.info(f"Processing video from user {user_id}: {duration}s, {file_size} bytes")
            
            # Check file size (20MB limit)
            if file_size > 20 * 1024 * 1024:
                await send_telegram_message(chat_id, "⚠️ Video is too large. Please send videos smaller than 20MB.")
                return JSONResponse(content={"status": "video_too_large"})
            
            # Send processing message
            await send_telegram_message(chat_id, "🎥 Processing video... This may take a moment.")
            
            try:
                # Download the file from Telegram
                file_url = await get_telegram_file_url(file_id)
                
                # Download to temporary location
                temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".mp4")
                temp_file_path = temp_file.name
                temp_file.close()
                
                # Download file
                async with httpx.AsyncClient(timeout=120.0) as client:
                    response = await client.get(file_url)
                    response.raise_for_status()
                    
                    async with aiofiles.open(temp_file_path, 'wb') as f:
                        await f.write(response.content)
                
                logger.info(f"Downloaded video to: {temp_file_path}")
                
                # Get caption if provided
                caption = message.get("caption", "")
                if caption:
                    # User provided specific question about the video
                    user_prompt = f"I've sent you a video. {caption}\n\n[Video path: {temp_file_path}]"
                else:
                    # No caption, just describe the video
                    user_prompt = f"I've sent you a video. Please analyze and describe what happens in it.\n\n[Video path: {temp_file_path}]"
                
                logger.info(f"Video ready for analysis: {temp_file_path}")
                
            except Exception as e:
                logger.error(f"Failed to download video: {e}", exc_info=True)
                await send_telegram_message(chat_id, f"❌ Sorry, I couldn't download this video. Error: {str(e)}")
                return JSONResponse(content={"status": "video_download_failed"})
        
        else:
            await send_telegram_message(chat_id, "Sorry, I can only process text, voice messages, documents (PDF, DOCX, etc.), images, and videos.")
            return JSONResponse(content={"status": "unsupported_message_type"})
        
        # Get conversation history
        chat_history = get_chat_history(user_id)
        
        # Load user preferences if this is a fresh conversation (no history)
        user_context = ""
        if not chat_history:
            # First interaction after restart - load preferences from database
            logger.info(f"Loading user preferences for fresh conversation: {user_id}")
            try:
                from tools import get_user_preferences
                prefs_result = await get_user_preferences.ainvoke({"user_id": user_id})
                
                if prefs_result and "No preferences" not in prefs_result:
                    user_context = f"\n\n[User Preferences from Database]\n{prefs_result}\n"
                    logger.info(f"Loaded preferences: {prefs_result[:100]}...")
            except Exception as e:
                logger.error(f"Failed to load user preferences: {e}")
        
        # Prepend user context to prompt if available
        if user_context:
            user_prompt = user_context + user_prompt
        
        # Invoke the agent (non-streaming for reliable tool calls)
        logger.info(f"Invoking agent for user {user_id}")
        
        # Get response from agent
        result = await agent_executor.ainvoke({
            "input": user_prompt,
            "chat_history": chat_history,
            "user_id": user_id
        })
        
        full_response = result.get("output", "")
        logger.info(f"Agent response received")
        
        final_answer = full_response or "I'm sorry, I couldn't process that."
        logger.info(f"Agent response: {final_answer}")
        
        # Handle max iterations error
        if final_answer == "Agent stopped due to max iterations.":
            # Check if there are intermediate steps with file paths
            intermediate_steps = result.get("intermediate_steps", [])
            if intermediate_steps:
                # Look for the last tool call result
                for action, observation in reversed(intermediate_steps):
                    if observation and observation.endswith(".wav") and os.path.exists(observation):
                        final_answer = observation
                        logger.info(f"Recovered audio file from intermediate steps: {final_answer}")
                        break
        
        # Update conversation history
        update_chat_history(user_id, user_prompt, final_answer)
        
        # Check if the response is a local audio file path
        if final_answer.strip().endswith(".wav") and os.path.exists(final_answer.strip()):
            audio_path = final_answer.strip()
            logger.info(f"Detected audio file path: {audio_path}")
            
            # Send audio message to Telegram (will auto-convert to MP3)
            await send_telegram_message(chat_id, audio_path=audio_path)
            
            # Also send a text confirmation
            await send_telegram_message(chat_id, text="🎵 Here's your audio message!")
        else:
            # Send text response back to Telegram
            await send_telegram_message(chat_id, text=final_answer)
        
        return JSONResponse(content={"status": "success"})
    
    except Exception as e:
        logger.error(f"Error processing webhook: {str(e)}", exc_info=True)
        if 'chat_id' in locals():
            await send_telegram_message(chat_id, "Sorry, an error occurred while processing your request.")
        raise HTTPException(status_code=500, detail=str(e))
