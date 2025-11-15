"""
NVIDIA VLM (Vision Language Model) Tools
Provides image and video analysis capabilities using nvidia/nemotron-nano-12b-v2-vl
"""

import requests
import os
import base64
import logging
from langchain.tools import tool
from typing import List, Optional

logger = logging.getLogger(__name__)

# NVIDIA API Configuration
NVIDIA_API_URL = "https://integrate.api.nvidia.com/v1/chat/completions"
NVIDIA_API_KEY = os.getenv("NVIDIA_API_KEY")  # Set this in your environment

# Supported media formats
SUPPORTED_FORMATS = {
    "png": ["image/png", "image_url"],
    "jpg": ["image/jpeg", "image_url"],
    "jpeg": ["image/jpeg", "image_url"],
    "webp": ["image/webp", "image_url"],
    "mp4": ["video/mp4", "video_url"],
    "webm": ["video/webm", "video_url"],
    "mov": ["video/mov", "video_url"]
}


def get_file_extension(filename: str) -> str:
    """Extract file extension from filename"""
    _, ext = os.path.splitext(filename)
    return ext[1:].lower()


def get_mime_type(ext: str) -> str:
    """Get MIME type for file extension"""
    return SUPPORTED_FORMATS[ext][0]


def get_media_type(ext: str) -> str:
    """Get media type (image_url or video_url) for file extension"""
    return SUPPORTED_FORMATS[ext][1]


def encode_media_to_base64(file_path: str) -> str:
    """Encode media file to base64 string"""
    try:
        with open(file_path, "rb") as f:
            return base64.b64encode(f.read()).decode("utf-8")
    except Exception as e:
        logger.error(f"Failed to encode media file: {e}")
        raise


