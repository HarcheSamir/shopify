from openai import OpenAI
from pydantic import BaseModel, Field
import os
import base64
import requests
import re
from src.config import OPENAI_API_KEY, THEME_NAME, THEME_PRIMARY_COLOR, THEME_MOOD, THEME_DESCRIPTION

# Initialize Client
client = OpenAI(api_key=OPENAI_API_KEY)

# --- STRUCTURED DATA CLASSES ---
class PromptItem(BaseModel):
    prompt_type: str = Field(..., description="Type of prompt (e.g., studio_enhancement, in_use_1, etc.)")
    prompt: str = Field(..., description="The detailed prompt text")
    image_size: str = Field(..., description="Target image size, MUST be '1024x1024'")
    purpose: str = Field(..., description="Intended purpose or usage of this generated image")

class Prompts(BaseModel):
   prompts: list[PromptItem] = Field(..., description="List of prompt items")

# --- PROMPT GENERATION LOGIC ---
def generate_prompts_struct(product_title, product_description):
    """
    Generates 6 distinct photography prompts based on the product details.
    Uses Structured Output (parse), so it is robust by default.
    """
    system_prompt = """# Enhanced Product Photography Agent System Prompt

## 🎯 Role & Objective:
You are a world-class AI image prompt engineer and commercial advertising visual director. Your job is to analyze a product and generate 6 distinct, high-performance prompts for AI image generation models that produce different types of commercial imagery for complete marketing campaigns.

## 📸 Image Categories & Specifications:
ALL IMAGES MUST BE 1024x1024 SQUARE TO COMPLY WITH DALL-E 2.

### 1. STUDIO_ENHANCEMENT
- **Purpose**: Professional product photography for e-commerce
- **Resolution**: 1024x1024 (Square - API Requirement)
- **Style**: Clean, minimalist, studio-lit enhancement of the original product
- **Lighting**: Soft diffused lighting, subtle shadows, professional studio setup
- **Background**: Clean white/light gradient, reflective acrylic surface
- **Composition**: Product centered, 85mm macro lens perspective, shallow depth of field
- **Focus**: Maximum detail on product features, textures, and materials

### 2-4. IN_USE (3 variations)
- **Purpose**: Lifestyle imagery showing product being used naturally
- **Resolution**: 1024x1024 (Square - API Requirement)
- **Style**: Authentic, relatable, lifestyle photography
- **Settings**: Real-world environments where product would be used
- **People**: Include hands/people using the product when appropriate
- **Lighting**: Natural lighting, golden hour, or warm indoor lighting
- **Mood**: Warm, inviting, aspirational lifestyle scenarios

### 5. BANNER_LANDSCAPE
- **Purpose**: Website headers, hero sections, Facebook/LinkedIn covers, YouTube thumbnails
- **Resolution**: 1024x1024 (Square - Will be cropped to landscape by theme)
- **Style**: Dynamic, cinematic, eye-catching with premium feel
- **Composition**: Product positioned strategically with 40% space for text overlay on left or right
- **Background**: Branded gradients, atmospheric depth, premium lighting effects
- **Elements**: Include brand colors, geometric overlays, motion lines, or abstract elements
- **Mood**: Professional, premium, attention-grabbing for marketing campaigns

### 6. BANNER_SQUARE
- **Purpose**: Instagram posts, Facebook ads, social media thumbnails, app icons
- **Resolution**: 1024x1024 (Perfect square for social media algorithms)
- **Style**: Bold, centered composition optimized for mobile viewing
- **Composition**: Product prominently featured in center with branded background
- **Background**: Vibrant gradients, brand colors, modern geometric patterns
- **Elements**: High contrast, bold shadows, modern typography-friendly design
- **Mood**: Social media optimized, engaging, shareable, brand-focused

## 💡 Prompt Writing Rules:
- Always specify camera settings (lens, aperture, lighting)
- Include material textures and finishes
- Specify background and environment details
- Add mood and style descriptors
- Include resolution hints (4K, professional, sharp)
- Make each prompt unique and distinct
- Ensure "in_use" prompts show different scenarios

## 🎨 CRITICAL COLOR REQUIREMENTS:
- **Theme**: {theme_name}
- **Primary Color**: {theme_primary_color}
- **Theme Mood**: {theme_mood}
- **Color Palette**: Generate images using colors that perfectly complement {theme_primary_color}
- **Specific Color Instructions**:
  - Studio images: Use neutral backgrounds (white/cream) with subtle theme color accents
  - Lifestyle images: Natural lighting with theme-appropriate environmental colors
  - Banner images: Bold use of theme colors with proper contrast for text overlay

## ✅ Expected Output:
Generate exactly 6 prompts with these prompt_types:
1. "studio_enhancement" - 1024x1024
2. "in_use_1" - 1024x1024
3. "in_use_2" - 1024x1024
4. "in_use_3" - 1024x1024
5. "banner_landscape" - 1024x1024
6. "banner_square" - 1024x1024
""".format(
        theme_name=THEME_NAME,
        theme_primary_color=THEME_PRIMARY_COLOR,
        theme_mood=THEME_MOOD,
        theme_description=THEME_DESCRIPTION
    )

    try:
        completion = client.beta.chat.completions.parse(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Product Title: {product_title}\nProduct Description: {product_description}\nTheme: {THEME_NAME}\nPrimary Color: {THEME_PRIMARY_COLOR}\nTheme Description: {THEME_DESCRIPTION}"},
            ],
            response_format=Prompts,
        )
        return completion.choices[0].message.parsed
    except Exception as e:
        print(f"Error generating prompt structure: {e}")
        return None

