# GOOGLE TOOLS TROUBLESHOOTING GUIDE

## Problem: Google Tools Not Working
**Symptoms:**
- Contact search returns "no contact found" for existing contacts
- Google Docs shows "document deleted" or gives invalid links
- Agent claims to create/read sheets but nothing appears in Google account
- Agent is hallucinating responses instead of calling actual tools

---

## ROOT CAUSE ANALYSIS

### 1. **Authentication Missing**
The most likely cause is that you're using the old `token.pickle` file which only has 2 scopes (Gmail + Calendar), but the new Google tools require **15 scopes**.

### 2. **Agent Not Logging Tool Calls**
I've added comprehensive logging to all Google tools with:
- 🔵 Blue markers when tools are called
- ✅ Green checkmarks when tools succeed
- ❌ Red X marks when tools fail
- Detailed error messages with actionable solutions

### 3. **APIs Not Enabled**
Google Cloud Console requires each API to be enabled individually.

---

## SOLUTION: Step-by-Step Fix

### **STEP 1: Check Current Status**
```powershell
python check_google_auth.py
```

This will tell you:
- ✅ If credentials.json exists
- ⚠️ If old token.pickle needs deletion
- ❌ If token_full_access.pickle is missing
- 📋 Which scopes are granted vs required
- 🔌 Which APIs are accessible

---

### **STEP 2: Reset Authentication**
```powershell
python reset_google_auth.py
```

This will:
- Delete `token.pickle` (old 2-scope token)
- Delete `token_full_access.pickle` (if corrupted)
- Show instructions for re-authentication

---

### **STEP 3: Enable All APIs in Google Cloud Console**

Go to: https://console.cloud.google.com/apis/library

Enable these APIs:
1. **Gmail API** ✅ (already enabled)
2. **Google Calendar API** ✅ (already enabled)
3. **People API** ❌ (NEW - for Contacts)
4. **Google Docs API** ❌ (NEW)
5. **Google Sheets API** ❌ (NEW)
6. **Google Drive API** ❌ (NEW)
7. **YouTube Data API v3** ❌ (NEW)

For each API:
- Click "ENABLE"
- Wait for confirmation
- Move to next API

---

### **STEP 4: Restart Server**
```powershell
# Stop current server (Ctrl+C)
python run.py
```

---

### **STEP 5: Trigger Re-Authentication**

Send a message to your Telegram bot:
```
Search for John in my contacts
```

This will:
1. Attempt to call `search_google_contacts()`
2. Detect missing/invalid credentials
3. Open OAuth consent screen in browser
4. Show ALL 15 scopes for approval
5. Create `token_full_access.pickle` after approval

**IMPORTANT:** Verify you see ALL these permissions in the consent screen:
- ✅ Read, compose, send emails
- ✅ View and edit calendar events
- ✅ See and download your contacts ← **NEW**
- ✅ View and manage your Google Docs ← **NEW**
- ✅ See, edit, create, and delete spreadsheets ← **NEW**
- ✅ View and manage files in Google Drive ← **NEW**
- ✅ View your YouTube account ← **NEW**

If you only see Gmail + Calendar, STOP and check:
- Is `google_tools.py` using the correct SCOPES list? (line 22-48)
- Did you delete old `token.pickle`?
- Did you restart the server?

---

### **STEP 6: Verify Tool Logging**

After re-authentication, test each tool and watch the **console logs**:

**Test Contact Search:**
```
You: Search for John
Agent should log:
🔵 CALLING search_google_contacts: 'John'
Searching Google Contacts for: John
Found 3 matching contacts
✅ Search completed successfully
```

**Test Doc Creation:**
```
You: Create a Google Doc titled "Test Doc" with content "Hello World"
Agent should log:
🔵 CALLING create_google_doc: 'Test Doc'
Creating Google Doc: Test Doc
Created doc with ID: 1abc123...
Adding content to document...
✅ Created Google Doc: Test Doc | URL: https://docs.google.com/document/d/...
```

**Test Sheet Reading:**
```
You: Read this Google Sheet: https://docs.google.com/spreadsheets/d/{SHEET_ID}/edit
Agent should log:
🔵 CALLING read_google_sheet: {SHEET_ID} (range: Sheet1)
Reading Google Sheet: {SHEET_ID}
✅ Read Google Sheet: 5 rows
```

---

## ERROR MESSAGES YOU MIGHT SEE

### **Error: "Google credentials not found"**
**Solution:** Run `python check_google_auth.py` to diagnose

### **Error: "Token has been expired or revoked"**
**Solution:** Run `python reset_google_auth.py`

### **Error: "Permission denied" or "403 Forbidden"**
**Solution:** 
1. Enable the specific API in Google Cloud Console
2. Run `python reset_google_auth.py`
3. Re-authenticate

### **Error: "404 Not Found" (for Docs/Sheets)**
**Solution:** Check the document/sheet ID in the URL

### **Error: No error, but tools don't work**
**This is the hallucination problem!**
**Solution:**
1. Check console logs - do you see 🔵 markers?
2. If NO blue markers → Agent is NOT calling tools
3. If YES blue markers → Check what error appears after
4. The improved error handling will now show you exactly what's wrong

---

## VERIFICATION CHECKLIST

After following all steps, verify:

- [ ] `python check_google_auth.py` shows ✅ for all checks
- [ ] Console logs show 🔵 when tools are called
- [ ] No ❌ error messages in logs
- [ ] Created Google Docs appear in your Google Drive
- [ ] Created Google Sheets appear in your Google Drive
- [ ] Contact searches return actual results
- [ ] All 7 APIs show "accessible" in check_google_auth.py

---

## STILL NOT WORKING?

### Check these common issues:

1. **Wrong credentials.json**
   - Make sure it's for a Desktop App (not Web App or Service Account)
   - Download from: Cloud Console > APIs & Services > Credentials > OAuth 2.0 Client IDs

2. **Two token files exist**
   - Delete BOTH `token.pickle` and `token_full_access.pickle`
   - Re-authenticate fresh

3. **Scopes mismatch between files**
   - Check `google_tools.py` line 22-48
   - Check `tools.py` line 126-145
   - They should have IDENTICAL SCOPES lists (15 scopes)

4. **Agent not using tools at all**
   - Check `main.py` line 50: `all_tools = tools_list + google_tools_list`
   - Check `main.py` line 526: `create_tool_calling_agent(llm, all_tools, ...)`
   - Restart server after any code changes

5. **Async function issues**
   - All Google tools are `async def`
   - LangChain should handle this automatically
   - If not, check LangChain version: `pip show langchain`

---

## QUICK TEST SCRIPT

Create `test_google_direct.py`:

```python
import asyncio
from google_tools import search_google_contacts, create_google_doc

async def test():
    print("Testing contact search...")
    result = await search_google_contacts("test")
    print(result)
    print()
    
    print("Testing doc creation...")
    result = await create_google_doc("Test Doc", "This is a test")
    print(result)

if __name__ == "__main__":
    asyncio.run(test())
```

Run:
```powershell
python test_google_direct.py
```

This bypasses the agent and tests tools directly.

---

## CONTACT ME IF:

- ✅ All APIs enabled
- ✅ token_full_access.pickle exists with 15 scopes
- ✅ check_google_auth.py shows all green
- ❌ Tools STILL don't work

Then we need to:
1. Check if LangChain is properly invoking async tools
2. Verify the agent's tool-calling configuration
3. Check for any middleware blocking Google API calls
