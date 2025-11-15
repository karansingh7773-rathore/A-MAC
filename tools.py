from langchain.tools import tool
from azure.cosmos import CosmosClient, PartitionKey, exceptions
import httpx
import os
import logging
from typing import Dict, Any, Optional
import uuid
from datetime import datetime
from dotenv import load_dotenv
import riva.client
from riva.client.auth import Auth
import asyncio
import tempfile
import wave
from langchain_community.tools.tavily_search import TavilySearchResults
from langchain_community.tools.gmail.utils import build_resource_service, get_gmail_credentials
from langchain_community.tools.gmail.create_draft import GmailCreateDraft
from langchain_community.tools.gmail.send_message import GmailSendMessage
from langchain_community.tools.gmail.search import GmailSearch
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
import pickle
from browser_tools import browser_tools_list
from browser_agent import execute_browser_task
# Document processing imports
from unstructured.partition.auto import partition
from pathlib import Path

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)

# Environment variables
NVIDIA_API_KEY = os.getenv("NVIDIA_API_KEY")
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")
GOOGLE_CREDENTIALS_PATH = os.getenv("GOOGLE_CREDENTIALS_PATH", "credentials.json")
# Use unified token file with all scopes
GOOGLE_TOKEN_PATH = os.getenv("GOOGLE_TOKEN_PATH", "token_full_access.pickle")
COSMOS_ENDPOINT = os.getenv("COSMOS_ENDPOINT")
COSMOS_KEY = os.getenv("COSMOS_KEY")
COSMOS_DATABASE_NAME = os.getenv("COSMOS_DATABASE_NAME", "ai_agent_db")
COSMOS_CONTAINER_NAME = os.getenv("COSMOS_CONTAINER_NAME", "user_data")

# Initialize Cosmos DB client
cosmos_client = None
database = None
container = None

try:
    cosmos_client = CosmosClient(COSMOS_ENDPOINT, COSMOS_KEY)
    database = cosmos_client.create_database_if_not_exists(id=COSMOS_DATABASE_NAME)
    container = database.create_container_if_not_exists(
        id=COSMOS_CONTAINER_NAME,
        partition_key=PartitionKey(path="/user_id")
        # Removed offer_throughput - not supported on serverless accounts
    )
    logger.info("Cosmos DB initialized successfully")
except Exception as e:
    logger.error(f"Failed to initialize Cosmos DB: {e}")


# Initialize NVIDIA Riva ASR with correct auth and function ID
riva_asr_service = None
riva_tts_service = None

try:
    # Create auth for ASR (Whisper) with its specific function ID
    riva_asr_auth = Auth(
        ssl_cert=None,
        use_ssl=True,
        uri="grpc.nvcf.nvidia.com:443",
        metadata_args=[
            ["authorization", f"Bearer {NVIDIA_API_KEY}"],
            ["function-id", "b702f636-f60c-4a3d-a6f4-f3568c13bd7d"]  # Whisper ASR
        ]
    )
    
    riva_asr_service = riva.client.ASRService(riva_asr_auth)
    logger.info("NVIDIA Riva ASR initialized successfully")
except Exception as e:
    logger.error(f"Failed to initialize NVIDIA Riva ASR: {e}")

# Initialize manual TTS client with correct function ID
try:
    TTS_FUNCTION_ID = "877104f7-e885-42b9-8de8-f6e4c6303969"  # Magpie TTS
    tts_auth = Auth(
        ssl_cert=None,
        use_ssl=True,
        uri="grpc.nvcf.nvidia.com:443",
        metadata_args=[
            ["authorization", f"Bearer {NVIDIA_API_KEY}"],
            ["function-id", TTS_FUNCTION_ID]
        ]
    )
    riva_tts_service = riva.client.SpeechSynthesisService(tts_auth)
    logger.info("Manual Riva TTS client initialized successfully")
except Exception as e:
    logger.error(f"Failed to initialize manual Riva TTS client: {e}", exc_info=True)
    riva_tts_service = None

# Initialize Tavily Search tool
tavily_search = None
try:
    if TAVILY_API_KEY:
        tavily_search = TavilySearchResults(
            api_key=TAVILY_API_KEY,
            max_results=5,
            search_depth="advanced",
            include_answer=True,
            include_raw_content=False,
            include_images=False
        )
        logger.info("Tavily Search initialized successfully")
    else:
        logger.warning("TAVILY_API_KEY not found in environment variables")
