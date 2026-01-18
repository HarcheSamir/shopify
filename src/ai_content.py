import json
from openai import OpenAI
from pydantic import BaseModel, Field
from typing import List, Dict, Any

class PromptItem(BaseModel):
    prompt_type: str
    prompt: str
    image_size: str
    purpose: str

class Prompts(BaseModel):
    prompts: List[PromptItem]

class AIContentGenerator:
    def __init__(self, api_key: str):
        if not api_key:
            raise ValueError("OpenAI API Key is missing")
        self.client = OpenAI(api_key=api_key)

    def _clean_json_response(self, response_text: str) -> str:
        """Extracts JSON from markdown code blocks if present."""
        if "```json" in response_text:
            start = response_text.find("```json") + 7
            end = response_text.find("```", start)
            if end != -1:
                return response_text[start:end].strip()
        return response_text.replace("```", "").strip()

    def generate_image_prompts(self, product_title: str, product_description: str, theme_name: str, primary_color: str) -> Prompts:
        """Generates 6 distinct image prompts for the product."""
        system_prompt = f"""
        You are an expert AI image prompt engineer.
        Product: {product_title}
        Description: {product_description}
        Theme Color: {primary_color}
        
        Generate exactly 6 prompts:
        1. "studio_enhancement" (1024x1536) - Product on clean background
        2. "in_use_1" (1024x1024) - Lifestyle usage
        3. "in_use_2" (1024x1024) - Lifestyle usage
        4. "in_use_3" (1024x1024) - Lifestyle usage
        5. "banner_landscape" (1536x1024) - Hero banner
        6. "banner_square" (1024x1024) - Social media style
        
        Ensure color harmony with {primary_color}.
        """
        
        try:
            completion = self.client.beta.chat.completions.parse(
                model="gpt-4o-2024-08-06", # Using reliable model for structured output
                messages=[{"role": "system", "content": system_prompt}],
                response_format=Prompts,
            )
            return completion.choices[0].message.parsed
        except Exception as e:
            # Fallback if parse fails or model unavailable
            print(f"Warning: Prompt generation failed: {e}")
            return Prompts(prompts=[])

    def generate_color_schema(self, primary_color: str, original_schema_json: str) -> str:
        """
        Generates a new color schema JSON based on the primary color.
        Enforces strict black/white text contrast rules.
        """
        prompt = f"""
        You are an expert UI designer. Generate a new Shopify color_schemes JSON.
        
        INPUT SCHEMA STRUCTURE (Keep keys exactly like this):
        {original_schema_json}
        
        PRIMARY COLOR: {primary_color}
        
        RULES:
        1. Replace the accent colors with variations of {primary_color}.
        2. CRITICAL: All "text" fields MUST be either #000000 or #ffffff based on contrast.
        3. Never use the primary color for body text.
        4. Return ONLY valid JSON.
        """
        
        response = self.client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
        )
        
        return self._clean_json_response(response.choices[0].message.content)

    def translate_text(self, text: str, target_language: str) -> str:
        """Simple translation helper."""
        if target_language.lower() == "english":
            return text
            
        response = self.client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{
                "role": "user", 
                "content": f"Translate to {target_language}. Return ONLY the translation, keep HTML tags: {text}"
            }],
            temperature=0.3
        )
        return response.choices[0].message.content.strip().replace('"', '')

    def generate_marketing_copy(self, brand_name: str, product_title: str, product_desc: str, language: str) -> Dict[str, Any]:
        """Generates the full suite of marketing content matches the original notebook."""
        
        prompt = f"""
        PS: GENERATE THE CONTENT STRICTLY IN {language}.
        
        Generate high-converting marketing content for an e-commerce product page with a NEW THEME.
        Return STRICTLY a JSON object.
        
        Product: {product_title}
        Description: {product_desc}
        Brand: {brand_name}

        OUTPUT JSON STRUCTURE (Fill every field):
        {{
            "NEW_THEME_BRAND_NAME": "{brand_name}",
            "NEW_THEME_MAIN_TITLE_HERO_SLOGAN": "Hero slogan (6-10 words)",
            "NEW_THEME_SUBTITLE_HERO": "Hero subtitle (10-15 words)",
            "NEW_THEME_SUBTITLE_BUTTON_TEXT": "CTA Button text (e.g. Shop Now)",
            "NEW_THEME_MAIN_TITLE_FEATURE": "Feature section title (5-8 words)",
            "NEW_THEME_TEXT_FEATURE": "Feature description (20-30 words)",
            "NEW_THEME_PRODUCT_BLURB_CONTENT": "Short product blurb (under 20 words)",
            "NEW_THEME_REVIEWS_SECTION_HEADLINE": "Reviews headline",
            "NEW_THEME_CUSTOMERS_REVIEW_TEXT_DESCRIPTION": "Reviews subtitle",
            "NEW_THEME_FAQ_LIST": [
                {{"question": "Q1...", "answer": "A1..."}},
                {{"question": "Q2...", "answer": "A2..."}},
                {{"question": "Q3...", "answer": "A3..."}},
                {{"question": "Q4...", "answer": "A4..."}}
            ],
            "NEW_THEME_MULTICOLUMN_REVIEWS_LIST": [
                {{"stars": "★★★★★", "review_headline": "Title 1", "review_body": "Body 1", "author_info": "Name 1"}},
                {{"stars": "★★★★★", "review_headline": "Title 2", "review_body": "Body 2", "author_info": "Name 2"}},
                {{"stars": "★★★★★", "review_headline": "Title 3", "review_body": "Body 3", "author_info": "Name 3"}}
            ]
        }}
        """
        
        try:
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"},
                temperature=0.7
            )
            return json.loads(response.choices[0].message.content)
        except Exception as e:
            print(f"AI Generation Error: {e}")
            # Return minimal safe structure to prevent crashes
            return {
                "NEW_THEME_BRAND_NAME": brand_name,
                "NEW_THEME_MAIN_TITLE_HERO_SLOGAN": f"Discover {product_title}",
                "NEW_THEME_SUBTITLE_BUTTON_TEXT": "Shop Now"
            }