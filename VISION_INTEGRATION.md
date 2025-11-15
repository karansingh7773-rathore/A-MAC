# NVIDIA VLM Integration - Vision Capabilities

## Overview

Your agent can now **see and understand images and videos**! 🎉

Using NVIDIA's `nemotron-nano-12b-v2-vl` Vision Language Model, the agent can:
- ✅ Analyze images (JPG, PNG, WEBP)
- ✅ Analyze videos (MP4, WEBM, MOV)
- ✅ Compare multiple images
- ✅ Read text from screenshots
- ✅ Identify objects and scenes
- ✅ Describe actions in videos

---

## Setup

### 1. Get NVIDIA API Key

1. Go to: https://build.nvidia.com/
2. Sign up/login with your account
3. Navigate to the API Keys section
4. Create a new API key
5. Copy the API key

### 2. Add API Key to Environment

**Option A: Add to `.env` file**
```bash
NVIDIA_API_KEY=nvapi-your-key-here
```

**Option B: Set as environment variable**
```powershell
# Windows (PowerShell)
$env:NVIDIA_API_KEY="nvapi-your-key-here"

# Windows (CMD)
set NVIDIA_API_KEY=nvapi-your-key-here

# Linux/Mac
export NVIDIA_API_KEY=nvapi-your-key-here
```

### 3. Install Dependencies

```powershell
venv\Scripts\activate
pip install -r requirements.txt
```

---

## How It Works

### Architecture

```
Telegram User
    ↓
Sends Image/Video
    ↓
main.py (Webhook Handler)
    ↓
Downloads & saves to temp file
    ↓
Agent receives prompt with file path
    ↓
Agent calls vision_tools (analyze_image/analyze_video)
    ↓
vision_tools.py encodes media to base64
    ↓
Sends to NVIDIA VLM API
    ↓
Returns analysis
    ↓
Agent sends response to user
```

### Key Features

**1. No Reasoning Mode (`/no_think`)**
- The VLM model's reasoning is DISABLED
- This prevents it from confusing your main agent LLM
- The VLM only provides visual analysis
- Your main agent (Qwen) handles all reasoning and conversation

**2. Automatic Format Detection**
- Supports: .jpg, .jpeg, .png, .webp (images)
- Supports: .mp4, .webm, .mov (videos)
- Validates file types before processing

**3. Smart Query Generation**
- If user provides caption: Uses as specific query
- If no caption: Uses default description prompts

---

## Usage Examples

### Via Telegram

**Image Analysis:**
```
User: [Sends photo of a sunset]
Agent: 🔵 CALLING analyze_image
Agent: The image shows a beautiful sunset over the ocean. The sky is painted with vibrant orange and pink hues...

User: [Sends screenshot] "Read the text"
Agent: 🔵 CALLING analyze_image with query "Read and extract all text visible in this image"
Agent: The text reads: "Welcome to our service. Please login with your credentials..."
```

**Video Analysis:**
```
User: [Sends video clip] "What's happening?"
Agent: 🔵 CALLING analyze_video
Agent: The video shows a person performing a cooking demonstration. They are chopping vegetables...
```

**Multiple Images:**
```
User: [Sends 3 photos] "Compare these"
Agent: 🔵 CALLING analyze_multiple_images
Agent: Comparing the three images:
- Image 1: Shows a daytime street scene
- Image 2: Shows the same location at night
- Image 3: Shows it during winter with snow
```

### Direct Tool Testing

```powershell
python test_vision_tools.py
```

This will:
1. Check if NVIDIA_API_KEY is set
2. Let you test image/video analysis
3. Verify the integration works

---

## Tools Added

### 1. `analyze_image(image_path, query)`

**Purpose:** Analyze a single image

**Parameters:**
- `image_path` (str): Full path to image file
- `query` (str): Question about the image (default: "Describe this image in detail")

**Example:**
```python
result = await analyze_image.ainvoke({
    "image_path": "/path/to/image.jpg",
    "query": "What objects do you see?"
})
```

### 2. `analyze_video(video_path, query)`

**Purpose:** Analyze a video file

**Parameters:**
- `video_path` (str): Full path to video file
- `query` (str): Question about the video (default: "Describe what happens in this video")

**Limitations:**
- Only ONE video at a time
- Max 20MB file size (Telegram limit)