# --- IMAGE EDITING LOGIC ---
def edit_images_with_openai(image_path, prompt, size="1024x1024", output_path="edited_image.png"):
    """
    Edits an image using OpenAI's DALL-E 2 API (Inpainting/Editing).
    Returns the path to the saved image.
    """
    if not os.path.exists(image_path):
        print(f"Error: Input image not found at {image_path}")
        return None

    # DALL-E 2 Edit API strictly enforces 1024x1024.
    if size != "1024x1024":
        size = "1024x1024"

    try:
        with open(image_path, "rb") as input_file:
            result = client.images.edit(
                model="dall-e-2",
                image=input_file,
                prompt=prompt,
                size=size,
                n=1,
                response_format="b64_json"
            )

        image_base64 = result.data[0].b64_json
        image_bytes = base64.b64decode(image_base64)

        with open(output_path, "wb") as f:
            f.write(image_bytes)

        return output_path

    except Exception as e:
        print(f"Error editing image with OpenAI: {e}")
        return None

# --- TEXT HELPERS ---
def clean_gpt_response(content):
    """
    Cleans markdown code blocks and extra quotes from GPT responses.
    Ensures JSON parsing doesn't break due to ```json wrappers.
    """
    if not content:
        return ""
    
    # Remove markdown code blocks (```json ... ```)
    if "```" in content:
        pattern = r"```(?:json)?\s*(.*?)\s*```"
        match = re.search(pattern, content, re.DOTALL)
        if match:
            content = match.group(1)
        else:
            content = content.replace("```json", "").replace("```", "")

    content = content.strip()
    
    # Remove surrounding quotes if they exist
    if content.startswith('"') and content.endswith('"'):
        content = content[1:-1]
        
    return content

def prompt_gpt(prompt, temperature=0.6):
    """
    Simple text generation helper with LOGGING and CLEANING.
    """
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=temperature,
        )
        content = response.choices[0].message.content

        # --- LOGGING FOR DEBUGGING ---
        print(f"\n--- [OPENAI LOG START] ---\n{content}\n--- [OPENAI LOG END] ---\n")
        # -----------------------------

        return clean_gpt_response(content)
    except Exception as e:
        print(f"GPT error: {e}")
        return None