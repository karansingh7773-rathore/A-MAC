"""
Test script for document reading functionality
"""
import asyncio
from tools import read_document

async def test_document_reading():
    """Test the read_document tool"""
    
    print("="*60)
    print("Testing Document Reading Tool")
    print("="*60)
    
    # Test with a sample path (you can replace this with an actual file path)
    test_file = input("\nEnter the full path to a document to test (PDF, DOCX, PPTX, TXT, etc.):\n> ")
    
    if not test_file.strip():
        print("\nNo file path provided. Using example path...")
        test_file = "D:/Documents/sample.pdf"
    
    print(f"\nReading document: {test_file}\n")
    print("-"*60)
    
    result = await read_document(test_file)
    
    print(result)
    print("\n" + "="*60)

if __name__ == "__main__":
    asyncio.run(test_document_reading())
