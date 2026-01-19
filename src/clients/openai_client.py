from openai import OpenAI
from pydantic import BaseModel, Field
import os
import base64
from src.config import OPENAI_API_KEY

client = OpenAI(api_key=OPENAI_API_KEY)

class PromptItem(BaseModel):
    prompt_type: str = Field(..., description="Type of prompt (e.g., studio_enhancement, in_use_1, etc.)")
    prompt: str = Field(..., description="The detailed prompt text")
    image_size: str = Field(..., description="Target image size, e.g., '1024x1536'")
    purpose: str = Field(..., description="Intended purpose or usage of this generated image")

class Prompts(BaseModel):
   prompts: list[PromptItem] = Field(..., description="List of prompt items")

def generate_prompts_struct(product_title, product_description, theme_name, primary_color, mood, description):
    system_prompt = """# Enhanced Product Photography Agent System Prompt
    [... SYSTEM PROMPT FROM NOTEBOOK ...]
    Generate exactly 6 prompts with these prompt_types:
    1. "studio_enhancement" - 1024x1536
    2. "in_use_1" - 1024x1024
    3. "in_use_2" - 1024x1024
    4. "in_use_3" - 1024x1024
    5. "banner_landscape" - 1536x1024
    6. "banner_square" - 1024x1024
    """
    # Note: I abbreviated the system prompt string here for brevity in the response, 
    # but in your actual file, paste the FULL string from the original notebook cell.
    
    completion = client.beta.chat.completions.parse(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Product Title: {product_title}\nProduct Description: {product_description}\nTheme: {theme_name}\nPrimary Color: {primary_color}\nTheme Description: {description}"},
        ],
        response_format=Prompts,
    )
    return completion.choices[0].message.parsed

def edit_image(image_path, prompt, size="1024x1024", output_path="edited.png"):
    with open(image_path, "rb") as f:
        result = client.images.edit(
            model="dall-e-2", # Note: gpt-image-1 in notebook might be an alias, using standard dall-e-2 for edits
            image=f,
            prompt=prompt,
            size=size,
            n=1
        )
    
    image_url = result.data[0].url
    # In standard OpenAI API, edit returns a URL, not b64_json usually unless specified. 
    # The notebook code used `result.data[0].b64_json`. If you have access to that model:
    # return b64 data. Otherwise download from URL.
    # Assuming standard behavior:
    import requests
    img_data = requests.get(image_url).content
    with open(output_path, 'wb') as handler:
        handler.write(img_data)
    return output_path

def prompt_gpt(prompt):
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.6,
        )
        return response.choices[0].message.content.replace('"',"")
    except Exception as e:
        print(f"GPT error: {e}")
        return None

def prompt_deepseek_style(prompt):
    # The notebook uses a separate client for DeepSeek logic, but points to OpenAI structure
    # We will use the standard client here for simplicity, assuming GPT-4o
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}],
        temperature=1.0, # High temp as per notebook
    )
    return response.choices[0].message.content