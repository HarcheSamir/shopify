import requests
from src.config import IMGBB_API_KEY

def upload_to_imgbb(file_path):
    """
    Uploads a local image to ImgBB and returns the public display URL.
    Required because RunwayML needs a public URL, not a local file.
    """
    url = "https://api.imgbb.com/1/upload"
    try:
        with open(file_path, "rb") as f:
            files = {"image": f}
            payload = {
                "key": IMGBB_API_KEY,
                "expiration": "6000" # URL valid for 100 minutes, plenty for Runway to grab it
            }
            response = requests.post(url, files=files, data=payload)
        
        response.raise_for_status()
        return response.json()["data"]["url"]
    except Exception as e:
        print(f"❌ ImgBB Upload Failed: {e}")
        return None