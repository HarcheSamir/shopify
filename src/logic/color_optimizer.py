import json
import os
import re
import base64
import traceback
from typing import Dict, Any, List
from src.clients.openai_client import client

# ==============================================================================
# 1. UTILITIES & MATH
# ==============================================================================

def encode_image_to_base64(image_path: str) -> str:
    """
    Reads an image file and converts it to a Base64 string for API usage.
    """
    try:
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode('utf-8')
    except Exception:
        return ""

def hex_to_rgb(hex_color: str) -> tuple:
    """
    Converts hex string (e.g. #ffffff) to RGB tuple (255, 255, 255).
    """
    hex_color = hex_color.lstrip('#')
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))

def calculate_luminance(rgb: tuple) -> float:
    """
    Calculates the relative luminance of a color to determine if it is light or dark.
    Uses standard W3C formula.
    """
    def linearize(channel):
        channel = channel / 255.0
        if channel <= 0.03928:
            return channel / 12.92
        else:
            return pow((channel + 0.055) / 1.055, 2.4)

    r, g, b = rgb
    return 0.2126 * linearize(r) + 0.7152 * linearize(g) + 0.0722 * linearize(b)

def is_dark_color(hex_color: str) -> bool:
    """
    Returns True if the color is considered dark (luminance < 0.18).
    """
    try:
        rgb = hex_to_rgb(hex_color)
        luminance = calculate_luminance(rgb)
        return luminance < 0.18
    except:
        # Fallback to assuming it's light if invalid hex
        return False

def enforce_text_color_rules(schema_json: dict, theme_color: str) -> dict:
    """
    Post-process the schema to enforce strict text color rules (Accessibility).
    - Dark Background -> White Text
    - Light Background -> Black Text
    - Button Labels -> Contrast against Button Background
    """
    if "color_schemes" not in schema_json:
        return schema_json

    for scheme_name, scheme_data in schema_json["color_schemes"].items():
        settings = scheme_data.get("settings", {})

        if "text" in settings and "background" in settings:
            background_color = settings["background"]

            # 1. Enforce Black/White Text based on background
            if is_dark_color(background_color):
                settings["text"] = "#ffffff"
            else:
                settings["text"] = "#000000"

            # 2. Button Labels
            if "button" in settings:
                btn_bg = settings["button"]
                if "button_label" in settings:
                    settings["button_label"] = "#ffffff" if is_dark_color(btn_bg) else "#000000"

            # 3. Secondary Button Labels (Outline buttons usually)
            if "secondary_button_label" in settings:
                # Usually matches text color
                settings["secondary_button_label"] = settings["text"]

    return schema_json

def clean_json_response(response_text: str) -> str:
    """
    Strips Markdown code blocks if present in GPT response.
    """
    if "```json" in response_text:
        start_marker = "```json"
        end_marker = "```"
        start_idx = response_text.find(start_marker)
        if start_idx != -1:
            start_idx += len(start_marker)
            end_idx = response_text.find(end_marker, start_idx)
            if end_idx != -1:
                response_text = response_text[start_idx:end_idx]

    response_text = response_text.replace("```", "").strip()
    return response_text

# ==============================================================================
# 2. GENERATION LOGIC
# ==============================================================================

