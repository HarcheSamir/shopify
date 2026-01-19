import os
import requests
import uuid
import re

def download_file(url, output_path):
    response = requests.get(url, stream=True)
    if response.status_code == 200:
        with open(output_path, "wb") as f:
            for chunk in response.iter_content(1024):
                f.write(chunk)
        print(f"Downloaded: {output_path}")
        return output_path
    else:
        print(f"Failed to download: {url}")
        return None

def encode_image_to_base64(image_path):
    import base64
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')

def extract_language_code(language_name, openai_client):
    prompt = f"""
    Please provide only the 2-letter ISO 639-1 language code for the language: {language_name}
    Return only the 2-letter code, nothing else.
    Language: {language_name}
    Code:"""
    try:
        response = openai_client.prompt_gpt(prompt)
        code = response.strip().lower()
        match = re.search(r'\b([a-z]{2})\b', code)
        if match:
            return match.group(1)
        return "en"
    except Exception:
        return "en"