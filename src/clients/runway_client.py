import requests
import time
from src.config import RUNWAY_API_KEY, RUNWAY_VERSION

def generate_video(prompt_image_url):
    url = "https://api.dev.runwayml.com/v1/image_to_video"
    headers = {
        "X-Runway-Version": RUNWAY_VERSION,
        "Authorization": f"Bearer {RUNWAY_API_KEY}"
    }
    data = {
        "promptImage": prompt_image_url,
        "model": "gen4_turbo",
        "promptText": "Cinematic vertical 360-degree product showcase...", # Paste full prompt from notebook
        "duration": 5,
        "ratio": "1280:720"
    }
    response = requests.post(url, headers=headers, json=data)
    response.raise_for_status()
    return response.json()["id"]

def poll_video(task_id):
    url = f"https://api.dev.runwayml.com/v1/tasks/{task_id}"
    headers = {
        "X-Runway-Version": RUNWAY_VERSION,
        "Authorization": f"Bearer {RUNWAY_API_KEY}"
    }
    while True:
        response = requests.get(url, headers=headers)
        result = response.json()
        status = result.get("status")
        print(f"Runway Status: {status}")
        if status == "SUCCEEDED":
            return result["output"][0]
        elif status == "FAILED":
            raise Exception("Video generation failed.")
        time.sleep(5)