import os
import base64
from dotenv import load_dotenv
from langchain_nvidia_ai_endpoints import ChatNVIDIA
from PIL import Image
import requests

load_dotenv()

NVIDIA_API_KEY = os.getenv("NVIDIA_API_KEY")

def test_deepseek_vision():
    """Test if DeepSeek can handle image inputs."""
    
    print("Testing DeepSeek Vision Capabilities...")
    print("=" * 60)
    
    # Initialize DeepSeek model
    llm = ChatNVIDIA(
        model="deepseek-ai/deepseek-v3.1-terminus",
        api_key=NVIDIA_API_KEY,
        temperature=0.3,
        max_tokens=2048
    )
    
    # Test 1: Text-only (baseline)
    print("\n1. Testing text-only input (baseline):")
    try:
        response = llm.invoke("What is 2+2?")
        print(f"✅ Text response: {response.content[:100]}...")
    except Exception as e:
        print(f"❌ Text test failed: {e}")
    
    # Test 2: Try image with base64 (OpenAI format)
    print("\n2. Testing image input (base64 format):")
    try:
        # Create a simple test image or use existing screenshot
        test_image_path = "browser_screenshot.png"
        
        if not os.path.exists(test_image_path):
            # Create a simple test image
            img = Image.new('RGB', (100, 100), color='red')
            img.save(test_image_path)
            print(f"Created test image: {test_image_path}")
        
        with open(test_image_path, 'rb') as img_file:
            image_data = base64.b64encode(img_file.read()).decode('utf-8')
        
        # Try OpenAI-style multimodal input
        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "What do you see in this image?"},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/png;base64,{image_data}"
                        }
                    }
                ]
            }
        ]
        
        response = llm.invoke(messages)
        print(f"✅ Vision response: {response.content[:200]}...")
        print("✅ DeepSeek supports vision!")
        return True
        
    except Exception as e:
        print(f"❌ Vision test failed: {e}")
        print(f"Error type: {type(e).__name__}")
    
    # Test 3: Try direct API call to confirm
    print("\n3. Testing via direct NVIDIA API:")
    try:
        with open(test_image_path, 'rb') as img_file:
            image_data = base64.b64encode(img_file.read()).decode('utf-8')
        
        headers = {
            "Authorization": f"Bearer {NVIDIA_API_KEY}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": "deepseek-ai/deepseek-v3.1-terminus",
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "Describe this image."},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/png;base64,{image_data}"
                            }
                        }
                    ]
                }
            ],
            "max_tokens": 500,
            "temperature": 0.3
        }
        
        response = requests.post(
            "https://integrate.api.nvidia.com/v1/chat/completions",
            headers=headers,
            json=payload,
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            content = result['choices'][0]['message']['content']
            print(f"✅ Direct API vision response: {content[:200]}...")
            print("✅ DeepSeek DOES support vision via direct API!")
            return True
        else:
            print(f"❌ API returned error: {response.status_code}")
            print(f"Response: {response.text[:500]}")
            
    except Exception as e:
        print(f"❌ Direct API test failed: {e}")
    
    print("\n" + "=" * 60)
    print("CONCLUSION: DeepSeek does NOT support vision inputs.")
    print("Recommendation: Use Gemini 2.0 Flash for browser automation (correct choice!)")
    return False


if __name__ == "__main__":
    supports_vision = test_deepseek_vision()
    
    print("\n" + "=" * 60)
    if supports_vision:
        print("🎉 DeepSeek supports vision! You could use it for browser automation.")
    else:
        print("✅ Current architecture is correct:")
        print("   - DeepSeek: Main reasoning/routing (text-only)")
        print("   - Gemini 2.0 Flash: Browser automation with vision")
        print("   - NVIDIA VLM: Available as fallback if needed")