except Exception as e:
    logger.error(f"Failed to initialize Tavily Search: {e}")


# Initialize Gmail and Calendar services
gmail_service = None
calendar_service = None
# Use the same comprehensive scopes as google_tools.py
SCOPES = [
    # Gmail
    'https://www.googleapis.com/auth/gmail.send',
    'https://www.googleapis.com/auth/gmail.readonly',
    'https://www.googleapis.com/auth/gmail.modify',
    # Calendar
    'https://www.googleapis.com/auth/calendar',
    'https://www.googleapis.com/auth/calendar.events',
    # Contacts & People API
    'https://www.googleapis.com/auth/contacts',
    'https://www.googleapis.com/auth/contacts.readonly',
    # Docs
    'https://www.googleapis.com/auth/documents',
    'https://www.googleapis.com/auth/documents.readonly',
    # Sheets
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/spreadsheets.readonly',
    # Drive
    'https://www.googleapis.com/auth/drive',
    'https://www.googleapis.com/auth/drive.file',
    'https://www.googleapis.com/auth/drive.readonly',
    # YouTube Data API
    'https://www.googleapis.com/auth/youtube.readonly',
]

try:
    creds = None
    # Check if token.pickle exists
    if os.path.exists(GOOGLE_TOKEN_PATH):
        with open(GOOGLE_TOKEN_PATH, 'rb') as token:
            creds = pickle.load(token)
    
    # If there are no valid credentials, let the user log in
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                GOOGLE_CREDENTIALS_PATH, SCOPES)
            creds = flow.run_local_server(port=0)
        
        # Save the credentials for the next run
        with open(GOOGLE_TOKEN_PATH, 'wb') as token:
            pickle.dump(creds, token)
    
    # Build services
    gmail_service = build('gmail', 'v1', credentials=creds)
    calendar_service = build('calendar', 'v3', credentials=creds)
    logger.info("Gmail and Calendar services initialized successfully")
except Exception as e:
    logger.error(f"Failed to initialize Gmail/Calendar services: {e}")


@tool
async def transcribe_audio(audio_file_url: str) -> str:
    """
    Transcribe an audio file to text using NVIDIA Riva ASR (Whisper) via gRPC.
    
    Args:
        audio_file_url: The URL of the audio file to transcribe
        
    Returns:
        The transcribed text
    """
    try:
        if not riva_asr_service:
            return "Error: NVIDIA Riva ASR not initialized"
        
        logger.info(f"Transcribing audio from: {audio_file_url}")
        
        # Download audio file
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(audio_file_url)
            response.raise_for_status()
            audio_data = response.content
        
        # Save to temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix=".oga") as temp_file:
            temp_file.write(audio_data)
            temp_file_path = temp_file.name
        
        logger.info(f"Audio downloaded to: {temp_file_path}")
        
        # Configure ASR with correct language code
        config = riva.client.RecognitionConfig(
            language_code="en",  # Use "en" not "en-US"
            max_alternatives=1,
            enable_automatic_punctuation=True,
            audio_channel_count=1
        )
        
        # Transcribe using Riva ASR
        loop = asyncio.get_event_loop()
        
        def transcribe_sync():
            with open(temp_file_path, 'rb') as audio_file:
                audio_bytes = audio_file.read()
                response = riva_asr_service.offline_recognize(audio_bytes, config)
                if response.results and len(response.results) > 0:
                    return response.results[0].alternatives[0].transcript
                return ""
        
        transcription = await loop.run_in_executor(None, transcribe_sync)
        
        # Clean up temporary file
        try:
            os.remove(temp_file_path)
        except Exception as e:
            logger.warning(f"Could not delete temp file: {e}")
        
        logger.info(f"Transcription successful: {transcription[:100] if transcription else 'empty'}...")
        return transcription if transcription else "Could not transcribe audio"
    
    except Exception as e:
        logger.error(f"Audio transcription failed: {e}")
        return f"Error transcribing audio: {str(e)}"


