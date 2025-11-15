"""
Helper script to reset Google OAuth authentication
Run this to delete old tokens and force re-authentication with all scopes
"""

import os
import sys

def reset_google_auth():
    """Delete old token files to force re-authentication"""
    
    token_files = [
        "token.pickle",
        "token_full_access.pickle"
    ]
    
    deleted = []
    not_found = []
    
    for token_file in token_files:
        if os.path.exists(token_file):
            try:
                os.remove(token_file)
                deleted.append(token_file)
                print(f"✅ Deleted: {token_file}")
            except Exception as e:
                print(f"❌ Failed to delete {token_file}: {e}")
        else:
            not_found.append(token_file)
            print(f"ℹ️  Not found: {token_file}")
    
    print("\n" + "="*60)
    
    if deleted:
        print(f"\n✅ Successfully deleted {len(deleted)} token file(s)")
        print("\n📝 Next steps:")
        print("1. Restart your server: python run.py")
        print("2. Trigger any Google tool (e.g., ask to add a contact)")
        print("3. Browser will open asking for permissions")
        print("4. You should now see ALL scopes:")
        print("   • Gmail")
        print("   • Calendar")
        print("   • Contacts")
        print("   • Google Docs")
        print("   • Google Sheets")
        print("   • Google Drive")
        print("   • YouTube")
        print("\n5. Click 'Allow' to grant all permissions")
        print("6. Token will be saved as 'token_full_access.pickle'")
    else:
        print("\nℹ️  No token files to delete.")
        print("\n📝 Next steps:")
        print("1. Make sure credentials.json exists")
        print("2. Run the server: python run.py")
        print("3. Browser will open for first-time authentication")
    
    print("\n" + "="*60 + "\n")

if __name__ == "__main__":
    print("\n" + "="*60)
    print("  Google OAuth Token Reset Tool")
    print("="*60 + "\n")
    
    response = input("This will delete existing Google OAuth tokens. Continue? (y/n): ")
    
    if response.lower() in ['y', 'yes']:
        reset_google_auth()
    else:
        print("\n❌ Cancelled. No changes made.\n")
        sys.exit(0)
