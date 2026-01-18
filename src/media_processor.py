import os
import requests
import base64
from openai import OpenAI

class MediaProcessor:
    def __init__(self, openai_key: str, runway_key: str, imgbb_key: str):
        self.client = OpenAI(api_key=openai_key)
        self.runway_key = runway_key
        self.imgbb_key = imgbb_key

    def edit_image(self, image_path: str, prompt: str, output_path: str):
        """Uses DALL-E 2 to edit/generate variations of the logo/base image."""
        if not os.path.exists(image_path):
            print(f"Warning: Image path not found {image_path}")
            return None

        try:
            # Note: DALL-E 2 edit requires a square PNG < 4MB. 
            # Assuming input is valid for this snippet.
            with open(image_path, "rb") as image_file:
                response = self.client.images.edit(
                    model="dall-e-2",
                    image=image_file,
                    prompt=prompt,
                    n=1,
                    size="1024x1024"
                )

            image_url = response.data[0].url
            img_data = requests.get(image_url).content
            with open(output_path, 'wb') as handler:
                handler.write(img_data)

            return output_path

        except Exception as e:
            print(f"Error editing image: {e}")
            return None

    def upload_to_imgbb(self, file_path: str) -> str:
        """Uploads image to ImgBB to get a public URL for Shopify import."""
        url = "https://api.imgbb.com/1/upload"
        try:
            with open(file_path, "rb") as f:
                payload = {"key": self.imgbb_key, "expiration": "60000"} # 16 hours expiry
                files = {"image": f}
                response = requests.post(url, files=files, data=payload)
                response.raise_for_status()
                return response.json()["data"]["url"]
        except Exception as e:
            print(f"ImgBB Upload failed: {e}")
            return None