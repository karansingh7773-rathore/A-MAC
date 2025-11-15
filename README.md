# AI Agent Backend - Guardian Agent

A high-performance, scalable AI agent backend built with FastAPI, LangChain, and NVIDIA AI Endpoints.

## 🚀 Features

- **Speech-to-Text (STT)**: NVIDIA Riva Whisper for audio transcription
- **Text-to-Speech (TTS)**: NVIDIA Riva Magpie for audio generation
- **Web Search**: Tavily Search for real-time information retrieval
- **Email Management**: Send and search emails via Gmail API
- **Calendar Management**: Create and list events via Google Calendar API
- **Database**: Azure Cosmos DB for persistent storage
- **Streaming**: Real-time response streaming from NVIDIA LLM
- **Telegram Integration**: Full webhook support for Telegram bot

## 📋 Prerequisites

- Python 3.9+
- Azure Cosmos DB account (serverless)
- NVIDIA API key
- Tavily API key
- Google Cloud credentials (Gmail & Calendar APIs enabled)
- Telegram Bot Token

## 🛠️ Installation

1. **Clone the repository**
```bash
git clone <your-repo-url>
cd A-MAC
```

2. **Create virtual environment**
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies**
```bash
pip install -r requirements.txt
```

4. **Set up environment variables**
Create a `.env` file in the root directory:
```env
# NVIDIA AI Endpoints
NVIDIA_API_KEY=your_nvidia_api_key

# Telegram Bot
TELEGRAM_BOT_TOKEN=your_telegram_bot_token

# Tavily Search API
TAVILY_API_KEY=your_tavily_api_key

# Google Services (Gmail & Calendar)
GOOGLE_CREDENTIALS_PATH=credentials.json
GOOGLE_TOKEN_PATH=token.pickle

# Azure Cosmos DB
COSMOS_ENDPOINT=your_cosmos_endpoint
COSMOS_KEY=your_cosmos_key
COSMOS_DATABASE_NAME=ai_agent_db
COSMOS_CONTAINER_NAME=user_data
```

5. **Install Playwright browsers**
```bash
playwright install chromium
```

6. **Set up Google OAuth**
- Download `credentials.json` from Google Cloud Console
- Place it in the project root
- First run will open browser for authentication
- Token will be saved as `token.pickle`

## 🏃 Running the Application

### Local Development
```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

### Production (with Gunicorn)
```bash
gunicorn -w 4 -k uvicorn.workers.UvicornWorker main:app --bind 0.0.0.0:8000 --timeout 600
```

## 🔧 Architecture

### Core Components

1. **FastAPI Server** (`main.py`)
   - Webhook endpoint for Telegram
   - Agent orchestration
   - Streaming response support

2. **Tools Module** (`tools.py`)
   - Speech-to-Text (NVIDIA Riva Whisper)
   - Text-to-Speech (NVIDIA Riva Magpie)
   - Web Search (Tavily)
   - Email Tools (Gmail API)
   - Calendar Tools (Google Calendar API)
   - Database Tools (Cosmos DB)

3. **LangChain Agent**
   - NVIDIA Llama-3.1-Nemotron-Ultra-253B as brain
   - ReAct (Reason + Act) loop
   - Tool calling capabilities
   - Streaming support

### Tool Descriptions

| Tool | Description | Usage |
|------|-------------|-------|
| `transcribe_audio` | Convert voice to text | Automatic for voice messages |
| `convert_text_to_speech` | Convert text to audio | On demand or for responses |
| `web_search` | Search the web | Real-time information queries |
| `send_email` | Send emails via Gmail | `send_email(to, subject, body)` |
| `search_emails` | Search Gmail inbox | `search_emails(query)` |
| `create_calendar_event` | Add calendar events | Schedule meetings/events |
| `list_calendar_events` | View upcoming events | Check calendar |
| `navigate_browser` | Navigate to URL | Browser automation |
| `take_screenshot` | Capture page screenshot | Visual analysis |
| `analyze_screenshot` | VLM analysis of screenshot | Understand page content |
| `click_at` | Click at coordinates | Browser interaction |
| `type_text` | Type text | Form filling |
| `press_key` | Press keyboard key | Navigation/submission |
| `scroll_page` | Scroll up/down | Page navigation |
| `save_contact_to_cosmos` | Save contacts | Store user contacts |
| `get_user_history` | Retrieve history | Access past conversations |
| `store_note` | Save notes | Store user notes |

## 📡 API Endpoints

### Health Check
```bash
GET /
```

### Telegram Webhook
```bash
POST /webhook/telegram
```

## 🔐 Security

- API keys stored in `.env` file (never commit!)
- Google OAuth tokens saved securely
- Azure Cosmos DB with key-based auth
- SSL/TLS for all external communications

## 🐛 Debugging

Enable detailed logging:
```python
logging.basicConfig(level=logging.DEBUG)
```

View agent execution:
```python
agent_executor = AgentExecutor(
    agent=agent,
    tools=tools_list,
    verbose=True  # Shows agent reasoning
)
```

## 📦 Deployment

### Azure App Service

1. Create App Service (Python 3.9+)
2. Configure environment variables in portal
3. Set startup command:
```bash
gunicorn -w 2 -k uvicorn.workers.UvicornWorker main:app --bind=0.0.0.0:8000 --timeout=600
```

### Docker (Optional)
```dockerfile
FROM python:3.9-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["gunicorn", "-w", "4", "-k", "uvicorn.workers.UvicornWorker", "main:app", "--bind", "0.0.0.0:8000"]
```

## 🤝 Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit changes (`git commit -m 'Add AmazingFeature'`)
4. Push to branch (`git push origin feature/AmazingFeature`)
5. Open Pull Request

## 📝 License

This project is licensed under the MIT License.

## 🙏 Acknowledgments

- NVIDIA AI Endpoints for powerful models
- LangChain for agent framework
- FastAPI for web framework
- Tavily for web search
- Google for Gmail/Calendar APIs