**Example:**
```python
result = await analyze_video.ainvoke({
    "video_path": "/path/to/video.mp4",
    "query": "Summarize the main events"
})
```

### 3. `analyze_multiple_images(image_paths, query)`

**Purpose:** Analyze and compare multiple images

**Parameters:**
- `image_paths` (str): Comma-separated paths
- `query` (str): Question about the images (default: "Compare and describe these images")

**Example:**
```python
result = await analyze_multiple_images.ainvoke({
    "image_paths": "/path/img1.jpg,/path/img2.jpg,/path/img3.jpg",
    "query": "What's different between these images?"
})
```

---

## Integration Points

### Files Modified

**1. `vision_tools.py` (NEW)**
- NVIDIA VLM API integration
- Base64 encoding
- 3 vision tools

**2. `main.py` (UPDATED)**
- Added vision_tools import
- Added photo message handler
- Added video message handler
- Updated system prompt with vision instructions
- Total tools: 29 (was 26)

**3. `requirements.txt` (UPDATED)**
- Added `requests`
- Added `colorama` (for test scripts)

---

## Testing Checklist

### Before Testing:
- [ ] NVIDIA_API_KEY is set in `.env`
- [ ] Dependencies installed (`pip install -r requirements.txt`)
- [ ] Server can start without errors

### Test 1: Image Analysis
1. Start server: `python run.py`
2. Send an image to your Telegram bot
3. Check console for: `🔵 CALLING analyze_image`
4. Verify agent describes the image

### Test 2: Video Analysis
1. Send a short video to your Telegram bot
2. Check console for: `🔵 CALLING analyze_video`
3. Verify agent describes what happens

### Test 3: Image with Caption
1. Send image with caption: "What colors do you see?"
2. Verify agent uses your specific question
3. Check response is relevant to your query

### Test 4: Direct Tool Test
1. Run: `python test_vision_tools.py`
2. Choose option to test
3. Verify results are accurate

---

## Troubleshooting

### Error: "NVIDIA_API_KEY not set"
**Solution:** Add API key to `.env` file or set environment variable

### Error: "Unsupported format"
**Solution:** 
- Images: Use .jpg, .png, or .webp
- Videos: Use .mp4, .webm, or .mov

### Error: "Only single video supported"
**Solution:** Send only ONE video at a time (cannot mix video with other media)

### Error: "Failed to connect to NVIDIA VLM API"
**Solutions:**
- Check internet connection
- Verify API key is valid
- Check if NVIDIA Build API is accessible from your location

### Agent doesn't call vision tools
**Solutions:**
- Check console for 🔵 markers
- Verify vision_tools_list is in all_tools
- Check system prompt includes vision documentation
- Restart server after code changes

---

## API Limits & Best Practices

### NVIDIA API Limits
- Check your plan's rate limits at build.nvidia.com
- Free tier usually has generous limits for testing
- Production use may require paid plan

### File Size Limits
- Images: No specific limit, but keep under 5MB for speed
- Videos: 20MB max (Telegram bot limit)

### Performance Tips
1. **Images:** Usually respond in 2-5 seconds
2. **Videos:** May take 10-30 seconds depending on length
3. **Multiple Images:** Process time increases linearly

### Best Practices
1. Keep videos short (< 30 seconds) for faster processing
2. Use high-quality images for better OCR/text reading
3. Provide specific captions for better-targeted analysis
4. Test with `test_vision_tools.py` before using via Telegram

---

## What's Next?

Your agent now has vision! 🎉

**Capabilities Added:**
- ✅ See and understand images
- ✅ Analyze video content
- ✅ Read text from screenshots
- ✅ Identify objects and scenes
- ✅ Compare multiple images

**Total Agent Tools:** 29
- 13 Core tools
- 11 Google Workspace tools
- 3 Vision tools
- 2 Browser tools

The agent is now multimodal and can handle:
- 💬 Text conversations
- 🎤 Voice messages (transcription)
- 📄 Documents (PDF, DOCX, PPTX, etc.)
- 📸 Images (analysis, OCR, description)
- 🎥 Videos (scene understanding, action recognition)
- 📧 Email & Calendar
- 📊 Google Docs & Sheets
- 👥 Google Contacts
- 🌐 Web search & browsing
- 📝 Notes & preferences

Your AI agent is now **truly multimodal**! 🚀