@tool
async def convert_text_to_speech(text_to_speak: str) -> str:
    """
    Converts text into a spoken audio file and returns the local file path.
    This is the FINAL step. You should return this file path directly to the user.
    Do NOT summarize or add extra commentary. The file path is the complete answer.
    
    Args:
        text_to_speak: The text to convert to speech
        
    Returns:
        Local file path of the generated audio file (this is your final answer)
    """
    try:
        if not riva_tts_service:
            return "Error: Manual Riva TTS client is not initialized"
        
        logger.info(f"Converting text to speech (Manual): {text_to_speak[:100]}...")
        
        # Generate unique filename
        filename = f"tts_{uuid.uuid4().hex[:8]}.wav"
        local_file_path = os.path.join(os.getcwd(), filename)
        
        # Use the Riva client's synthesize method directly
        loop = asyncio.get_event_loop()
        
        def synthesize_sync():
            # synthesize() returns a single response object with raw audio data
            response = riva_tts_service.synthesize(
                text=text_to_speak,
                voice_name="Magpie-Multilingual.EN-US.Mia",
                language_code="en-US",
                sample_rate_hz=22050
            )
            
            # Write the raw audio data as a proper WAV file with header
            with wave.open(local_file_path, 'wb') as wav_file:
                # Set WAV file parameters
                wav_file.setnchannels(1)  # Mono audio
                wav_file.setsampwidth(2)  # 16-bit = 2 bytes
                wav_file.setframerate(22050)  # Sample rate
                
                # Write the raw audio data
                wav_file.writeframes(response.audio)
        
        await loop.run_in_executor(None, synthesize_sync)
        
        logger.info(f"TTS audio saved locally with proper WAV header: {local_file_path}")
        
        # Verify file was created
        if not os.path.exists(local_file_path):
            raise FileNotFoundError(f"TTS output file not created: {local_file_path}")
        
        # Return ONLY the local file path
        return local_file_path
    
    except Exception as e:
        logger.error(f"Text-to-speech conversion failed: {e}", exc_info=True)
        return f"Error converting text to speech: {str(e)}"


@tool
def save_user_preference(user_id: str, preference_key: str, preference_value: str) -> str:
    """
    Save a user preference to Cosmos DB.
    Use this for storing user-specific settings like timezone, language, notification preferences, etc.
    
    Args:
        user_id: The ID of the user
        preference_key: The preference name (e.g., "timezone", "language", "theme")
        preference_value: The preference value
        
    Returns:
        Success or error message
    """
    try:
        if not container:
            return "Error: Cosmos DB not initialized"
        
        pref_id = f"{user_id}_{preference_key}"
        pref_item = {
            "id": pref_id,
            "user_id": user_id,
            "type": "preference",
            "key": preference_key,
            "value": preference_value,
            "updated_at": datetime.utcnow().isoformat()
        }
        
        # Upsert (update or insert)
        container.upsert_item(body=pref_item)
        logger.info(f"Preference saved: {preference_key}={preference_value} for user {user_id}")
        
        return f"✅ Preference saved: {preference_key} = {preference_value}"
    
    except exceptions.CosmosHttpResponseError as e:
        logger.error(f"Failed to save preference: {e}")
        return f"Error saving preference: {str(e)}"


@tool
def get_user_preferences(user_id: str) -> str:
    """
    Retrieve all user preferences from Cosmos DB.
    
    Args:
        user_id: The ID of the user
        
    Returns:
        Dictionary of user preferences
    """
    try:
        if not container:
            return "Error: Cosmos DB not initialized"
        
        query = f"SELECT * FROM c WHERE c.user_id = @user_id AND c.type = 'preference'"
        parameters = [{"name": "@user_id", "value": user_id}]
        
        items = list(container.query_items(
            query=query,
            parameters=parameters,
            enable_cross_partition_query=True
        ))
        
        if not items:
            return f"No preferences found for user {user_id}"
        
        prefs = {item['key']: item['value'] for item in items}
        
        formatted = "\n".join([f"• {k}: {v}" for k, v in prefs.items()])
        return f"*Your Preferences:*\n{formatted}"
    
    except exceptions.CosmosHttpResponseError as e:
        logger.error(f"Failed to retrieve preferences: {e}")
        return f"Error retrieving preferences: {str(e)}"


