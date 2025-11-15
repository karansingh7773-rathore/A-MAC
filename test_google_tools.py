"""
Direct test of Google tools (bypasses agent)
Use this to verify tools work independently
"""

import asyncio
import sys
from google_tools import (
    search_google_contacts,
    get_all_google_contacts,
    add_google_contact,
    create_google_doc,
    read_google_doc,
    create_google_sheet,
    read_google_sheet
)

async def test_contacts():
    print("\n" + "=" * 70)
    print("TESTING: Google Contacts")
    print("=" * 70)
    
    # Test 1: List all contacts
    print("\n📋 Test 1: List all contacts...")
    result = await get_all_google_contacts.ainvoke({"max_results": 5})
    print(result)
    
    # Test 2: Search contacts
    print("\n🔍 Test 2: Search contacts for 'test'...")
    result = await search_google_contacts.ainvoke({"query": "test"})
    print(result)
    
    # Test 3: Add contact
    print("\n➕ Test 3: Add test contact...")
    result = await add_google_contact.ainvoke({
        "first_name": "Test",
        "last_name": "Contact",
        "email": "test@example.com",
        "phone": "+1234567890"
    })
    print(result)

async def test_docs():
    print("\n" + "=" * 70)
    print("TESTING: Google Docs")
    print("=" * 70)
    
    # Test 1: Create document
    print("\n📄 Test 1: Create Google Doc...")
    result = await create_google_doc.ainvoke({
        "title": "Test Document from Agent",
        "content": "This is a test document created by the AI agent.\n\nIt should appear in your Google Drive."
    })
    print(result)
    
    # Test 2: Read document (you'll need to provide a doc ID)
    doc_id = input("\n📖 Test 2: Enter a Google Doc ID to read (or press Enter to skip): ").strip()
    if doc_id:
        result = await read_google_doc.ainvoke({"doc_id": doc_id})
        print(result)
    else:
        print("Skipped")

async def test_sheets():
    print("\n" + "=" * 70)
    print("TESTING: Google Sheets")
    print("=" * 70)
    
    # Test 1: Create spreadsheet
    print("\n📊 Test 1: Create Google Sheet...")
    result = await create_google_sheet.ainvoke({
        "title": "Test Spreadsheet from Agent",
        "headers": ["Name", "Email", "Phone"],
        "data": [
            ["John Doe", "john@example.com", "555-1234"],
            ["Jane Smith", "jane@example.com", "555-5678"]
        ]
    })
    print(result)
    
    # Test 2: Read spreadsheet
    sheet_id = input("\n📖 Test 2: Enter a Google Sheet ID to read (or press Enter to skip): ").strip()
    if sheet_id:
        result = await read_google_sheet.ainvoke({"sheet_id": sheet_id, "range_name": "Sheet1"})
        print(result)
    else:
        print("Skipped")

async def main():
    print("\n" + "=" * 70)
    print("GOOGLE TOOLS DIRECT TEST")
    print("=" * 70)
    print("\nThis script tests Google tools directly (bypasses the agent)")
    print("You'll see actual API calls and their results")
    print("\nMake sure you've run: python check_google_auth.py")
    print("=" * 70)
    
    tests = {
        '1': ('Contacts', test_contacts),
        '2': ('Docs', test_docs),
        '3': ('Sheets', test_sheets),
        'all': ('All Tests', None)
    }
    
    print("\nSelect test to run:")
    print("1. Google Contacts (search, list, add)")
    print("2. Google Docs (create, read)")
    print("3. Google Sheets (create, read)")
    print("all. Run all tests")
    
    choice = input("\nEnter choice (1/2/3/all): ").strip().lower()
    
    try:
        if choice == 'all':
            await test_contacts()
            await test_docs()
            await test_sheets()
        elif choice in tests and tests[choice][1]:
            await tests[choice][1]()
        else:
            print("❌ Invalid choice")
            return
        
        print("\n" + "=" * 70)
        print("✅ TESTING COMPLETE")
        print("=" * 70)
        print("\nIf all tests passed:")
        print("- Tools are working correctly")
        print("- The issue is with how the agent invokes them")
        print("\nIf tests failed:")
        print("- Check error messages above")
        print("- Run: python check_google_auth.py")
        print("- Read: GOOGLE_TOOLS_TROUBLESHOOTING.md")
        
    except KeyboardInterrupt:
        print("\n\n❌ Test interrupted by user")
    except Exception as e:
        print(f"\n\n❌ Unexpected error: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
