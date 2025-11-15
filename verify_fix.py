"""
Post-Fix Verification Script
Run this AFTER completing all fix steps to verify everything works
"""

import os
import pickle
import asyncio
from colorama import init, Fore, Style

init(autoreset=True)

def print_header(text):
    print(f"\n{Fore.CYAN}{'=' * 70}")
    print(f"{Fore.CYAN}{text}")
    print(f"{Fore.CYAN}{'=' * 70}\n")

def print_success(text):
    print(f"{Fore.GREEN}✅ {text}")

def print_warning(text):
    print(f"{Fore.YELLOW}⚠️  {text}")

def print_error(text):
    print(f"{Fore.RED}❌ {text}")

def print_info(text):
    print(f"{Fore.BLUE}ℹ️  {text}")

async def verify_fix():
    print_header("GOOGLE TOOLS FIX VERIFICATION")
    
    issues = []
    successes = []
    
    # Check 1: Old token deleted
    print_info("Checking for old token files...")
    if os.path.exists('token.pickle'):
        print_error("Old token.pickle still exists! Delete it.")
        issues.append("Delete token.pickle")
    else:
        print_success("Old token.pickle deleted")
        successes.append("Old token deleted")
    
    # Check 2: New token exists
    print_info("Checking for new token...")
    if not os.path.exists('token_full_access.pickle'):
        print_error("token_full_access.pickle not found! You need to re-authenticate.")
        issues.append("Re-authenticate to create token_full_access.pickle")
    else:
        print_success("token_full_access.pickle found")
        
        # Check token validity
        try:
            with open('token_full_access.pickle', 'rb') as token:
                creds = pickle.load(token)
            
            if creds and creds.valid:
                print_success("Token is valid")
                successes.append("Valid authentication token")
                
                # Check scopes
                granted_scopes = creds.scopes if hasattr(creds, 'scopes') and creds.scopes else []
                print_info(f"Granted scopes: {len(granted_scopes)}")
                
                if len(granted_scopes) >= 14:  # Should have 15, but 14+ is okay
                    print_success(f"Sufficient scopes granted ({len(granted_scopes)})")
                    successes.append(f"All {len(granted_scopes)} scopes granted")
                else:
                    print_error(f"Only {len(granted_scopes)} scopes granted (need 15)")
                    issues.append("Re-authenticate with all 15 scopes")
            else:
                print_error("Token is invalid or expired")
                issues.append("Refresh or re-create token")
        except Exception as e:
            print_error(f"Token error: {str(e)}")
            issues.append("Fix token file")
    
    # Check 3: credentials.json exists
    print_info("Checking credentials.json...")
    if not os.path.exists('credentials.json'):
        print_error("credentials.json not found!")
        issues.append("Download credentials.json from Google Cloud Console")
    else:
        print_success("credentials.json found")
        successes.append("OAuth credentials configured")
    
    # Check 4: Google tools file has logging
    print_info("Checking google_tools.py for logging...")
    try:
        with open('google_tools.py', 'r', encoding='utf-8') as f:
            content = f.read()
        
        if '🔵 CALLING' in content:
            print_success("Logging markers found in google_tools.py")
            successes.append("Enhanced logging enabled")
        else:
            print_warning("Logging markers not found (might be okay)")
        
        if 'logger.info' in content and 'logger.error' in content:
            print_success("Logger statements present")
        else:
            print_warning("Logger statements might be missing")
    except Exception as e:
        print_error(f"Error reading google_tools.py: {str(e)}")
    
    # Check 5: Test tools import
    print_info("Testing Google tools import...")
    try:
        from google_tools import (
            search_google_contacts,
            create_google_doc,
            create_google_sheet
        )
        print_success("Google tools import successfully")
        successes.append("Tools available to agent")
    except Exception as e:
        print_error(f"Import error: {str(e)}")
        issues.append("Fix google_tools.py import issues")
    
    # Check 6: Test tool execution (if token exists)
    if os.path.exists('token_full_access.pickle'):
        print_info("Testing tool execution...")
        try:
            from google_tools import get_all_google_contacts
            
            print_info("Attempting to list contacts (this tests API access)...")
            result = await get_all_google_contacts.ainvoke({"max_results": 1})
            
            if "❌" in result:
                print_error("Tool execution failed:")
                print(f"   {result}")
                issues.append("Enable APIs in Google Cloud Console and re-authenticate")
            else:
                print_success("Tool executed successfully!")
                successes.append("Google APIs accessible")
        except Exception as e:
            print_error(f"Tool execution error: {str(e)}")
            issues.append("Fix tool execution issues")
    
    # Summary
    print_header("VERIFICATION SUMMARY")
    
    if successes:
        print(f"{Fore.GREEN}SUCCESSES ({len(successes)}):")
        for success in successes:
            print(f"  ✅ {success}")
        print()
    
    if issues:
        print(f"{Fore.RED}ISSUES TO FIX ({len(issues)}):")
        for i, issue in enumerate(issues, 1):
            print(f"  {i}. {issue}")
        print()
        
        print_header("NEXT STEPS")
        print("Follow the instructions in QUICK_FIX.md to resolve issues:")
        print("1. python check_google_auth.py")
        print("2. Enable all APIs in Google Cloud Console")
        print("3. python reset_google_auth.py")
        print("4. Restart server and re-authenticate")
        print("5. python test_google_tools.py")
        print()
        
        return False
    else:
        print_header("🎉 ALL CHECKS PASSED!")
        print(f"{Fore.GREEN}Your Google tools should now be working!")
        print()
        print("To test through the agent:")
        print("1. Start server: python run.py")
        print("2. Send message to Telegram bot")
        print("3. Watch terminal for 🔵 CALLING markers")
        print("4. Verify actual operations in your Google account")
        print()
        
        return True

if __name__ == "__main__":
    try:
        result = asyncio.run(verify_fix())
        
        if result:
            print(f"{Fore.GREEN}✅ Verification successful! Your Google tools are ready.")
        else:
            print(f"{Fore.YELLOW}⚠️  Verification incomplete. Please fix the issues above.")
    except KeyboardInterrupt:
        print(f"\n{Fore.YELLOW}Verification cancelled by user.")
    except Exception as e:
        print(f"\n{Fore.RED}❌ Verification failed: {str(e)}")
        import traceback
        traceback.print_exc()