def generate_new_color_schemas(
    original_color_schema: str,
    theme_primary_color: str,
    theme_description: str,
    index_json_path: str,
    images_folder_path: str
) -> str:
    """
    Generates a brand new color schema JSON using GPT-4o.
    Uses the EXACT prompt from the original notebook.
    """

    # 1. Read Inputs
    try:
        with open(index_json_path, 'r', encoding='utf-8') as f:
            index_json_content = f.read()
    except Exception:
        index_json_content = "{}"

    # 2. Prepare Images context
    # NOTEBOOK FAITHFULNESS: Changed [:3] back to [:6]
    image_contents = []
    if os.path.exists(images_folder_path):
        valid_files = [f for f in os.listdir(images_folder_path) if f.lower().endswith(('.png', '.jpg'))]
        for img_file in valid_files[:6]:
            b64 = encode_image_to_base64(os.path.join(images_folder_path, img_file))
            if b64:
                image_contents.append({
                    "type": "image_url",
                    "image_url": {"url": f"data:image/png;base64,{b64}"}
                })

    # 3. Prompt Construction (EXACT COPY FROM NOTEBOOK)
    messages = [
        {
            "role": "system",
            "content": "You are a precise JSON generator and expert color designer for e-commerce themes. You MUST follow strict text color rules. Always return raw JSON without markdown formatting or explanations."
        },
        {
            "role": "user",
            "content": [
                {
                    "type": "text",
                    "text": f"""
You are an expert color designer for e-commerce themes. Generate a new color schema JSON based on the original schema, adapted to a new theme.

ORIGINAL COLOR SCHEMAS (use this EXACT format for output, including all keys and structure):
{original_color_schema}

NEW PRIMARY COLOR: {theme_primary_color}
THEME DESCRIPTION: {theme_description}

HOME PAGE STRUCTURE (index.json):
{index_json_content}

*** CRITICAL TEXT COLOR RULES - ABSOLUTE REQUIREMENT - ZERO TOLERANCE ***

FOR ALL SCHEMES WITHOUT EXCEPTION:
- ALL "text" fields MUST be ONLY #000000, #111111, #222222 (dark) OR #ffffff, #fafafa, #f8f8f8 (light)
- NEVER EVER use theme colors ({theme_primary_color}) in ANY text field
- NO exceptions, NO special schemes, NO accent text colors
- Body text, descriptions, paragraph text = BLACK or WHITE ONLY
- Choose based on background: light background = dark text (#000000), dark background = light text (#ffffff)

ABSOLUTELY FORBIDDEN:
- Do NOT use {theme_primary_color} or any variation of it in text fields
- Do NOT make any scheme "special" with colored text
- Do NOT use theme color for accent text or highlight text
- The theme color should ONLY be used for backgrounds, buttons, shadows, gradients

BUTTON LABELS:
- "button_label": Usually #ffffff (white) for contrast on colored buttons
- "secondary_button_label": Usually #000000 (black) for secondary/outline buttons

OTHER COLORS (backgrounds, buttons, gradients):
- These CAN and SHOULD use the theme color and harmonious palette
- Create vibrant, cohesive palette matching theme description and images
- Use CSS linear-gradient format for gradients

STRUCTURE REQUIREMENTS:
- Keep ALL existing scheme names exactly the same
- Do NOT add or remove schemes
- Update ALL hex colors and gradients to fit the new theme
- Ensure accessibility and contrast

Return ONLY the JSON object - no markdown, no explanations, just raw JSON.
"""
                }
            ] + image_contents
        }
    ]

    try:
        print("   🧠 Sending Color Schema Request to OpenAI...")
        # Call GPT-4o
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=messages,
            temperature=0.1,
            max_tokens=15000, # Keep high token limit for massive JSON
            response_format={"type": "json_object"}
        )

        raw_text = response.choices[0].message.content
        
        # --- DEBUG LOGGING ---
        print(f"\n--- [OPENAI COLOR LOG START] ---\n{raw_text}\n--- [OPENAI COLOR LOG END] ---\n")
        # ---------------------

        if not raw_text:
            raise ValueError("OpenAI returned empty content")

        clean_text = clean_json_response(raw_text)

        # Parse and Enforce Rules in Python to be safe
        schema_json = json.loads(clean_text)
        schema_json = enforce_text_color_rules(schema_json, theme_primary_color)

        return json.dumps(schema_json, indent=2)

    except Exception as e:
        print(f"   ❌ Color Generation Error: {str(e)}")
        traceback.print_exc()
        # Fallback: Return original but with simple replacement
        return original_color_schema.replace("#7069bc", theme_primary_color)

def fix_color_schema(json_string):
    """
    Sanitizes JSON string if formatting is slightly off.
    """
    try:
        # Try round trip to normalize formatting
        return json.dumps(json.loads(json_string), indent=2)
    except:
        return json_string

# ==============================================================================
# 3. OPTIMIZER CLASS (Contextual Analysis)
# ==============================================================================

class ShopifyColorSchemeOptimizer:
    def __init__(self):
        pass

    def extract_color_schemes(self, color_schemas: dict) -> dict:
        """
        Parses available schemes to know which are dark/light.
        """
        schemes = {}
        for name, data in color_schemas.get("color_schemes", {}).items():
            s = data.get("settings", {})
            schemes[name] = {
                "background": s.get("background", "#ffffff"),
                "text": s.get("text", "#000000"),
                "button": s.get("button", "#000000")
            }
        return schemes

    def optimize_theme_colors(self, color_schemas: str, json_file_path: str, images_folder: str):
        """
        Modifies index.json or product.json IN PLACE to use the best color scheme
        for each section.
        """
        print(f"🎨 Optimizing colors for {os.path.basename(json_file_path)}...")

        try:
            # Load the current template
            with open(json_file_path, 'r', encoding='utf-8') as f:
                template_data = json.load(f)

            # We apply a logical heuristic optimization.
            # We assign different schemes to break up the page visually.

            if "sections" in template_data:
                keys = list(template_data["sections"].keys())

                for i, section_id in enumerate(keys):
                    section = template_data["sections"][section_id]
                    sType = section.get("type", "")

                    new_scheme = None

                    # Logic: Alternating or Specific based on type
                    if sType == "image-banner":
                        # Hero Banner -> Usually transparent or Scheme 1
                        new_scheme = "background-1"
                    elif sType == "rich-text":
                        # Text block -> Use Accent scheme for emphasis
                        new_scheme = "accent-1"
                    elif sType == "multicolumn":
                        # Columns -> Standard background
                        new_scheme = "background-1"
                    elif sType == "image-with-text":
                        # Split -> Inverse for style
                        new_scheme = "inverse"
                    elif sType == "featured-collection":
                        new_scheme = "background-1"

                    # Apply if valid
                    if new_scheme:
                        if "settings" in section:
                            # Only update if color_scheme key exists
                            if "color_scheme" in section["settings"]:
                                section["settings"]["color_scheme"] = new_scheme
                            # Some themes use color_scheme_1
                            elif "color_scheme_1" in section["settings"]:
                                section["settings"]["color_scheme_1"] = new_scheme

            # Save back the optimized file
            with open(json_file_path, 'w', encoding='utf-8') as f:
                json.dump(template_data, f, indent=2)

        except Exception as e:
            print(f"❌ Failed to load JSON for optimization: {e}")