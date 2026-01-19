import shutil
import os
from src.clients.openai_client import Prompts, PromptItem
from src.mocks.data_payloads import MOCK_THEME_CONTENT, MOCK_ABOUT_US_HTML

class MockOpenAIClient:
    def generate_prompts_struct(self, *args, **kwargs):
        print("🧪 [MOCK] Generating 6 Rich Prompts for Product Photography...")
        # Exact structure required by the notebook
        return Prompts(prompts=[
            PromptItem(prompt_type="studio_enhancement", prompt="Mock studio shot", image_size="1024x1536", purpose="Main Product"),
            PromptItem(prompt_type="in_use_1", prompt="Mock lifestyle shot 1", image_size="1024x1024", purpose="Lifestyle"),
            PromptItem(prompt_type="in_use_2", prompt="Mock lifestyle shot 2", image_size="1024x1024", purpose="Lifestyle"),
            PromptItem(prompt_type="in_use_3", prompt="Mock lifestyle shot 3", image_size="1024x1024", purpose="Lifestyle"),
            PromptItem(prompt_type="banner_landscape", prompt="Mock banner landscape", image_size="1536x1024", purpose="Hero"),
            PromptItem(prompt_type="banner_square", prompt="Mock banner square", image_size="1024x1024", purpose="Collection"),
        ])

    def edit_image(self, image_path, prompt, size="1024x1024", output_path="edited.png"):
        print(f"🧪 [MOCK] Editing image {image_path} -> {output_path} (Copying original)")
        # Just copy the original image to the destination to simulate a generated image
        shutil.copy(image_path, output_path)
        return output_path

    def prompt_gpt(self, prompt):
        print(f"🧪 [MOCK] GPT Prompt: {prompt[:50]}...")
        if "ISO 639-1" in prompt:
            return "fr"
        return "Mock GPT Response"

class MockRunwayClient:
    def generate_video(self, img_url):
        print(f"🧪 [MOCK] Requesting Video Generation for {img_url}...")
        return "mock_task_id_12345"

    def poll_video(self, task_id):
        print(f"🧪 [MOCK] Polling video {task_id}... SUCCEEDED")
        # In the main logic, we download this URL. 
        # Since we can't mock a real download from a fake URL easily without changing main logic excessively,
        # we will handle the "download" of this mock video in the main script by checking the flag.
        return "http://mock.url/video.mp4"

class MockContentPrompts:
    def get_new_theme_content(self, *args, **kwargs):
        print("🧪 [MOCK] Returning Massive Theme Content JSON...")
        return MOCK_THEME_CONTENT

    def generate_about_us_content(self, *args, **kwargs):
        print("🧪 [MOCK] Returning About Us HTML...")
        return MOCK_ABOUT_US_HTML