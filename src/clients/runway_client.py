import requests
import time
from src.config import RUNWAY_API_KEY, RUNWAY_VERSION

def generate_video(prompt_image_url):
    """
    Starts a Gen-4 Turbo video generation task based on an input image URL.
    """
    url = "https://api.dev.runwayml.com/v1/image_to_video"
    headers = {
        "X-Runway-Version": RUNWAY_VERSION,
        "Authorization": f"Bearer {RUNWAY_API_KEY}"
    }
    
    # EXACT PROMPT FROM NOTEBOOK
    prompt_text = """Cinematic vertical 360-degree product showcase: Ultra-smooth, professional turntable rotation revealing every angle of the product in full vertical frame. The camera maintains perfect distance to keep the entire product visible from top to bottom throughout the rotation. Smooth orbital camera movement around the stationary product, emphasizing the full height and proportions. Soft, even studio lighting creates subtle highlights and shadows that define the product's form and premium materials. The rotation is slow, elegant, and continuous - completing one full revolution over the duration. No camera shake, jerky movements, or cuts. The product remains perfectly centered vertically and fully visible at all times. Professional commercial photography aesthetic with clean, minimalist background. Vertical composition optimized to showcase the product's complete silhouette and design details during the elegant rotation."""

    data = {
        "promptImage": prompt_image_url,
        "model": "gen4_turbo",
        "promptText": prompt_text,
        "duration": 5,
        "ratio": "1280:720"
    }

    try:
        response = requests.post(url, headers=headers, json=data)
        response.raise_for_status()
        task_id = response.json()["id"]
        print(f"🎬 Runway Task Started: {task_id}")
        return task_id
    except Exception as e:
        print(f"❌ Runway Generation Request Failed: {e}")
        print(f"Response: {response.text}")
        return None

def poll_video(task_id):
    """
    Polls the RunwayML API until the video is SUCCEEDED or FAILED.
    Returns the URL of the generated video (MP4).
    """
    url = f"https://api.dev.runwayml.com/v1/tasks/{task_id}"
    headers = {
        "X-Runway-Version": RUNWAY_VERSION,
        "Authorization": f"Bearer {RUNWAY_API_KEY}"
    }

    print("⏳ Polling RunwayML for video completion...")
    
    while True:
        try:
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            result = response.json()

            status = result.get("status")
            # print(f"   ...Status: {status}") # Uncomment for verbose debugging

            if status == "SUCCEEDED":
                video_url = result["output"][0]
                print(f"✅ Video Generated: {video_url}")
                return video_url
            elif status == "FAILED":
                print(f"❌ Video Generation Failed: {result.get('failureCode')} - {result.get('failure')}")
                raise Exception("RunwayML Task Failed")
            
            # Wait 5 seconds before next poll (as per notebook)
            time.sleep(5)
            
        except Exception as e:
            print(f"Error polling video: {e}")
            raise e