@tool
def save_agent_state(user_id: str, task_name: str, state_data: str) -> str:
    """
    Save agent state for multi-day tasks (like Techathon projects).
    Use this to remember task progress, intermediate results, and continue work later.
    
    Args:
        user_id: The ID of the user
        task_name: Name of the task/project (e.g., "Techathon_ML_Project")
        state_data: JSON string or text describing the current state
        
    Returns:
        Success or error message
    """
    try:
        if not container:
            return "Error: Cosmos DB not initialized"
        
        state_id = f"{user_id}_{task_name}"
        state_item = {
            "id": state_id,
            "user_id": user_id,
            "type": "agent_state",
            "task_name": task_name,
            "state": state_data,
            "updated_at": datetime.utcnow().isoformat()
        }
        
        container.upsert_item(body=state_item)
        logger.info(f"Agent state saved for task: {task_name} (user {user_id})")
        
        return f"✅ Task state saved: {task_name}"
    
    except exceptions.CosmosHttpResponseError as e:
        logger.error(f"Failed to save agent state: {e}")
        return f"Error saving task state: {str(e)}"


@tool
def get_agent_state(user_id: str, task_name: str) -> str:
    """
    Retrieve agent state for a specific task.
    
    Args:
        user_id: The ID of the user
        task_name: Name of the task/project
        
    Returns:
        Task state data or error message
    """
    try:
        if not container:
            return "Error: Cosmos DB not initialized"
        
        state_id = f"{user_id}_{task_name}"
        
        try:
            item = container.read_item(item=state_id, partition_key=user_id)
            return f"*Task: {task_name}*\n\nLast updated: {item['updated_at']}\n\nState:\n{item['state']}"
        except exceptions.CosmosResourceNotFoundError:
            return f"No saved state found for task: {task_name}"
    
    except exceptions.CosmosHttpResponseError as e:
        logger.error(f"Failed to retrieve agent state: {e}")
        return f"Error retrieving task state: {str(e)}"


@tool
def store_note(user_id: str, note_content: str) -> str:
    """
    Store a quick note for the user in Cosmos DB.
    
    Args:
        user_id: The ID of the user
        note_content: The content of the note
        
    Returns:
        Success or error message
    """
    try:
        if not container:
            return "Error: Cosmos DB not initialized"
        
        note_id = str(uuid.uuid4())
        note_item = {
            "id": note_id,
            "user_id": user_id,
            "type": "note",
            "content": note_content,
            "created_at": datetime.utcnow().isoformat()
        }
        
        container.create_item(body=note_item)
        logger.info(f"Note stored for user {user_id}")
        
        return f"✅ Note saved successfully"
    
    except exceptions.CosmosHttpResponseError as e:
        logger.error(f"Failed to store note: {e}")
        return f"Error storing note: {str(e)}"


@tool
def get_notes(user_id: str, limit: int = 10) -> str:
    """
    Retrieve recent notes for a user.
    
    Args:
        user_id: The ID of the user
        limit: Maximum number of notes to retrieve
        
    Returns:
        List of notes
    """
    try:
        if not container:
            return "Error: Cosmos DB not initialized"
        
        query = f"SELECT * FROM c WHERE c.user_id = @user_id AND c.type = 'note' ORDER BY c.created_at DESC OFFSET 0 LIMIT @limit"
        parameters = [
            {"name": "@user_id", "value": user_id},
            {"name": "@limit", "value": limit}
        ]
        
        items = list(container.query_items(
            query=query,
            parameters=parameters,
            enable_cross_partition_query=True
        ))
        
        if not items:
            return f"No notes found for user {user_id}"
        
        notes_list = []
        for idx, note in enumerate(items, 1):
            created = note['created_at'][:10]  # Just the date
            notes_list.append(f"{idx}. ({created}) {note['content']}")
        
        return f"*📝 Your Notes ({len(items)}):*\n\n" + "\n\n".join(notes_list)
    
    except exceptions.CosmosHttpResponseError as e:
        logger.error(f"Failed to retrieve notes: {e}")
        return f"Error retrieving notes: {str(e)}"


@tool
async def web_search(query: str) -> str:
    """
    Search the web for current information using Tavily Search.
    Use this tool when you need real-time information, recent news, or facts not in your training data.
    
    Args:
        query: The search query to look up on the web
        
    Returns:
        Search results with relevant information from the web
    """
    try:
        if not tavily_search:
            return "Error: Tavily Search not initialized. Please check TAVILY_API_KEY."
        
        logger.info(f"Performing web search: {query}")
        
        # Run search in executor to avoid blocking
        loop = asyncio.get_event_loop()
        results = await loop.run_in_executor(None, lambda: tavily_search.invoke({"query": query}))
        
        if not results:
            return "No results found for your search query."
        
        # Format results for better readability
        formatted_results = []
        for i, result in enumerate(results, 1):
            title = result.get("title", "No title")
            content = result.get("content", "No content")
            url = result.get("url", "")
            formatted_results.append(f"{i}. {title}\n{content}\nSource: {url}\n")
        
        response = "\n".join(formatted_results)
        logger.info(f"Web search completed. Found {len(results)} results.")
        
        return response
    
    except Exception as e:
        logger.error(f"Web search failed: {e}")
        return f"Error performing web search: {str(e)}"


