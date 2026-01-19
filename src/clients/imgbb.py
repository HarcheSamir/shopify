import requests
from src.config import IMGBB_API_KEY

def upload_to_imgbb(file_path):
    url = "https://api.imgbb.com/1/upload"
    with open(file_path, "rb") as f:
        files = {"image": f}
        payload = {"key": IMGBB_API_KEY, "expiration": "6000"}
        response = requests.post(url, files=files, data=payload)
    response.raise_for_status()
    return response.json()["data"]["url"]