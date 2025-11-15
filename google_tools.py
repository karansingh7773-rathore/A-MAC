"""
Google API Tools for A-MAC Agent
Includes: Contacts, People, Docs, Sheets, YouTube, Drive
"""

from langchain.tools import tool
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload
import pickle
import os
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
import json
import io

logger = logging.getLogger(__name__)

# Google API Scopes - Complete list for all services
SCOPES = [
    # Gmail (already authorized)
    'https://www.googleapis.com/auth/gmail.send',
    'https://www.googleapis.com/auth/gmail.readonly',
    'https://www.googleapis.com/auth/gmail.modify',
    # Calendar (already authorized)
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

GOOGLE_CREDENTIALS_PATH = os.getenv("GOOGLE_CREDENTIALS_PATH", "credentials.json")
# Use a new token file to avoid scope conflicts
GOOGLE_TOKEN_PATH = os.getenv("GOOGLE_TOKEN_PATH", "token_full_access.pickle")


def get_google_credentials():
    """Get or refresh Google API credentials with all required scopes."""
    creds = None
    
    # Load existing credentials
    if os.path.exists(GOOGLE_TOKEN_PATH):
        with open(GOOGLE_TOKEN_PATH, 'rb') as token:
            creds = pickle.load(token)
        
        # Check if existing credentials have all required scopes
        if creds and hasattr(creds, 'scopes'):
            existing_scopes = set(creds.scopes)
            required_scopes = set(SCOPES)
            missing_scopes = required_scopes - existing_scopes
            
            if missing_scopes:
                logger.warning(f"Token has missing scopes: {missing_scopes}")
                logger.info("Deleting old token and re-authenticating with all scopes...")
                creds = None  # Force re-authentication
    
    # Refresh or get new credentials
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
            except Exception as e:
                logger.error(f"Failed to refresh token: {e}")
                creds = None  # Force re-authentication
        
        if not creds:
            if not os.path.exists(GOOGLE_CREDENTIALS_PATH):
                raise FileNotFoundError(f"Google credentials file not found: {GOOGLE_CREDENTIALS_PATH}")
            
            logger.info("Starting OAuth flow with all required scopes...")
            flow = InstalledAppFlow.from_client_secrets_file(
                GOOGLE_CREDENTIALS_PATH, SCOPES)
            creds = flow.run_local_server(port=0)
        
        # Save credentials
        with open(GOOGLE_TOKEN_PATH, 'wb') as token:
            pickle.dump(creds, token)
        logger.info(f"Credentials saved to {GOOGLE_TOKEN_PATH}")
    
    return creds


# ==================== GOOGLE CONTACTS API ====================

@tool
async def add_google_contact(
    first_name: str,
    last_name: str = "",
    email: str = "",
    phone: str = "",
    company: str = "",
    job_title: str = "",
    notes: str = ""
) -> str:
    """
    Add a new contact to Google Contacts.
    
    Args:
        first_name: First name (required)
        last_name: Last name (optional)
        email: Email address (optional)
        phone: Phone number (optional)
        company: Company/organization name (optional)
        job_title: Job title/profession (optional)
        notes: Additional notes about the person (optional)
        
    Returns:
        Confirmation message with contact details
    """
    try:
        logger.info(f"🔵 CALLING add_google_contact: {first_name} {last_name}")
        creds = get_google_credentials()
        service = build('people', 'v1', credentials=creds)
        
        # Build contact data
        contact = {
            'names': [{
                'givenName': first_name,
                'familyName': last_name
            }]
        }
        
        if email:
            contact['emailAddresses'] = [{'value': email}]
        
        if phone:
            contact['phoneNumbers'] = [{'value': phone}]
        
        if company or job_title:
            contact['organizations'] = [{
                'name': company,
                'title': job_title
            }]
        
        if notes:
            contact['biographies'] = [{'value': notes, 'contentType': 'TEXT_PLAIN'}]
        
        # Create contact
        logger.info(f"Creating contact in Google...")
        result = service.people().createContact(body=contact).execute()
        
        contact_name = f"{first_name} {last_name}".strip()
        logger.info(f"✅ Created Google contact: {contact_name}")
        
        details = [f"Name: {contact_name}"]
        if email:
            details.append(f"Email: {email}")
        if phone:
            details.append(f"Phone: {phone}")
        if job_title:
            details.append(f"Title: {job_title}")
        if company:
            details.append(f"Company: {company}")
        
        return f"✅ Contact added to Google Contacts!\n\n" + "\n".join(details)
    
    except Exception as e:
        error_msg = str(e)
        logger.error(f"❌ Failed to add Google contact: {error_msg}", exc_info=True)
        
        # Provide actionable error messages
        if "invalid_grant" in error_msg or "Token has been expired" in error_msg:
            return "❌ Google authentication expired. Please delete token_full_access.pickle and try again."
        elif "credentials" in error_msg.lower():
            return "❌ Google credentials not found. Please run: python reset_google_auth.py"
        elif "403" in error_msg or "forbidden" in error_msg.lower():
            return "❌ Permission denied. Please enable People API in Google Cloud Console and re-authenticate."
        else:
            return f"❌ Error adding contact: {error_msg}\n\nTry: python reset_google_auth.py"


@tool
async def search_google_contacts(query: str) -> str:
    """
    Search Google Contacts by name, email, phone, or company.
    
    Args:
        query: Search query (name, email, phone, or company)
        
    Returns:
        List of matching contacts with their information
    """
    try:
        logger.info(f"🔵 CALLING search_google_contacts: '{query}'")
        creds = get_google_credentials()
        service = build('people', 'v1', credentials=creds)
        
        # Search contacts
        logger.info(f"Searching Google Contacts for: {query}")
        results = service.people().searchContacts(
            query=query,
            readMask='names,emailAddresses,phoneNumbers,organizations,biographies'
        ).execute()
        
        contacts = results.get('results', [])
        logger.info(f"Found {len(contacts)} matching contacts")
        
        if not contacts:
            return f"No contacts found matching '{query}'"
        
        contact_list = []
        for idx, item in enumerate(contacts[:10], 1):  # Limit to 10 results
            person = item.get('person', {})
            
            # Extract name
            names = person.get('names', [])
            name = names[0].get('displayName', 'Unknown') if names else 'Unknown'
            
            # Extract emails
            emails = person.get('emailAddresses', [])
            email = emails[0].get('value', 'No email') if emails else 'No email'
            
            # Extract phones
            phones = person.get('phoneNumbers', [])
            phone = phones[0].get('value', 'No phone') if phones else 'No phone'
            
            # Extract organization
            orgs = person.get('organizations', [])
            if orgs:
                company = orgs[0].get('name', '')
                title = orgs[0].get('title', '')
                job_info = f"{title} at {company}" if title and company else (title or company or 'No job info')
            else:
                job_info = 'No job info'
            
            contact_info = f"{idx}. *{name}*\n   📧 {email}\n   📱 {phone}\n   💼 {job_info}"
            contact_list.append(contact_info)
        
        result = f"*Found {len(contacts)} contact(s):*\n\n" + "\n\n".join(contact_list)
        logger.info(f"✅ Search completed successfully")
        return result
    
    except Exception as e:
        error_msg = str(e)
        logger.error(f"❌ Failed to search Google contacts: {error_msg}", exc_info=True)
        
        if "invalid_grant" in error_msg or "Token has been expired" in error_msg:
            return "❌ Google authentication expired. Please delete token_full_access.pickle and try again."
        elif "credentials" in error_msg.lower():
            return "❌ Google credentials not found. Please run: python reset_google_auth.py"
        elif "403" in error_msg or "forbidden" in error_msg.lower():
            return "❌ Permission denied. Please enable People API in Google Cloud Console and re-authenticate."
        else:
            return f"❌ Error searching contacts: {error_msg}\n\nTry: python reset_google_auth.py"


@tool
async def get_all_google_contacts(max_results: int = 50) -> str:
    """
    Get all Google Contacts.
    
    Args:
        max_results: Maximum number of contacts to retrieve (default: 50)
        
    Returns:
        List of all contacts
    """
    try:
        creds = get_google_credentials()
        service = build('people', 'v1', credentials=creds)
        
        # Get contacts
        results = service.people().connections().list(
            resourceName='people/me',
            pageSize=max_results,
            personFields='names,emailAddresses,phoneNumbers,organizations'
        ).execute()
        
        connections = results.get('connections', [])
        
        if not connections:
            return "No contacts found in Google Contacts"
        
        contact_list = []
        for idx, person in enumerate(connections, 1):
            # Extract name
            names = person.get('names', [])
            name = names[0].get('displayName', 'Unknown') if names else 'Unknown'
            
            # Extract emails
            emails = person.get('emailAddresses', [])
            email = emails[0].get('value', '') if emails else ''
            
            # Extract phones
            phones = person.get('phoneNumbers', [])
            phone = phones[0].get('value', '') if phones else ''
            
            contact_info = f"{idx}. {name}"
            if email:
                contact_info += f" - {email}"
            if phone:
                contact_info += f" - {phone}"
            
            contact_list.append(contact_info)
        
        return f"*📇 Your Google Contacts ({len(connections)}):*\n\n" + "\n".join(contact_list)
    
    except Exception as e:
        logger.error(f"Failed to get Google contacts: {e}", exc_info=True)
        return f"❌ Error retrieving contacts: {str(e)}"


# ==================== GOOGLE DOCS API ====================

@tool
async def create_google_doc(title: str, content: str) -> str:
    """
    Create a new Google Doc.
    
    Args:
        title: Document title
        content: Document content (text)
        
    Returns:
        Document URL and confirmation
    """
    try:
        logger.info(f"🔵 CALLING create_google_doc: '{title}'")
        creds = get_google_credentials()
        docs_service = build('docs', 'v1', credentials=creds)
        drive_service = build('drive', 'v3', credentials=creds)
        
        # Create document
        logger.info(f"Creating Google Doc: {title}")
        doc = docs_service.documents().create(body={'title': title}).execute()
        doc_id = doc.get('documentId')
        logger.info(f"Created doc with ID: {doc_id}")
        
        # Insert content
        requests = [{
            'insertText': {
                'location': {'index': 1},
                'text': content
            }
        }]
        
        logger.info(f"Adding content to document...")
        docs_service.documents().batchUpdate(
            documentId=doc_id,
            body={'requests': requests}
        ).execute()
        
        doc_url = f"https://docs.google.com/document/d/{doc_id}/edit"
        
        logger.info(f"✅ Created Google Doc: {title} | URL: {doc_url}")
        
        return f"✅ *Google Doc Created!*\n\n*Title:* {title}\n*URL:* {doc_url}\n\nYou can now edit and share this document."
    
    except Exception as e:
        error_msg = str(e)
        logger.error(f"❌ Failed to create Google Doc: {error_msg}", exc_info=True)
        
        if "invalid_grant" in error_msg or "Token has been expired" in error_msg:
            return "❌ Google authentication expired. Please delete token_full_access.pickle and try again."
        elif "credentials" in error_msg.lower():
            return "❌ Google credentials not found. Please run: python reset_google_auth.py"
        elif "403" in error_msg or "forbidden" in error_msg.lower():
            return "❌ Permission denied. Please enable Google Docs API in Google Cloud Console and re-authenticate."
        else:
            return f"❌ Error creating document: {error_msg}\n\nTry: python reset_google_auth.py"


@tool
async def read_google_doc(doc_id: str) -> str:
    """
    Read content from a Google Doc.
    
    Args:
        doc_id: Document ID (from URL: docs.google.com/document/d/{DOC_ID}/edit)
        
    Returns:
        Document content
    """
    try:
        logger.info(f"🔵 CALLING read_google_doc: {doc_id}")
        creds = get_google_credentials()
        service = build('docs', 'v1', credentials=creds)
        
        # Get document
        logger.info(f"Reading Google Doc: {doc_id}")
        doc = service.documents().get(documentId=doc_id).execute()
        
        title = doc.get('title', 'Untitled')
        content = []
        
        # Extract text content
        for element in doc.get('body', {}).get('content', []):
            if 'paragraph' in element:
                for text_run in element['paragraph'].get('elements', []):
                    if 'textRun' in text_run:
                        content.append(text_run['textRun'].get('content', ''))
        
        full_content = ''.join(content).strip()
        
        logger.info(f"✅ Read Google Doc: {title} ({len(full_content)} characters)")
        return f"*📄 Document: {title}*\n\n{full_content}"
    
    except Exception as e:
        error_msg = str(e)
        logger.error(f"❌ Failed to read Google Doc: {error_msg}", exc_info=True)
        
        if "invalid_grant" in error_msg or "Token has been expired" in error_msg:
            return "❌ Google authentication expired. Please delete token_full_access.pickle and try again."
        elif "credentials" in error_msg.lower():
            return "❌ Google credentials not found. Please run: python reset_google_auth.py"
        elif "404" in error_msg or "not found" in error_msg.lower():
            return f"❌ Document not found. Please check the document ID: {doc_id}"
        elif "403" in error_msg or "forbidden" in error_msg.lower():
            return "❌ Permission denied. Please enable Google Docs API and re-authenticate."
        else:
            return f"❌ Error reading document: {error_msg}\n\nTry: python reset_google_auth.py"


# ==================== GOOGLE SHEETS API ====================

@tool
async def create_google_sheet(title: str, headers: List[str], data: List[List[str]] = None) -> str:
    """
    Create a new Google Sheet with optional data.
    
    Args:
        title: Sheet title
        headers: Column headers (list of strings)
        data: Optional data rows (list of lists)
        
    Returns:
        Sheet URL and confirmation
    """
    try:
        logger.info(f"🔵 CALLING create_google_sheet: '{title}'")
        creds = get_google_credentials()
        service = build('sheets', 'v4', credentials=creds)
        
        # Create spreadsheet
        spreadsheet = {
            'properties': {'title': title},
            'sheets': [{
                'properties': {'title': 'Sheet1'}
            }]
        }
        
        logger.info(f"Creating Google Sheet: {title}")
        result = service.spreadsheets().create(body=spreadsheet).execute()
        sheet_id = result.get('spreadsheetId')
        logger.info(f"Created sheet with ID: {sheet_id}")
        
        # Add headers and data
        values = [headers]
        if data:
            values.extend(data)
        
        body = {'values': values}
        logger.info(f"Adding {len(values)} rows to sheet...")
        service.spreadsheets().values().update(
            spreadsheetId=sheet_id,
            range='Sheet1!A1',
            valueInputOption='RAW',
            body=body
        ).execute()
        
        sheet_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/edit"
        
        logger.info(f"✅ Created Google Sheet: {title} | URL: {sheet_url}")
        
        return f"✅ *Google Sheet Created!*\n\n*Title:* {title}\n*Columns:* {', '.join(headers)}\n*Rows:* {len(data) if data else 0}\n*URL:* {sheet_url}"
    
    except Exception as e:
        error_msg = str(e)
        logger.error(f"❌ Failed to create Google Sheet: {error_msg}", exc_info=True)
        
        if "invalid_grant" in error_msg or "Token has been expired" in error_msg:
            return "❌ Google authentication expired. Please delete token_full_access.pickle and try again."
        elif "credentials" in error_msg.lower():
            return "❌ Google credentials not found. Please run: python reset_google_auth.py"
        elif "403" in error_msg or "forbidden" in error_msg.lower():
            return "❌ Permission denied. Please enable Google Sheets API and re-authenticate."
        else:
            return f"❌ Error creating spreadsheet: {error_msg}\n\nTry: python reset_google_auth.py"


@tool
async def read_google_sheet(sheet_id: str, range_name: str = "Sheet1") -> str:
    """
    Read data from a Google Sheet.
    
    Args:
        sheet_id: Spreadsheet ID (from URL)
        range_name: Range to read (e.g., "Sheet1", "Sheet1!A1:C10")
        
    Returns:
        Sheet data in formatted text
    """
    try:
        logger.info(f"🔵 CALLING read_google_sheet: {sheet_id} (range: {range_name})")
        creds = get_google_credentials()
        service = build('sheets', 'v4', credentials=creds)
        
        # Get sheet data
        logger.info(f"Reading Google Sheet: {sheet_id}")
        result = service.spreadsheets().values().get(
            spreadsheetId=sheet_id,
            range=range_name
        ).execute()
        
        values = result.get('values', [])
        
        if not values:
            logger.info("Sheet is empty")
            return "Sheet is empty"
        
        # Format as table
        output = []
        for row_idx, row in enumerate(values):
            if row_idx == 0:
                output.append("*" + " | ".join(row) + "*")
                output.append("-" * 50)
            else:
                output.append(" | ".join(row))
        
        logger.info(f"✅ Read Google Sheet: {len(values)} rows")
        return f"*📊 Google Sheet Data:*\n\n" + "\n".join(output)
    
    except Exception as e:
        error_msg = str(e)
        logger.error(f"❌ Failed to read Google Sheet: {error_msg}", exc_info=True)
        
        if "invalid_grant" in error_msg or "Token has been expired" in error_msg:
            return "❌ Google authentication expired. Please delete token_full_access.pickle and try again."
        elif "credentials" in error_msg.lower():
            return "❌ Google credentials not found. Please run: python reset_google_auth.py"
        elif "404" in error_msg or "not found" in error_msg.lower():
            return f"❌ Spreadsheet not found. Please check the sheet ID: {sheet_id}"
        elif "403" in error_msg or "forbidden" in error_msg.lower():
            return "❌ Permission denied. Please enable Google Sheets API and re-authenticate."
        else:
            return f"❌ Error reading spreadsheet: {error_msg}\n\nTry: python reset_google_auth.py"
        logger.error(f"Failed to read Google Sheet: {e}", exc_info=True)
        return f"❌ Error reading spreadsheet: {str(e)}"


# ==================== YOUTUBE DATA API ====================

@tool
async def analyze_youtube_video(video_url: str) -> str:
    """
    Analyze a YouTube video and get detailed information.
    
    Args:
        video_url: YouTube video URL (e.g., https://youtube.com/watch?v=VIDEO_ID)
        
    Returns:
        Video metadata including title, description, statistics, comments
    """
    try:
        creds = get_google_credentials()
        youtube = build('youtube', 'v3', credentials=creds)
        
        # Extract video ID from URL
        if 'v=' in video_url:
            video_id = video_url.split('v=')[1].split('&')[0]
        elif 'youtu.be/' in video_url:
            video_id = video_url.split('youtu.be/')[1].split('?')[0]
        else:
            video_id = video_url
        
        # Get video details
        video_response = youtube.videos().list(
            part='snippet,statistics,contentDetails',
            id=video_id
        ).execute()
        
        if not video_response.get('items'):
            return f"❌ Video not found: {video_url}"
        
        video = video_response['items'][0]
        snippet = video['snippet']
        statistics = video['statistics']
        
        # Format output
        output = [
            f"*🎥 YouTube Video Analysis*\n",
            f"*Title:* {snippet['title']}",
            f"*Channel:* {snippet['channelTitle']}",
            f"*Published:* {snippet['publishedAt'][:10]}",
            f"\n*Statistics:*",
            f"👁️ Views: {statistics.get('viewCount', 'N/A')}",
            f"👍 Likes: {statistics.get('likeCount', 'N/A')}",
            f"💬 Comments: {statistics.get('commentCount', 'N/A')}",
            f"\n*Description:*\n{snippet['description'][:500]}..."
        ]
        
        # Get top comments
        try:
            comments_response = youtube.commentThreads().list(
                part='snippet',
                videoId=video_id,
                maxResults=5,
                order='relevance'
            ).execute()
            
            if comments_response.get('items'):
                output.append("\n*💬 Top Comments:*")
                for idx, item in enumerate(comments_response['items'], 1):
                    comment = item['snippet']['topLevelComment']['snippet']
                    output.append(f"{idx}. {comment['authorDisplayName']}: {comment['textDisplay'][:100]}...")
        except:
            pass  # Comments might be disabled
        
        return "\n".join(output)
    
    except Exception as e:
        logger.error(f"Failed to analyze YouTube video: {e}", exc_info=True)
        return f"❌ Error analyzing video: {str(e)}"


@tool
async def search_youtube(query: str, max_results: int = 5) -> str:
    """
    Search YouTube videos.
    
    Args:
        query: Search query
        max_results: Number of results to return (default: 5)
        
    Returns:
        List of video results with URLs and metadata
    """
    try:
        creds = get_google_credentials()
        youtube = build('youtube', 'v3', credentials=creds)
        
        # Search videos
        search_response = youtube.search().list(
            q=query,
            part='snippet',
            maxResults=max_results,
            type='video'
        ).execute()
        
        videos = []
        for item in search_response.get('items', []):
            video_id = item['id']['videoId']
            snippet = item['snippet']
            
            videos.append(
                f"*{snippet['title']}*\n"
                f"Channel: {snippet['channelTitle']}\n"
                f"URL: https://youtube.com/watch?v={video_id}\n"
            )
        
        return f"*🔍 YouTube Search Results for '{query}':*\n\n" + "\n".join(videos)
    
    except Exception as e:
        logger.error(f"Failed to search YouTube: {e}", exc_info=True)
        return f"❌ Error searching YouTube: {str(e)}"


# ==================== GOOGLE DRIVE API ====================

@tool
async def list_google_drive_files(max_results: int = 20, folder_id: str = None) -> str:
    """
    List files in Google Drive.
    
    Args:
        max_results: Maximum number of files to list (default: 20)
        folder_id: Optional folder ID to list files from specific folder
        
    Returns:
        List of files with names, types, and URLs
    """
    try:
        creds = get_google_credentials()
        service = build('drive', 'v3', credentials=creds)
        
        # Build query
        query = f"'{folder_id}' in parents" if folder_id else None
        
        # List files
        results = service.files().list(
            pageSize=max_results,
            q=query,
            fields="files(id, name, mimeType, createdTime, webViewLink)"
        ).execute()
        
        files = results.get('files', [])
        
        if not files:
            return "No files found in Google Drive"
        
        file_list = []
        for idx, file in enumerate(files, 1):
            mime_type = file.get('mimeType', '')
            icon = '📄'
            if 'folder' in mime_type:
                icon = '📁'
            elif 'document' in mime_type:
                icon = '📝'
            elif 'spreadsheet' in mime_type:
                icon = '📊'
            elif 'image' in mime_type:
                icon = '🖼️'
            
            file_list.append(
                f"{idx}. {icon} *{file['name']}*\n"
                f"   Type: {mime_type.split('.')[-1]}\n"
                f"   URL: {file.get('webViewLink', 'N/A')}"
            )
        
        return f"*📂 Google Drive Files ({len(files)}):*\n\n" + "\n\n".join(file_list)
    
    except Exception as e:
        logger.error(f"Failed to list Drive files: {e}", exc_info=True)
        return f"❌ Error listing files: {str(e)}"


@tool
async def upload_to_google_drive(file_path: str, folder_id: str = None) -> str:
    """
    Upload a file to Google Drive.
    
    Args:
        file_path: Local file path to upload
        folder_id: Optional folder ID to upload to specific folder
        
    Returns:
        Upload confirmation with file URL
    """
    try:
        creds = get_google_credentials()
        service = build('drive', 'v3', credentials=creds)
        
        file_name = os.path.basename(file_path)
        
        file_metadata = {'name': file_name}
        if folder_id:
            file_metadata['parents'] = [folder_id]
        
        media = MediaFileUpload(file_path, resumable=True)
        
        file = service.files().create(
            body=file_metadata,
            media_body=media,
            fields='id, webViewLink'
        ).execute()
        
        return f"✅ *File Uploaded to Google Drive!*\n\n*File:* {file_name}\n*URL:* {file.get('webViewLink')}"
    
    except Exception as e:
        logger.error(f"Failed to upload to Drive: {e}", exc_info=True)
        return f"❌ Error uploading file: {str(e)}"


# Export all Google tools
google_tools_list = [
    # Contacts
    add_google_contact,
    search_google_contacts,
    get_all_google_contacts,
    # Docs
    create_google_doc,
    read_google_doc,
    # Sheets
    create_google_sheet,
    read_google_sheet,
    # YouTube
    analyze_youtube_video,
    search_youtube,
    # Drive
    list_google_drive_files,
    upload_to_google_drive,
]