@tool
async def send_email(to: str, subject: str, body: str) -> str:
    """
    Send an email using Gmail with HTML formatting.
    
    Args:
        to: Recipient email address
        subject: Email subject line
        body: Email body content
        
    Returns:
        Success or error message
    """
    try:
        if not gmail_service:
            return "Error: Gmail service not initialized. Please check credentials.json"
        
        logger.info(f"Sending email to: {to}")
        
        from email.mime.multipart import MIMEMultipart
        from email.mime.text import MIMEText
        import base64
        
        # Convert plain text to HTML with proper formatting
        # Replace \n\n with paragraph breaks and \n with line breaks
        html_body = body.replace('\n\n', '</p><p>').replace('\n', '<br>')
        
        # Detect headings (lines that end with : or are in title case)
        lines = body.split('\n')
        formatted_lines = []
        for line in lines:
            stripped = line.strip()
            # Check if line looks like a heading (ends with : or is short and capitalized)
            if stripped and (
                stripped.endswith(':') or 
                (len(stripped.split()) <= 8 and stripped[0].isupper() and not stripped.endswith('.'))
            ):
                formatted_lines.append(f'<h3 style="margin-top: 20px; margin-bottom: 10px; color: #333;">{stripped}</h3>')
            elif stripped:
                formatted_lines.append(f'<p style="margin-bottom: 12px; line-height: 1.6;">{stripped}</p>')
            else:
                formatted_lines.append('<br>')
        
        html_content = f"""
        <html>
            <head>
                <style>
                    body {{
                        font-family: Arial, Helvetica, sans-serif;
                        font-size: 14px;
                        color: #333;
                        line-height: 1.6;
                    }}
                    p {{
                        margin-bottom: 12px;
                    }}
                    h3 {{
                        margin-top: 20px;
                        margin-bottom: 10px;
                        color: #333;
                    }}
                </style>
            </head>
            <body>
                {''.join(formatted_lines)}
            </body>
        </html>
        """
        
        # Create message with both HTML and plain text versions
        message = MIMEMultipart('alternative')
        message['to'] = to
        message['subject'] = subject
        
        # Plain text version (fallback)
        text_part = MIMEText(body, 'plain')
        message.attach(text_part)
        
        # HTML version (preferred)
        html_part = MIMEText(html_content, 'html')
        message.attach(html_part)
        
        raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
        
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None,
            lambda: gmail_service.users().messages().send(
                userId='me',
                body={'raw': raw_message}
            ).execute()
        )
        
        logger.info(f"Email sent successfully. Message ID: {result['id']}")
        return "Email sent successfully."
    
    except Exception as e:
        logger.error(f"Failed to send email: {e}")
        return f"Error sending email: {str(e)}"


@tool
async def search_emails(query: str, max_results: int = 5) -> str:
    """
    Search for emails in Gmail using a query.
    
    Args:
        query: Search query (e.g., "from:example@gmail.com subject:meeting")
        max_results: Maximum number of results to return
        
    Returns:
        List of matching emails with subjects and snippets
    """
    try:
        if not gmail_service:
            return "Error: Gmail service not initialized. Please check credentials.json"
        
        logger.info(f"Searching emails with query: {query}")
        
        loop = asyncio.get_event_loop()
        results = await loop.run_in_executor(
            None,
            lambda: gmail_service.users().messages().list(
                userId='me',
                q=query,
                maxResults=max_results
            ).execute()
        )
        
        messages = results.get('messages', [])
        
        if not messages:
            return f"No emails found matching: {query}"
        
        email_list = []
        for msg in messages:
            msg_data = await loop.run_in_executor(
                None,
                lambda m=msg: gmail_service.users().messages().get(
                    userId='me',
                    id=m['id'],
                    format='metadata',
                    metadataHeaders=['From', 'Subject', 'Date']
                ).execute()
            )
            
            headers = {h['name']: h['value'] for h in msg_data['payload']['headers']}
            email_list.append(
                f"From: {headers.get('From', 'Unknown')}\n"
                f"Subject: {headers.get('Subject', 'No subject')}\n"
                f"Date: {headers.get('Date', 'Unknown')}\n"
                f"Snippet: {msg_data.get('snippet', '')}\n"
            )
        
        logger.info(f"Found {len(email_list)} matching emails")
        return "\n---\n".join(email_list)
    
    except Exception as e:
        logger.error(f"Failed to search emails: {e}")
        return f"Error searching emails: {str(e)}"


