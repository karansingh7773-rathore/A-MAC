from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse, StreamingResponse
from langchain_nvidia_ai_endpoints import ChatNVIDIA
from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import HumanMessage, AIMessage
import httpx
import os
from typing import Dict, List
import logging
from dotenv import load_dotenv
import json

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
    save_contact_to_cosmos,
    get_user_history,
    store_note,
    tools_list
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI
app = FastAPI(title="AI Agent Backend", version="1.0.0")

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

# Initialize NVIDIA model with streaming support
llm = ChatNVIDIA(
    model="deepseek-ai/deepseek-v3.1-terminus",
    api_key=NVIDIA_API_KEY,
    temperature=0.7,
    max_tokens=1024,
    streaming=True  # Enable streaming
)

# Create agent prompt with even more explicit instructions
agent_prompt = ChatPromptTemplate.from_messages([
    ("system", """You are a helpful, obedient, and highly intelligent AI assistant.

[YOUR CORE GOAL]
Your primary goal is to **understand and obey the user's most recent instruction.**
DO NOT perform any action the user has just told you not to do.
Analyze the user's input *first*, and *then* decide if a tool is needed.
     
[CRITICAL RULE: HOW TO FINISH A TASK]
When a tool (like `save_contact_to_cosmos` or `send_email`) succeeds, it will return a simple confirmation like "OK. Contact saved." or "OK. Email sent."

When you receive this "OK" message, your job is to:
1.  **STOP** calling more tools.
2.  Provide a final, human-readable confirmation to the user.
3.  Example: If the tool returns "OK. Contact saved.", you should respond to the user: "Got it, I've saved Chinu's contact."
4.  Example: If the tool returns "OK. Email sent.", you should respond to the user: "Alright, I've sent that email to Chinu."

Do NOT loop. Do NOT call the same tool again. Your task is to report the success.

[PERSONAL DATA RULE (VERY IMPORTANT)]
You will receive a 'user_id' with every message. This ID represents a specific **person**.
You **MUST** use this *exact* `user_id` for any tool that saves or retrieves that person's
data (like `store_note`, `save_contact`, `get_user_history`).
Do **NOT** make up a 'user_id' like 'user123'.

---
[TOOL PROTOCOLS AND USAGE]
You must follow these rules when using tools.

**1. INTERNAL DATABASE FIRST (Tools: `get_user_history`, `save_contact_to_cosmos`)**
* **WHEN TO USE:** If the user asks about data *you* should know (like "my contacts," "my notes," "did you save..."), you **MUST** use these tools first.
* **DO NOT** use `web_search` or `search_emails` to answer questions about data the user has given you. Look in your own database first!
* **Example:** User asks "Is my contact updated?" -> Call `get_user_history` or a similar tool.


**2. WEB SEARCH (Tool: `tavily_search`)**
* **WHEN TO USE:** For questions about current events, news, or real-time data (weather, stocks).
* **HOW TO USE:** Call `tavily_search(query: str)` with a concise query.
* **Example:** User says "What's the latest AI news?" -> Call `tavily_search(query="latest AI news 2025")`

**3. EMAIL (Tools: `search_email`, `send_email`)**
* **RULE:** All email actions are for the user's authenticated account.
* **Tool: `search_email(query: str)`**
    * **WHEN:** User asks to "find," "search," or "look for" emails.
    * **Example:** User: "Find my recent flight receipts." -> Call `search_email(query="receipt from:airline")`
* **Tool: `send_email(to: str, subject: str, body: str)`**
    * **CRITICAL:** You **MUST** have all three arguments (`to`, `subject`, `body`) before calling.
    * **If missing info:** You **MUST** ask the user for it.
    
**4. AGENTIC LOGIC: Multi-Step Plans**
* **CRITICAL:** If a user's request requires multiple tools, you **MUST** plan and execute them in the correct logical order.
*
* **EXAMPLE 1 (Info Missing):**
    * **User:** "Send an email to Karan about our project."
    * **You (Internal Monologue):** "My goal is to send an email. First, I must find Karan's email address."
    * **You:** -> Call `get_user_history(user_id="...")` to find a contact named "Karan".
    * **Tool Response:** `[...{{'name': 'Karan', 'email': 'karan@example.com'}}...]`
    * **You (Internal Monologue):** "I found the email. Now I am missing the subject and body."
    * **You:** "Okay, I found Karan (karan@example.com). What should the subject and body of the email be?"
    * **User:** "Subject is 'Project Update' and the body is '...'"
    * **You:** -> Call `send_email(to="karan@example.com", subject="Project Update", body="...")`
*
* **EXAMPLE 2 (Complex Request):**
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

**7. AUDIO GENERATION (Tool: `convert_text_to_speech`)**
* **WHEN:** ONLY use this if the user *explicitly asks* to hear your voice (e.g., "say hello to me").
* **OBEY:** If the user says "don't use text to speech" or just has a normal conversation, you **MUST NOT** use this tool. Respond with text.
* **FINAL ANSWER:** When this tool returns a local file path (e.g., '...file.wav'), that file path **IS YOUR FINAL ANSWER**. You MUST stop, and output **ONLY** that raw file path and nothing else.
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
agent = create_tool_calling_agent(llm, tools_list, agent_prompt)

# Create agent executor with stricter settings
agent_executor = AgentExecutor(
    agent=agent,
    tools=tools_list,
    verbose=True,
    handle_parsing_errors=True,
    max_iterations=3,
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
    async with httpx.AsyncClient() as client:
        if audio_path:
            # Send audio file directly from local path
            logger.info(f"Sending audio file: {audio_path}")
            
            with open(audio_path, 'rb') as audio_file:
                files = {'voice': (os.path.basename(audio_path), audio_file, 'audio/wav')}
                data = {'chat_id': chat_id}
                
                response = await client.post(
                    f"{TELEGRAM_API_URL}/sendAudio",
                    files=files,
                    data=data,
                    timeout=60.0
                )
            
            # Clean up local file after sending
            try:
                os.remove(audio_path)
                logger.info(f"Cleaned up local audio file: {audio_path}")
            except Exception as e:
                logger.warning(f"Could not delete local file: {e}")
            
            response.raise_for_status()
            return response.json()
        else:
            # Send text message
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
        
        if not chat_id:
            raise HTTPException(status_code=400, detail="No chat_id in payload")
        
        user_prompt = None
        
        # Handle voice messages
        if "voice" in message:
            voice = message["voice"]
            file_id = voice["file_id"]
            
            logger.info(f"Processing voice message from user {user_id}")
            
            # Get audio file URL
            audio_url = await get_telegram_file_url(file_id)
            
            # Transcribe audio using our tool (now async)
            transcription_result = await transcribe_audio.ainvoke({"audio_file_url": audio_url})
            user_prompt = transcription_result
            
            logger.info(f"Transcription: {user_prompt}")
        
        # Handle text messages
        elif "text" in message:
            user_prompt = message["text"]
            logger.info(f"Processing text message from user {user_id}: {user_prompt}")
        
        else:
            await send_telegram_message(chat_id, "Sorry, I can only process text and voice messages.")
            return JSONResponse(content={"status": "unsupported_message_type"})
        
        # Get conversation history
        chat_history = get_chat_history(user_id)
        
        # Invoke the agent with streaming
        logger.info(f"Invoking agent for user {user_id}")
        
        # Stream the response
        full_response = ""
        async for chunk in agent_executor.astream({
            "input": user_prompt,
            "chat_history": chat_history,
            "user_id": user_id
        }):
            # Accumulate response chunks
            if "output" in chunk:
                full_response = chunk["output"]
                logger.info(f"Agent streaming chunk: {chunk['output'][:50]}...")
        
        final_answer = full_response or "I'm sorry, I couldn't process that."
        logger.info(f"Agent response: {final_answer}")
        
        # Handle max iterations error
        if final_answer == "Agent stopped due to max iterations.":
            # Check if there are intermediate steps with file paths
            intermediate_steps = chunk.get("intermediate_steps", [])
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
            
            # Send audio message to Telegram
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


@app.on_event("startup")
async def startup_event():
    """Initialize connections on startup."""
    logger.info("AI Agent Backend starting up...")
    logger.info(f"NVIDIA API Key configured: {bool(NVIDIA_API_KEY)}")
    logger.info(f"Telegram Bot Token configured: {bool(TELEGRAM_BOT_TOKEN)}")
