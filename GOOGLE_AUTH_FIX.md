# 🔑 Google OAuth - Full Permissions Setup

## 🐛 Problem

You're only seeing **Gmail** and **Calendar** permissions, but we need **all Google services**:
- ✅ Gmail (already shown)
- ✅ Calendar (already shown)
- ❌ Contacts (missing)
- ❌ Google Docs (missing)
- ❌ Google Sheets (missing)
- ❌ Google Drive (missing)
- ❌ YouTube (missing)

## 🔍 Root Cause

The old `token.pickle` file was created with limited scopes (only Gmail + Calendar). We need to delete it and re-authenticate with **all scopes**.

## ✅ Solution

### Step 1: Delete Old Token

Run this command in PowerShell:

```powershell
python reset_google_auth.py
```

**OR** manually delete:
```powershell
Remove-Item token.pickle -ErrorAction SilentlyContinue
Remove-Item token_full_access.pickle -ErrorAction SilentlyContinue
```

### Step 2: Restart Server

```powershell
python run.py
```

### Step 3: Trigger Authentication

Send a message to your bot that uses a Google tool:

**Example:**
```
"Add a test contact: John Test, email test@example.com"
```

### Step 4: Grant All Permissions

A browser window will open showing:

**"Select what A-MAC can access"**

You should now see **ALL** of these:

- ☑️ **Gmail** - Read, compose, and send emails
- ☑️ **Calendar** - See, edit, share, and delete calendars
- ☑️ **Contacts** - See and manage contacts ← **NEW!**
- ☑️ **Google Docs** - View and manage documents ← **NEW!**
- ☑️ **Google Sheets** - View and manage spreadsheets ← **NEW!**
- ☑️ **Google Drive** - View and manage Drive files ← **NEW!**
- ☑️ **YouTube** - View YouTube account ← **NEW!**

**Click "Continue" or "Allow"** to grant all permissions.

### Step 5: Verify

Check that `token_full_access.pickle` was created:

```powershell
ls token_full_access.pickle
```

## 🎯 What Changed

### Files Modified:

1. **`google_tools.py`**
   - Changed token file: `token.pickle` → `token_full_access.pickle`
   - Added comprehensive scopes list
   - Added scope validation (auto-detects missing scopes)

2. **`tools.py`**
   - Updated to use same token file: `token_full_access.pickle`
   - Updated scopes to match `google_tools.py`

3. **`reset_google_auth.py`** (NEW)
   - Helper script to delete old tokens
   - Provides step-by-step instructions

## 🔄 Token Files Explained

| File | Purpose | Status |
|------|---------|--------|
| `token.pickle` | Old token (Gmail + Calendar only) | ❌ Delete this |
| `token_full_access.pickle` | New token (all Google services) | ✅ Use this |

## 🧪 Testing After Setup

Once authentication is complete, test each service:

### Test Contacts
```
User: "Add a test contact: Jane Doe, email jane@test.com"
User: "Search for Jane"
```

### Test Google Docs
```
User: "Create a Google Doc titled 'Test Document' with content 'Hello World'"
```

### Test Google Sheets
```
User: "Create a spreadsheet called 'Test Sheet' with columns Name, Email, Phone"
```

### Test YouTube
```
User: "Search YouTube for Python tutorials"
```

### Test Drive
```
User: "List my Google Drive files"
```

## ❗ Important Notes

### If You Still See Only Gmail + Calendar:

1. **Make sure old token is deleted:**
   ```powershell
   Remove-Item token.pickle -Force
   ```

2. **Check scopes in code:**
   - `google_tools.py` line ~22: Should show all scopes
   - `tools.py` line ~128: Should show all scopes

3. **Clear browser cache:**
   - Google might cache the old consent screen
   - Try in incognito/private mode

4. **Revoke and re-grant:**
   - Go to https://myaccount.google.com/permissions
   - Find "A-MAC" and click "Remove Access"
   - Re-run authentication

### Scope Validation

The code now automatically checks if the token has all required scopes. If any are missing, it will:
1. Log a warning
2. Delete the old token
3. Force re-authentication

## 🎉 Expected Result

After successful authentication, you should see:

```
✅ Credentials saved to token_full_access.pickle
```

And when you use Google tools, they should work without asking for permissions again.

## 🔧 Troubleshooting

### Error: "Access blocked: This app's request is invalid"

**Solution:** Enable the APIs in Google Cloud Console:
1. Go to https://console.cloud.google.com/apis/library
2. Search and enable:
   - People API (for Contacts)
   - Google Docs API
   - Google Sheets API
   - YouTube Data API v3
   - Google Drive API

### Error: "The OAuth client was not found"

**Solution:** Make sure `credentials.json` is valid and in the project root.

### Error: "insufficient authentication scopes provided"

**Solution:** Delete `token_full_access.pickle` and re-authenticate.

---

## 📝 Quick Reference

**Delete tokens:**
```powershell
python reset_google_auth.py
```

**Restart server:**
```powershell
python run.py
```

**Test authentication:**
```
"Add test contact: John Test, test@example.com"
```

**Expected scopes count:** 15 scopes total (not just 2)

---

**Once you see all 7 services in the consent screen, you're good to go!** 🚀