@tool
async def create_calendar_event(summary: str, start_time: str, end_time: str, description: str = "", location: str = "") -> str:
    """
    Create a new event in Google Calendar.
    
    Args:
        summary: Event title/summary
        start_time: Start time in ISO format (e.g., "2024-01-15T10:00:00")
        end_time: End time in ISO format (e.g., "2024-01-15T11:00:00")
        description: Event description (optional)
        location: Event location (optional)
        
    Returns:
        Success message with event link or error message
    """
    try:
        if not calendar_service:
            return "Error: Calendar service not initialized. Please check credentials.json"
        
        logger.info(f"Creating calendar event: {summary}")
        
        event = {
            'summary': summary,
            'location': location,
            'description': description,
            'start': {
                'dateTime': start_time,
                'timeZone': 'UTC',
            },
            'end': {
                'dateTime': end_time,
                'timeZone': 'UTC',
            },
        }
        
        loop = asyncio.get_event_loop()
        created_event = await loop.run_in_executor(
            None,
            lambda: calendar_service.events().insert(
                calendarId='primary',
                body=event
            ).execute()
        )
        
        event_link = created_event.get('htmlLink')
        logger.info(f"Calendar event created: {event_link}")
        
        return f"Event '{summary}' created successfully!\nLink: {event_link}"
    
    except Exception as e:
        logger.error(f"Failed to create calendar event: {e}")
        return f"Error creating calendar event: {str(e)}"


@tool
async def list_calendar_events(max_results: int = 10) -> str:
    """
    List upcoming events from Google Calendar.
    
    Args:
        max_results: Maximum number of events to return
        
    Returns:
        List of upcoming calendar events
    """
    try:
        if not calendar_service:
            return "Error: Calendar service not initialized. Please check credentials.json"
        
        logger.info(f"Listing upcoming calendar events")
        
        from datetime import datetime as dt
        now = dt.utcnow().isoformat() + 'Z'
        
        loop = asyncio.get_event_loop()
        events_result = await loop.run_in_executor(
            None,
            lambda: calendar_service.events().list(
                calendarId='primary',
                timeMin=now,
                maxResults=max_results,
                singleEvents=True,
                orderBy='startTime'
            ).execute()
        )
        
        events = events_result.get('items', [])
        
        if not events:
            return "No upcoming events found."
        
        event_list = []
        for event in events:
            start = event['start'].get('dateTime', event['start'].get('date'))
            summary = event.get('summary', 'No title')
            location = event.get('location', 'No location')
            event_list.append(
                f"Event: {summary}\n"
                f"Start: {start}\n"
                f"Location: {location}\n"
            )
        
        logger.info(f"Found {len(event_list)} upcoming events")
        return "\n---\n".join(event_list)
    
    except Exception as e:
        logger.error(f"Failed to list calendar events: {e}")
        return f"Error listing calendar events: {str(e)}"


