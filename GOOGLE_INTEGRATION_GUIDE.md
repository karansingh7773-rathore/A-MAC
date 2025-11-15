# 🚀 Google APIs Integration - Complete Guide

## 📋 Overview

Your AI agent now has **full access to Google Workspace** with the following integrations:

### ✅ Integrated Google Services

1. **📇 Google Contacts** - Add, search, and manage contacts
2. **👥 Google People API** - Find people and their detailed information
3. **📝 Google Docs** - Create and read documents
4. **📊 Google Sheets** - Create and read spreadsheets
5. **🎥 YouTube Data API v3** - Analyze videos, get metadata, search
6. **📂 Google Drive** - List, upload, and manage files

### 💾 Cosmos DB - Repurposed

**Previous Use:** Storing contacts, notes, conversation history

**New Use (Strategic):**
- ✅ **User Preferences** - Settings like timezone, language, theme, notification preferences
- ✅ **Agent State** - Multi-day task progress (Techathon projects, research tasks)
- ✅ **Quick Notes** - Temporary notes that don't need Google integration

---

## 🏗️ Architecture Changes

### Before

```
User Request
    ↓
Agent decides
    ↓
Cosmos DB (for everything)
    - Contacts ❌
    - Notes ❌
    - Preferences ❌
    - History ❌
```

### After

```
User Request
    ↓
Agent decides
    ↓
┌─────────────────────┬────────────────────┐
│  Google Services    │   Cosmos DB        │
│  (Primary Storage)  │   (State & Prefs)  │
├─────────────────────┼────────────────────┤
│  • Contacts         │  • Preferences     │
│  • Documents        │  • Agent State     │
│  • Spreadsheets     │  • Quick Notes     │
│  • Files (Drive)    │                    │
│  • Emails (Gmail)   │                    │
│  • Events (Calendar)│                    │
└─────────────────────┴────────────────────┘
```

---

## 🛠️ New Tools Documentation

### 1. Google Contacts

#### **add_google_contact**
```python
add_google_contact(
    first_name="John",
    last_name="Doe",
    email="john@example.com",
    phone="+1-555-0100",
    company="Google",
    job_title="Software Engineer",
    notes="Met at conference, interested in AI"
)
```

**Use Cases:**
- "Save John's contact, he works at Google as a Software Engineer"
- "Add my friend Sarah, her email is sarah@email.com and phone is 555-1234"
- "Remember my professor Dr. Smith, email prof.smith@university.edu, teaches AI"

#### **search_google_contacts**
```python
search_google_contacts(query="John")
search_google_contacts(query="Google")  # Find all contacts from Google
search_google_contacts(query="555-1234")  # Search by phone
```

**Use Cases:**
- "What's Karan's email?"
- "Find all my contacts who work at Microsoft"
- "Do I have anyone named Sarah saved?"

#### **get_all_google_contacts**
```python
get_all_google_contacts(max_results=50)
```

**Use Cases:**
- "Show me all my contacts"
- "List everyone in my contact list"

---

### 2. Google Docs

#### **create_google_doc**
```python
create_google_doc(
    title="Meeting Notes - Nov 13",
    content="Attendees: John, Sarah, Mike\n\nAgenda:\n1. Project updates\n2. Next steps"
)
```

**Use Cases:**
- "Create a document with today's meeting notes"
- "Make a Google Doc for my research paper outline"
- "Write a doc summarizing this conversation"

#### **read_google_doc**
```python
read_google_doc(doc_id="1ABC123xyz...")
```

**Use Cases:**
- "Read this doc: https://docs.google.com/document/d/1ABC123xyz/edit"
- "What does my resume doc say?"
- "Summarize this Google Doc for me"

---

### 3. Google Sheets

#### **create_google_sheet**
```python
create_google_sheet(
    title="Sales Tracker",
    headers=["Date", "Customer", "Amount", "Status"],
    data=[
        ["2025-11-13", "John Doe", "$500", "Paid"],
        ["2025-11-12", "Sarah Smith", "$750", "Pending"]
    ]
)
```

**Use Cases:**
- "Create a sales tracker spreadsheet"
- "Make a budget sheet with columns: Category, Amount, Notes"
- "Create an expense tracker"

#### **read_google_sheet**
```python
read_google_sheet(
    sheet_id="1XYZ789abc...",
    range_name="Sheet1!A1:C10"
)
```

**Use Cases:**
- "Read this sheet: https://docs.google.com/spreadsheets/d/1XYZ789/edit"
- "What's in my budget spreadsheet?"
- "Show me the data from cells A1 to C10"

---

### 4. YouTube Data API

#### **analyze_youtube_video**
```python
analyze_youtube_video(video_url="https://youtube.com/watch?v=dQw4w9WgXcQ")
```

