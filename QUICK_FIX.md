# QUICK FIX - Google Tools Not Working

## 🔴 PROBLEM
- Agent says "no contact found" for existing contacts
- Google Docs show "deleted" or invalid links  
- Agent claims to create sheets but nothing appears

## ✅ SOLUTION (5 minutes)

### 1️⃣ Check what's wrong
```powershell
python check_google_auth.py
```

### 2️⃣ Enable APIs (if not already)
Go to: https://console.cloud.google.com/apis/library

Click "ENABLE" for each:
- People API
- Google Docs API
- Google Sheets API
- Google Drive API
- YouTube Data API v3

### 3️⃣ Delete old tokens
```powershell
python reset_google_auth.py
```

### 4️⃣ Restart and re-authenticate
```powershell
python run.py
```

In Telegram send: `search for test`

Browser will open → Approve ALL permissions

### 5️⃣ Verify it works
```powershell
python test_google_tools.py
```

Choose "all" to test everything

---

## 🔍 HOW TO KNOW IT'S WORKING

Watch your terminal when using Telegram bot:

**WORKING ✅**
```
🔵 CALLING search_google_contacts: 'John'
Searching Google Contacts for: John
Found 3 matching contacts
✅ Search completed successfully
```

**BROKEN ❌**
```
(No 🔵 marker)
Agent just responds without calling any tool
```

---

## 📚 MORE HELP
- Full guide: `GOOGLE_TOOLS_TROUBLESHOOTING.md`
- What changed: `WHAT_I_FIXED.md`
