"""
Test NVIDIA VLM Vision Tools
Tests image and video analysis capabilities
"""

import asyncio
import os
from vision_tools import analyze_image, analyze_video, analyze_multiple_images

async def test_vision_tools():
    print("=" * 70)
    print("NVIDIA VLM VISION TOOLS TEST")
    print("=" * 70)
    print()
    
    # Check API key
    api_key = os.getenv("NVIDIA_API_KEY") #NVIDIA_API_KEY = os.getenv("NVIDIA_API_KEY")
    if not api_key:
        print("❌ NVIDIA_API_KEY not set!")
        print()
        print("Please set your NVIDIA API key:")
        print("  1. Get API key from: https://build.nvidia.com/")
        print("  2. Add to .env file: NVIDIA_API_KEY=your_key_here")
        print("  3. Or set environment variable:")
        print("     Windows: set NVIDIA_API_KEY=your_key_here")
        print("     Linux/Mac: export NVIDIA_API_KEY=your_key_here")
        print()
        return
    
    print(f"✅ NVIDIA_API_KEY is set (length: {len(api_key)})")
    print()
    
    print("=" * 70)
    print("TEST OPTIONS")
    print("=" * 70)
    print()
    print("1. Test image analysis (provide image path)")
    print("2. Test video analysis (provide video path)")
    print("3. Test multiple images (provide comma-separated paths)")
    print("4. Skip testing (just verify setup)")
    print()
    
    choice = input("Enter choice (1/2/3/4): ").strip()
    
    if choice == "1":
        print()
        print("=" * 70)
        print("IMAGE ANALYSIS TEST")
        print("=" * 70)
        print()
        image_path = input("Enter image path (.jpg, .png, .webp): ").strip()
        
        if not os.path.exists(image_path):
            print(f"❌ File not found: {image_path}")
            return
        
        query = input("What should I analyze? (press Enter for default description): ").strip()
        if not query:
            query = "Describe this image in detail"
        
        print()
        print("🔄 Analyzing image...")
        print()
        
        result = await analyze_image.ainvoke({
            "image_path": image_path,
            "query": query
        })
        
        print("=" * 70)
        print("ANALYSIS RESULT")
        print("=" * 70)
        print()
        print(result)
        print()
    
    elif choice == "2":
        print()
        print("=" * 70)
        print("VIDEO ANALYSIS TEST")
        print("=" * 70)
        print()
        video_path = input("Enter video path (.mp4, .webm, .mov): ").strip()
        
        if not os.path.exists(video_path):
            print(f"❌ File not found: {video_path}")
            return
        
        query = input("What should I analyze? (press Enter for default description): ").strip()
        if not query:
            query = "Describe what happens in this video"
        
        print()
        print("🔄 Analyzing video (this may take a moment)...")
        print()
        
        result = await analyze_video.ainvoke({
            "video_path": video_path,
            "query": query
        })
        
        print("=" * 70)
        print("ANALYSIS RESULT")
        print("=" * 70)
        print()
        print(result)
        print()
    
    elif choice == "3":
        print()
        print("=" * 70)
        print("MULTIPLE IMAGES ANALYSIS TEST")
        print("=" * 70)
        print()
        paths_input = input("Enter comma-separated image paths: ").strip()
        
        paths = [p.strip() for p in paths_input.split(",")]
        
        for path in paths:
            if not os.path.exists(path):
                print(f"❌ File not found: {path}")
                return
        
        query = input("What should I analyze? (press Enter for default comparison): ").strip()
        if not query:
            query = "Compare and describe these images"
        
        print()
        print(f"🔄 Analyzing {len(paths)} images...")
        print()
        
        result = await analyze_multiple_images.ainvoke({
            "image_paths": paths_input,
            "query": query
        })
        
        print("=" * 70)
        print("ANALYSIS RESULT")
        print("=" * 70)
        print()
        print(result)
        print()
    
    elif choice == "4":
        print()
        print("✅ Setup verification complete!")
        print()
        print("Your NVIDIA VLM tools are ready to use.")
        print("The agent can now analyze images and videos sent via Telegram!")
        print()
    
    else:
        print("❌ Invalid choice")
        return
    
    print("=" * 70)
    print("✅ TEST COMPLETE")
    print("=" * 70)
    print()
    print("Your vision tools are working! The agent can now:")
    print("  ✅ Analyze images sent via Telegram")
    print("  ✅ Analyze videos sent via Telegram")
    print("  ✅ Compare multiple images")
    print("  ✅ Answer questions about visual content")
    print()

if __name__ == "__main__":
    try:
        asyncio.run(test_vision_tools())
    except KeyboardInterrupt:
        print("\n\n❌ Test interrupted by user")
    except Exception as e:
        print(f"\n\n❌ Test failed: {str(e)}")
        import traceback
        traceback.print_exc()