def analyze_media_with_nvidia(
    media_files: List[str],
    query: str,
    use_reasoning: bool = False
) -> str:
    """
    Analyze images or video using NVIDIA VLM model
    
    Args:
        media_files: List of file paths to analyze
        query: Question or instruction about the media
        use_reasoning: If True, uses /think mode (reasoning), False uses /no_think
        
    Returns:
        Analysis result from NVIDIA VLM
    """
    if not NVIDIA_API_KEY:
        return "❌ NVIDIA_API_KEY not set. Please add it to your environment variables."
    
    try:
        has_video = False
        
        # Build content array
        content = [{"type": "text", "text": query}]
        
        for media_file in media_files:
            if not os.path.exists(media_file):
                return f"❌ File not found: {media_file}"
            
            ext = get_file_extension(media_file)
            
            if ext not in SUPPORTED_FORMATS:
                return f"❌ Unsupported format: {ext}. Supported: {', '.join(SUPPORTED_FORMATS.keys())}"
            
            media_type_key = get_media_type(ext)
            
            if media_type_key == "video_url":
                has_video = True
            
            logger.info(f"Encoding {media_file} as base64...")
            base64_data = encode_media_to_base64(media_file)
            
            # Add media to content array
            media_obj = {
                "type": media_type_key,
                media_type_key: {
                    "url": f"data:{get_mime_type(ext)};base64,{base64_data}"
                }
            }
            content.append(media_obj)
        
        # Validate video constraints
        if has_video and len(media_files) > 1:
            return "❌ Only single video analysis is supported. Cannot mix video with other media."
        
        # Set system prompt based on reasoning preference and media type
        # For agent integration, we turn off reasoning to avoid confusion
        if has_video:
            # Videos only support /no_think
            system_prompt = "/no_think"
        else:
            # Images support both, use based on preference
            system_prompt = "/think" if use_reasoning else "/no_think"
        
        # Build request
        headers = {
            "Authorization": f"Bearer {NVIDIA_API_KEY}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        
        messages = [
            {
                "role": "system",
                "content": system_prompt,
            },
            {
                "role": "user",
                "content": content,
            }
        ]
        
        payload = {
            "max_tokens": 4096,
            "temperature": 1,
            "top_p": 1,
            "frequency_penalty": 0,
            "presence_penalty": 0,
            "messages": messages,
            "stream": False,
            "model": "nvidia/nemotron-nano-12b-v2-vl",
        }
        
        logger.info(f"Sending request to NVIDIA VLM API...")
        response = requests.post(NVIDIA_API_URL, headers=headers, json=payload, timeout=60)
        response.raise_for_status()
        
        result = response.json()
        
        # Extract the response text
        if "choices" in result and len(result["choices"]) > 0:
            analysis = result["choices"][0]["message"]["content"]
            logger.info(f"✅ NVIDIA VLM analysis completed")
            return analysis
        else:
            logger.error(f"Unexpected API response: {result}")
            return "❌ No analysis result from NVIDIA VLM"
    
    except requests.exceptions.RequestException as e:
        logger.error(f"NVIDIA API request failed: {e}")
        return f"❌ Failed to connect to NVIDIA VLM API: {str(e)}"
    except Exception as e:
        logger.error(f"Error analyzing media: {e}", exc_info=True)
        return f"❌ Error analyzing media: {str(e)}"


@tool
async def analyze_image(image_path: str, query: str = "Describe this image in detail") -> str:
    """
    Analyze an image using NVIDIA VLM model.
    Use this tool when user sends an image or asks to analyze/describe/read an image.
    
    Args:
        image_path: Path to the image file (jpg, png, jpeg, webp)
        query: Question or instruction about the image (default: "Describe this image in detail")
        
    Returns:
        Detailed description and analysis of the image
        
    Examples:
        - "What's in this image?"
        - "Describe this picture"
        - "Read the text in this image"
        - "What objects do you see?"
    """
    logger.info(f"🔵 CALLING analyze_image: {image_path}")
    logger.info(f"Query: {query}")
    
    # Turn off reasoning to avoid confusing main agent LLM
    result = analyze_media_with_nvidia([image_path], query, use_reasoning=False)
    
    logger.info(f"✅ Image analysis completed")
    return result


@tool
async def analyze_video(video_path: str, query: str = "Describe what happens in this video") -> str:
    """
    Analyze a video using NVIDIA VLM model.
    Use this tool when user sends a video or asks to analyze/describe/read a video.
    
    Args:
        video_path: Path to the video file (mp4, webm, mov)
        query: Question or instruction about the video (default: "Describe what happens in this video")
        
    Returns:
        Detailed description and analysis of the video
        
    Examples:
        - "What's happening in this video?"
        - "Describe this video"
        - "Summarize the video content"
        - "What actions do you see?"
    """
    logger.info(f"🔵 CALLING analyze_video: {video_path}")
    logger.info(f"Query: {query}")
    
    # Videos only support /no_think mode
    result = analyze_media_with_nvidia([video_path], query, use_reasoning=False)
    
    logger.info(f"✅ Video analysis completed")
    return result


@tool
async def analyze_multiple_images(
    image_paths: str,
    query: str = "Compare and describe these images"
) -> str:
    """
    Analyze multiple images together using NVIDIA VLM model.
    Use this tool when user sends multiple images or asks to compare images.
    
    Args:
        image_paths: Comma-separated paths to image files (e.g., "image1.jpg,image2.png,image3.jpg")
        query: Question or instruction about the images (default: "Compare and describe these images")
        
    Returns:
        Detailed analysis comparing and describing all images
        
    Examples:
        - "Compare these images"
        - "What's different between these pictures?"
        - "Describe all these images"
    """
    logger.info(f"🔵 CALLING analyze_multiple_images")
    
    # Parse comma-separated paths
    paths = [p.strip() for p in image_paths.split(",")]
    logger.info(f"Analyzing {len(paths)} images")
    logger.info(f"Query: {query}")
    
    # Turn off reasoning to avoid confusing main agent LLM
    result = analyze_media_with_nvidia(paths, query, use_reasoning=False)
    
    logger.info(f"✅ Multiple images analysis completed")
    return result


# Export tools list
vision_tools_list = [
    analyze_image,
    analyze_video,
    analyze_multiple_images,
]