**Returns:**
- Video title
- Channel name
- Description
- Views, likes, comments count
- Published date
- Top comments

**Use Cases:**
- "Analyze this video: https://youtube.com/watch?v=abc123"
- "What's this YouTube video about?"
- "Get stats for this video"
- "Show me the comments on this video"

#### **search_youtube**
```python
search_youtube(query="Python tutorials", max_results=5)
```

**Use Cases:**
- "Find Python tutorial videos"
- "Search YouTube for machine learning courses"
- "Show me popular AI videos"

---

### 5. Google Drive

#### **list_google_drive_files**
```python
list_google_drive_files(max_results=20, folder_id=None)
```

**Use Cases:**
- "Show my Google Drive files"
- "List all files in my Drive"
- "What documents do I have in Drive?"

#### **upload_to_google_drive**
```python
upload_to_google_drive(
    file_path="D:/Documents/report.pdf",
    folder_id=None  # Optional
)
```

**Use Cases:**
- "Upload this report to my Google Drive"
- "Save this file to Drive"
- "Back up this document to Google Drive"

---

### 6. Cosmos DB - User Preferences

#### **save_user_preference**
```python
save_user_preference(
    user_id="12345",
    preference_key="timezone",
    preference_value="America/Los_Angeles"
)
```

**Use Cases:**
- "Set my timezone to PST"
- "Remember I prefer dark mode"
- "Save my notification preference as email"
- "Set my default language to Spanish"

#### **get_user_preferences**
```python
get_user_preferences(user_id="12345")
```

**Use Cases:**
- "What are my settings?"
- "Show my preferences"
- "What timezone did I set?"

---

### 7. Cosmos DB - Agent State

#### **save_agent_state**
```python
save_agent_state(
    user_id="12345",
    task_name="Techathon_ML_Project",
    state_data="Completed: Data collection, preprocessing. Next: Model training with 10k samples"
)
```

**Use Cases:**
- "Remember where we are on the ML project"
- "Save my Techathon progress"
- "Store the current state of my research"

#### **get_agent_state**
```python
get_agent_state(user_id="12345", task_name="Techathon_ML_Project")
```

**Use Cases:**
- "Where did we leave off on the ML project?"
- "Continue my Techathon work"
- "What was the last step we completed?"

---

## 🔑 Setup Instructions

### 1. Google Cloud Console Setup

1. Go to https://console.cloud.google.com/
2. Create a new project or select existing one
3. Enable APIs:
   - Google Contacts API
   - Google People API
   - Google Docs API
   - Google Sheets API
   - YouTube Data API v3
   - Google Drive API
   - Gmail API (already enabled)
   - Google Calendar API (already enabled)

4. Create OAuth 2.0 credentials:
   - Go to "APIs & Services" → "Credentials"
   - Click "Create Credentials" → "OAuth client ID"
   - Application type: Desktop app
   - Download the JSON file
   - Rename it to `credentials.json`
   - Place in your project root: `D:\A-MAC\credentials.json`

### 2. Install Dependencies

```bash
pip install google-auth-oauthlib google-auth-httplib2 google-api-python-client
```

### 3. First Authentication

When you first use any Google tool, a browser will open asking you to:
1. Sign in to your Google account
2. Grant permissions
3. Token will be saved to `token.pickle` for future use

### 4. Environment Variables

No changes needed to `.env` file - uses existing `credentials.json`

---

## 📊 Use Case Examples

### Example 1: Contact Management

**User:** "Save my friend John, he works at Google as a Software Engineer, email is john@google.com"

**Agent Process:**
```python
1. add_google_contact(
    first_name="John",
    email="john@google.com",
    company="Google",
    job_title="Software Engineer"
)
2. Response: "✅ Contact added to Google Contacts!
             Name: John
             Email: john@google.com
             Title: Software Engineer
             Company: Google"
```

---

### Example 2: Document Creation from Analysis

**User:** "Analyze this YouTube video and create a summary document: https://youtube.com/watch?v=abc123"

**Agent Process:**
```python
1. analyze_youtube_video("https://youtube.com/watch?v=abc123")
   # Returns: Title, views, likes, description, comments
   
2. create_google_doc(
    title="YouTube Video Summary - [Video Title]",
    content="""
    Video: [Title]
    Channel: [Channel Name]
    Views: [View Count]
    
    Summary:
    [Description]
    
    Key Points:
    - Point 1
    - Point 2
    
    Top Comments:
    1. [Comment 1]
    2. [Comment 2]
    """
)

3. Response: "✅ Analysis complete! I've created a summary document:
             [Google Doc URL]"
```

---

