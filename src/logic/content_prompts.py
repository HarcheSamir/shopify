import json
import re
from src.clients.openai_client import client, prompt_gpt, clean_gpt_response

# --- BASIC TEXT GENERATORS ---

def generate_slogan_prompt(product_title, product_description, language):
    prompt = f"Create a catchy 4-7 word slogan in language {language} for a brand selling {product_title}. Product details: {product_description}. Return only the slogan."
    return prompt_gpt(prompt)

def generate_product_blurb_prompt(product_title, product_description, language):
    prompt = f"Write a short, catchy product blurb in {language} for a brand selling {product_title}. Product details: {product_description}. Keep it under 20 words, engaging, and easy to read."
    return prompt_gpt(prompt)

def generate_cta_prompt(product_title, product_description, language):
    prompt = f"Write a short, action-oriented call-to-action in {language} for a product called {product_title}. Product details: {product_description}. Keep it under 5 words, engaging, and suitable for a button."
    return prompt_gpt(prompt)

def generate_product_description_prompt(product_title, product_description, language):
    prompt = f"Write a compelling product description in {language} for a product called {product_title}. Product details: {product_description}. Make it one or two sentences, highlight key features, and keep it under 40 words."
    return prompt_gpt(prompt)

def generate_heading_prompt_product(product_title, product_description, language):
    prompt = f"""
You are a professional marketing copywriter.
Generate a short, catchy, and engaging heading in {language} for the following product:
Title: {product_title}
Description: {product_description}

The heading should be:
- No more than 7 words.
- Impactful and memorable.
- Suitable for a product page with a product video on the right.
- Written in natural {language} for maximum appeal.
    """
    return prompt_gpt(prompt.strip())

def generate_content_prompt_product(product_title, product_description, language):
    prompt = f"""
You are a professional marketing copywriter.
Generate a compelling product description in {language} for the following product:
Title: {product_title}
Description: {product_description}

The paragraph should be:
- 2 to 3 sentences long (Short sentences).
- Highlight the product's quality and immersive experience.
- Use vivid, engaging language that matches the product video on the right.
- Written in natural {language} with a persuasive tone.
    """
    return prompt_gpt(prompt.strip())

def generate_alternative_slogan_prompt(product_title, product_description, existing_slogan, language):
    prompt = f"Write a new and different 4-7 word slogan in {language} for a product called {product_title}. Product details: {product_description}. The slogan must be original and not similar to this one: '{existing_slogan}'. Return only the slogan."
    return prompt_gpt(prompt)

def generate_highlight_prompt(language, product_name, product_description):
    prompt = f"""
You are a professional copywriter. Write a single paragraph in {language} inside <p>...</p> tags.
The text should:
- Highlight the key benefits and features of "{product_name}" based on this description: "{product_description}".
- Be concise, visually appealing, and easy to scan.
- Use engaging language with simple icon suggestions like 🔋, 📱, ⚡ where appropriate.
- Do NOT add extra text outside <p>...</p>.
- Output only the final <p>...</p> block, nothing else.
"""
    return prompt_gpt(prompt)

def generate_why_choose_prompt(language, brand_name):
    prompt = f"""
You are a professional copywriter. Write a single paragraph in {language} inside <p>...</p> tags.
The text should:
- Explain briefly and persuasively why someone should choose "{brand_name}".
- Be concise, engaging, and visually appealing.
- Use simple icon suggestions like ⭐, 🚀, 💡 where appropriate.
- Output only the final <p>...</p> block, nothing else.
- Length or Total words must be under 25 word
"""
    return prompt_gpt(prompt)

# --- TRANSLATION UTILS ---

def translate_text(text, target_language):
    """Simple translation function - returns only translated text"""
    prompt = f"Translate to {target_language}. Return only the translation, no explanations , IF THE THE Input text has HTML tags like <br> or <p> or any keep them and translate the text and return if no html return just the text : {text}"
    return prompt_gpt(prompt, temperature=0.3)

def translate_benefits(content, target_language):
    """Translate benefits content to target language"""
    prompt = r"Translate this HTML content to {target_language}. Return only the translated text with the same HTML structure with the <pr> and <br\/> tags. Do not add any explanations or additional text:\n\n{content}".format(target_language=target_language, content=content)
    return prompt_gpt(prompt, temperature=0.3)

# --- COMPLEX JSON GENERATORS ---

def generate_customer_qna(product_name, product_description, language):
    prompt = f"""
You are a professional copywriter. Generate exactly 4 customer Q&A pairs for the product:
Name: "{product_name}"
Description: "{product_description}"

Requirements:
- Questions must be short, natural, and in {language}.
- Answers must be concise, helpful, and wrapped in <p>...</p> tags.
- Return the result as valid JSON array with 4 objects, each having:
  "Question": "The question",
  "Answer": "<p>The answer</p>"
- Do NOT add extra text or commentary. Only valid JSON.
    """
    
    try:
        raw_text = prompt_gpt(prompt)
        # prompt_gpt already calls clean_gpt_response, so we just load it
        return json.loads(raw_text)
    except Exception as e:
        print(f"Error generating Q&A: {e}")
        return []

def get_valid_reviews(product_title, product_description, language, max_retries=3):
    """
    Asks GPT for a JSON array of reviews directly.
    NO FALLBACKS: Raises error if fails.
    """
    prompt = f"""
    Generate 6 unique product reviews in {language} for the product '{product_title}'.
    Product details: {product_description}.
    
    Return a STRICT JSON ARRAY of objects. Each object must have these keys:
    - "stars": string (e.g. "★★★★★" or "★★★★☆")
    - "review_headline": string (Short title)
    - "review_body": string (2-3 sentences)
    - "author_info": string (Name, City)

    Example format:
    [
      {{
        "stars": "★★★★★",
        "review_headline": "Super!",
        "review_body": "I loved it.",
        "author_info": "Paul, London"
      }}
    ]
    Do not add any markdown formatting or text outside the JSON.
    """

    for attempt in range(max_retries):
        result = prompt_gpt(prompt)
        try:
            # prompt_gpt cleans the markdown now
            data = json.loads(result)
            
            if isinstance(data, list) and len(data) > 0:
                # Basic validation
                if "review_headline" in data[0]:
                    return data
        except json.JSONDecodeError:
            print(f"   ⚠️ Review generation JSON error (Attempt {attempt+1})")
            continue
            
    # If we get here, it failed. Raise error to stop script.
    raise Exception("❌ FAILED to generate valid JSON Reviews after 3 attempts. Stopping to prevent bad data.")

def get_pros_json(product_title, product_description, language):
    """
    Asks GPT for a simple JSON list of 5 short benefits.
    NO FALLBACKS: Raises error if fails.
    """
    prompt = f"""
    Generate exactly 5 short key benefits (pros) for: {product_title} in {language}.
    Return ONLY a JSON Array of strings.
    Example: ["Fast Shipping", "Eco-friendly", "Durable", "Soft", "Cheap"]
    """
    
    for attempt in range(3):
        response = prompt_gpt(prompt)
        try:
            data = json.loads(response)
            
            if isinstance(data, list) and len(data) >= 5:
                return {
                    "pros_store_1": data[0],
                    "pros_store_2": data[1],
                    "pros_store_3": data[2],
                    "pros_store_4": data[3],
                    "pros_store_5": data[4]
                }
        except Exception:
            pass
            
    # If we get here, it failed. Raise error to stop script.
    raise Exception("❌ FAILED to generate valid JSON Pros after 3 attempts. Stopping to prevent bad data.")