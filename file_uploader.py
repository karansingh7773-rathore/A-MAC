# file_uploader.py
import os
import httpx
import logging

logger = logging.getLogger(__name__)

# This is the CORRECT global endpoint from the documentation
# We POST directly to this. We do NOT send a GET request.
UPLOAD_URL = "https://upload.gofile.io/uploadfile"

async def upload_file_to_public_url(local_file_path: str) -> str:
    """
    Uploads a local file to gofile.io and returns the public download page URL.
    This version uses the correct global endpoint from the official API docs.
    """
    if not os.path.exists(local_file_path):
        logger.error(f"File not found at {local_file_path}")
        raise FileNotFoundError(f"File not found at {local_file_path}")

    logger.info(f"Uploading file: {local_file_path} to {UPLOAD_URL}...")
    
    try:
        # Open the file and prepare the multipart POST
        with open(local_file_path, "rb") as f:
            # Gofile requires the file to be sent as 'multipart/form-data'
            # The key for the file must be "file"
            file_tuple = (os.path.basename(local_file_path), f.read(), "application/octet-stream")
            files_payload = {"file": file_tuple}

            # Set a long timeout for the upload itself
            # Add follow_redirects=True for safety
            async with httpx.AsyncClient(timeout=60.0, follow_redirects=True) as client:
                # We do ONE POST request directly to the global URL
                response = await client.post(UPLOAD_URL, files=files_payload)
                
                response.raise_for_status()
                
                upload_data = response.json()
                
                if upload_data.get("status") == "ok":
                    # We return the public download page
                    public_url = upload_data["data"]["downloadPage"]
                    logger.info(f"File uploaded successfully. Public URL: {public_url}")
                    return public_url
                else:
                    logger.error(f"GoFile upload failed. Status: {upload_data.get('status')}")
                    raise Exception("GoFile upload failed.")

    except httpx.HTTPStatusError as e:
        logger.error(f"Failed to upload to GoFile. Status: {e.response.status_code}, Response: {e.response.text}")
        raise Exception(f"Failed to upload to GoFile: {e.response.status_code}")
    except Exception as e:
        logger.error(f"An unexpected error occurred during file upload: {e}", exc_info=True)
        raise Exception(f"An unexpected error occurred during file upload: {e}")