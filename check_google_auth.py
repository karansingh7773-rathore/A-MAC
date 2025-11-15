"""
Check Google Authentication Status
Validates credentials, scopes, and API access
"""

import os
import pickle
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

# Required scopes
REQUIRED_SCOPES = [
    # Gmail & Calendar (existing)
    'https://www.googleapis.com/auth/gmail.send',
    'https://www.googleapis.com/auth/calendar',
    'https://www.googleapis.com/auth/calendar.events',
    
    # Google Contacts (new)
    'https://www.googleapis.com/auth/contacts',
    'https://www.googleapis.com/auth/contacts.readonly',
    
    # Google Docs (new)
    'https://www.googleapis.com/auth/documents',
    'https://www.googleapis.com/auth/documents.readonly',
    
    # Google Sheets (new)
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/spreadsheets.readonly',
    
    # Google Drive (new)
    'https://www.googleapis.com/auth/drive.file',
    'https://www.googleapis.com/auth/drive.readonly',
    
    # YouTube Data API (new)
    'https://www.googleapis.com/auth/youtube.readonly',
    
    # Google Drive metadata
    'https://www.googleapis.com/auth/drive.metadata.readonly'
]

def check_auth_status():
    print("=" * 70)
    print("GOOGLE AUTHENTICATION STATUS CHECK")
    print("=" * 70)
    print()
    
    # Check credentials.json
    if not os.path.exists('credentials.json'):
        print("❌ CRITICAL: credentials.json NOT FOUND")
        print("   Download from Google Cloud Console > APIs & Services > Credentials")
        print()
        return False
    else:
        print("✅ credentials.json found")
    
    # Check for old token
    if os.path.exists('token.pickle'):
        print("⚠️  WARNING: Old token.pickle found (2 scopes only)")
        print("   This file should be deleted!")
        print()
    
    # Check for new token
    if not os.path.exists('token_full_access.pickle'):
        print("❌ token_full_access.pickle NOT FOUND")
        print("   You need to authenticate with all 15 scopes")
        print()
        print("   NEXT STEPS:")
        print("   1. Delete token.pickle if it exists")
        print("   2. Run: python reset_google_auth.py")
        print("   3. Restart your server")
        print("   4. Trigger any Google tool to start OAuth flow")
        print()
        return False
    else:
        print("✅ token_full_access.pickle found")
        print()
    
    # Load and validate token
    try:
        with open('token_full_access.pickle', 'rb') as token:
            creds = pickle.load(token)
        
        # Check if token is valid
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                print("⏳ Token expired, attempting refresh...")
                creds.refresh(Request())
                
                # Save refreshed token
                with open('token_full_access.pickle', 'wb') as token:
                    pickle.dump(creds, token)
                
                print("✅ Token refreshed successfully")
            else:
                print("❌ Token invalid and cannot be refreshed")
                print("   Run: python reset_google_auth.py")
                return False
        else:
            print("✅ Token is valid")
        
        # Check scopes
        print()
        print("-" * 70)
        print("SCOPE VALIDATION")
        print("-" * 70)
        
        granted_scopes = creds.scopes if hasattr(creds, 'scopes') and creds.scopes else []
        
        print(f"✅ Granted scopes: {len(granted_scopes)}")
        print(f"📋 Required scopes: {len(REQUIRED_SCOPES)}")
        print()
        
        missing_scopes = []
        for scope in REQUIRED_SCOPES:
            if scope not in granted_scopes:
                missing_scopes.append(scope)
        
        if missing_scopes:
            print(f"❌ Missing {len(missing_scopes)} scopes:")
            for scope in missing_scopes:
                service = scope.split('/')[-1].split('.')[0]
                print(f"   - {service}: {scope}")
            print()
            print("   SOLUTION: Run python reset_google_auth.py")
            return False
        else:
            print("✅ All required scopes granted!")
        
        print()
        print("-" * 70)
        print("API ACCESS TEST")
        print("-" * 70)
        
        # Test each API
        apis_to_test = [
            ('Gmail API', 'gmail', 'v1'),
            ('Calendar API', 'calendar', 'v3'),
            ('People API (Contacts)', 'people', 'v1'),
            ('Docs API', 'docs', 'v1'),
            ('Sheets API', 'sheets', 'v4'),
            ('Drive API', 'drive', 'v3'),
            ('YouTube API', 'youtube', 'v3'),
        ]
        
        for api_name, service_name, version in apis_to_test:
            try:
                service = build(service_name, version, credentials=creds)
                print(f"✅ {api_name} accessible")
            except Exception as e:
                print(f"❌ {api_name} ERROR: {str(e)}")
        
        print()
        print("=" * 70)
        print("✅ AUTHENTICATION STATUS: READY")
        print("=" * 70)
        print()
        print("Your Google tools should work now!")
        print("If you still see errors, check that APIs are enabled in Google Cloud Console.")
        print()
        return True
        
    except Exception as e:
        print(f"❌ Error loading token: {str(e)}")
        print()
        print("   SOLUTION: Run python reset_google_auth.py")
        return False

if __name__ == "__main__":
    check_auth_status()