### Example 3: Email with Contact Lookup

**User:** "Email Karan about the project update"

**Agent Process:**
```python
1. search_google_contacts(query="Karan")
   # Returns: Email: karan@example.com
   
2. Agent asks: "I found Karan (karan@example.com). What should the email say?"

3. User: "Subject: Project Update, Body: The project is on track..."

4. send_email(
    to="karan@example.com",
    subject="Project Update",
    body="The project is on track..."
)
```

---

### Example 4: Multi-Day Task Management

**User:** "Remember my Techathon progress: I've finished data collection and preprocessing, next I need to train the model"

**Agent Process:**
```python
save_agent_state(
    user_id="[user_id]",
    task_name="Techathon_ML_Project",
    state_data="""
    Status: In Progress
    Completed Steps:
    - Data collection (1000 samples)
    - Data preprocessing
    - Feature engineering
    
    Next Steps:
    - Train ML model
    - Evaluate performance
    - Deploy model
    
    Notes: Using scikit-learn, targeting 90% accuracy
    """
)
```

**Next Day:**

**User:** "Continue my Techathon work"

**Agent:**
```python
get_agent_state(user_id="[user_id]", task_name="Techathon_ML_Project")
# Returns saved state

Response: "Here's where we left off on your Techathon project:
- ✅ Data collection (1000 samples)
- ✅ Data preprocessing  
- ✅ Feature engineering

Next up: Train the ML model with scikit-learn, targeting 90% accuracy.

Ready to continue?"
```

---

## 🎯 Best Practices

### 1. Contact Management
- ✅ **DO:** Use Google Contacts for all contact storage
- ❌ **DON'T:** Store contacts in Cosmos DB

### 2. Document Storage
- ✅ **DO:** Create Google Docs/Sheets for persistent documents
- ✅ **DO:** Use Google Drive for file storage
- ❌ **DON'T:** Store document content in Cosmos DB

### 3. User Preferences
- ✅ **DO:** Store settings like timezone, language, theme in Cosmos DB
- ✅ **DO:** Use key-value pairs for preferences
- ❌ **DON'T:** Mix preferences with contacts

### 4. Agent State
- ✅ **DO:** Save progress for multi-day tasks
- ✅ **DO:** Include next steps and current status
- ❌ **DON'T:** Use for simple one-time tasks

---

## 🔄 Migration from Old System

### Old Cosmos DB Contacts → Google Contacts

If you had contacts stored in Cosmos DB, you can migrate them:

1. Get all old contacts from Cosmos DB
2. For each contact, call `add_google_contact()`
3. Delete old Cosmos DB contact entries

**Note:** This migration is NOT automatic. You'll need to do it manually or ask the agent to help.

---

## 🚀 Testing

### Test Google Contacts
```
User: "Save a test contact: John Test, email test@example.com"
User: "Search for John Test"
User: "Show all my contacts"
```

### Test Google Docs
```
User: "Create a test document with the title 'Test Doc' and content 'Hello World'"
```

### Test YouTube
```
User: "Analyze this video: https://youtube.com/watch?v=[ANY_VIDEO_ID]"
User: "Search YouTube for Python tutorials"
```

### Test Google Drive
```
User: "List my Google Drive files"
```

### Test Preferences
```
User: "Set my timezone to PST"
User: "What are my preferences?"
```

### Test Agent State
```
User: "Remember my test project: step 1 complete"
User: "Get the state of my test project"
```

---

## 📈 Performance & Limits

### Google API Quotas
- **Contacts API:** 600 requests/minute
- **Docs API:** 300 requests/minute
- **Sheets API:** 100 requests/minute
- **YouTube API:** 10,000 units/day
- **Drive API:** 1,000 requests/100 seconds

### Cosmos DB
- **No change** to existing limits
- **Reduced usage** (only preferences and state)

---

## 🐛 Troubleshooting

### Error: "Credentials file not found"
**Solution:** Make sure `credentials.json` is in the project root

### Error: "Permission denied"
**Solution:** Re-authenticate by deleting `token.pickle` and running again

### Error: "API not enabled"
**Solution:** Enable the API in Google Cloud Console

### Error: "Quota exceeded"
**Solution:** Wait for quota reset or request increase in Cloud Console

---

## 🎉 Summary

Your agent now has:
- ✅ **11 new Google tools** (Contacts, Docs, Sheets, YouTube, Drive)
- ✅ **4 repurposed Cosmos DB tools** (Preferences & State only)
- ✅ **Full Google Workspace integration**
- ✅ **Professional data management**
- ✅ **Multi-day task persistence**

**Total Tools:** 26 (up from 13)

**Ready to use! Just restart the server and authenticate when prompted.** 🚀