@tool
async def read_document(file_path: str) -> str:
    """
    Read and extract text from any document file (PDF, DOCX, PPTX, TXT, images, etc.).
    
    This tool uses the Unstructured library to intelligently parse documents:
    - Auto-detects file type (.pdf, .docx, .pptx, .txt, .html, images, etc.)
    - Extracts text from digital PDFs
    - Performs OCR on scanned PDFs and images (using Tesseract)
    - Identifies document structure (titles, headings, paragraphs, lists, tables)
    - Removes junk like headers, footers, and page numbers
    
    Args:
        file_path: Absolute path to the file to read (e.g., "C:/Documents/report.pdf")
        
    Returns:
        Extracted and cleaned text content from the document
        
    Examples:
        - read_document("C:/Users/John/Desktop/contract.pdf")
        - read_document("D:/Downloads/presentation.pptx")
        - read_document("E:/Work/invoice_scan.jpg")
    """
    try:
        # Validate file exists
        file_path_obj = Path(file_path)
        if not file_path_obj.exists():
            return f"Error: File not found at path: {file_path}"
        
        if not file_path_obj.is_file():
            return f"Error: Path is not a file: {file_path}"
        
        logger.info(f"Processing document: {file_path}")
        
        # Use Unstructured to partition the document
        # This automatically detects file type and extracts content
        elements = partition(filename=str(file_path))
        
        if not elements:
            return f"Error: No content could be extracted from {file_path}"
        
        # Organize content by element type
        structured_content = {
            'titles': [],
            'headings': [],
            'text': [],
            'lists': [],
            'tables': [],
            'other': []
        }
        
        for element in elements:
            element_type = str(type(element).__name__)
            element_text = str(element).strip()
            
            if not element_text:
                continue
            
            # Categorize elements
            if 'Title' in element_type:
                structured_content['titles'].append(element_text)
            elif 'Header' in element_type or 'Heading' in element_type:
                structured_content['headings'].append(element_text)
            elif 'NarrativeText' in element_type or 'Text' in element_type:
                structured_content['text'].append(element_text)
            elif 'ListItem' in element_type:
                structured_content['lists'].append(element_text)
            elif 'Table' in element_type:
                structured_content['tables'].append(element_text)
            else:
                structured_content['other'].append(element_text)
        
        # Format the output nicely
        output_parts = []
        
        # Add file info
        file_size = file_path_obj.stat().st_size / 1024  # KB
        output_parts.append(f"📄 Document: {file_path_obj.name}")
        output_parts.append(f"📊 Size: {file_size:.2f} KB")
        output_parts.append(f"📝 Elements found: {len(elements)}")
        output_parts.append("\n" + "="*60 + "\n")
        
        # Add titles
        if structured_content['titles']:
            output_parts.append("📌 TITLES:")
            for title in structured_content['titles']:
                output_parts.append(f"  • {title}")
            output_parts.append("")
        
        # Add headings
        if structured_content['headings']:
            output_parts.append("📑 HEADINGS:")
            for heading in structured_content['headings']:
                output_parts.append(f"  • {heading}")
            output_parts.append("")
        
        # Add main text content
        if structured_content['text']:
            output_parts.append("📖 CONTENT:")
            output_parts.append("\n".join(structured_content['text']))
            output_parts.append("")
        
        # Add lists
        if structured_content['lists']:
            output_parts.append("📋 LISTS:")
            for item in structured_content['lists']:
                output_parts.append(f"  • {item}")
            output_parts.append("")
        
        # Add tables
        if structured_content['tables']:
            output_parts.append("📊 TABLES:")
            for table in structured_content['tables']:
                output_parts.append(table)
                output_parts.append("---")
            output_parts.append("")
        
        # Add other content
        if structured_content['other']:
            output_parts.append("📎 OTHER ELEMENTS:")
            output_parts.append("\n".join(structured_content['other']))
        
        result = "\n".join(output_parts)
        
        logger.info(f"Successfully extracted {len(elements)} elements from {file_path_obj.name}")
        
        return result
    
    except Exception as e:
        logger.error(f"Failed to read document {file_path}: {e}", exc_info=True)
        return f"Error reading document: {str(e)}\n\nMake sure the file path is correct and the file is accessible."


@tool
async def browser_automation(task_description: str) -> str:
    """
    Execute browser automation tasks using DeepSeek AI with vision.
    Use this for tasks on websites like YouTube, WhatsApp Web, Instagram, etc.
    
    Args:
        task_description: What to do (e.g., "Search for 'timeless song' on YouTube and play the first video")
        
    Returns:
        Result of the browser task
    """
    try:
        result = await execute_browser_task(task_description)
        return result
    except Exception as e:
        logger.error(f"Browser automation failed: {e}")
        return f"Error: {str(e)}"


# Export all tools
tools_list = [
    transcribe_audio,
    convert_text_to_speech,
    web_search,
    read_document,  # Document processing tool (PDF, DOCX, PPTX, images, etc.)
    browser_automation,  # Single browser automation tool
    send_email,
    search_emails,
    create_calendar_event,
    list_calendar_events,
    # Cosmos DB - User Preferences & Agent State
    save_user_preference,
    get_user_preferences,
    save_agent_state,
    get_agent_state,
    store_note,
    get_notes,
]

