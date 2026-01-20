import json
import re
from src.clients.openai_client import client

def prompt_gpt(prompt, temperature=0.6):
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=temperature,
        )
        content = response.choices[0].message.content.strip()
        if content.startswith('"') and content.endswith('"'):
            content = content[1:-1]
        return content
    except Exception as e:
        print(f"GPT error: {e}")
        return None

# --- RESTORED MAIN CONTENT FUNCTION ---
def get_new_theme_content(product_title, product_description, language):
    """
    Retrieves the main JSON structure for the theme (Hero, Features, etc.).
    """
    # NOTE: This uses the massive prompt logic. 
    # We will fully implement the prompt text in Phase 2/3 when we need the DeepSeek structure.
    # For now, it returns an empty dict to prevent ImportErrors.
    return {}

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
    # Fixed escape sequence by using raw string
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
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
        )
        return response.choices[0].message.content.strip().replace('"',"")
    except Exception as e:
        print(f"Translation error: {e}")
        return text

def translate_benefits(content, target_language):
    """Translate benefits content to target language"""
    # Fixed escape sequence with raw string r""
    prompt = r"Translate this HTML content to {target_language}. Return only the translated text with the same HTML structure with the <pr> and <br\/> tags. Do not add any explanations or additional text:\n\n{content}".format(target_language=target_language, content=content)
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
        )
        return response.choices[0].message.content.strip().replace('"',"")
    except Exception as e:
        print(f"Error translating benefits: {e}")
        return content

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
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.6,
        )
        raw_text = response.choices[0].message.content.strip()

        try:
            qna_data = json.loads(raw_text)
        except json.JSONDecodeError:
            start = raw_text.find("[")
            end = raw_text.rfind("]") + 1
            if start != -1 and end != -1:
                raw_text = raw_text[start:end]
                try:
                    qna_data = json.loads(raw_text)
                except:
                    return []
            else:
                return []

        if not isinstance(qna_data, list) or len(qna_data) != 4:
            return []

        return qna_data

    except Exception as e:
        print(f"Error generating Q&A: {e}")
        return []

def get_valid_reviews(product_title, product_description, language, max_retries=5):
    prompt = f"""
Generate 4 unique product reviews in {language} for the product '{product_title}'.
Product details: {product_description}.
Each review must follow exactly this HTML structure:

<h2>Review Title</h2><p></p><p>Review content here</p><h6><strong>Reviewer Name, City</strong></h6>

Return the reviews as a single JSON object with keys review_1, review_2, review_3, and review_4.
The value for each key must be the full HTML string for the review.
Do not add explanations or extra text.
"""

    for attempt in range(max_retries):
        result = prompt_gpt(prompt)
        try:
            data = json.loads(result)
            if (isinstance(data, dict) and len(data) == 4):
                return data
        except json.JSONDecodeError:
            try:
                review_pattern = r'review_(\d+):\s*(<h2>.*?</h6>)'
                matches = re.findall(review_pattern, result, re.DOTALL)
                if len(matches) == 4:
                    data = {}
                    for review_num, review_content in matches:
                        data[f"review_{review_num}"] = review_content.strip()
                    return data
            except Exception:
                pass
    return {}

def fix_json_format(response: str) -> str:
    match = re.search(r'\{.*\}', response, re.DOTALL)
    if match:
        response = match.group(0)
    response = re.sub(r'pros_store_(\d+):\s*([^,\n}]+)', r'"pros_store_\1": "\2"', response)
    response = response.replace('.,', ',')
    response = response.replace('.}', '}')
    return response

def get_pros_json(product_title, product_description, language):
    prompt = f"""
You are given the following product information:
Title: {product_title}
Description: {product_description}

Generate exactly 5 pros of this product in {language}.
Output MUST be valid JSON only, no explanations, no extra text.
Keys must be: pros_store_1, pros_store_2, pros_store_3, pros_store_4, pros_store_5.
"""
    current_prompt = prompt
    for attempt in range(3):
        response = prompt_gpt(current_prompt)
        try:
            data = json.loads(response)
            if all(f"pros_store_{i}" in data for i in range(1, 6)):
                return data
        except json.JSONDecodeError:
            try:
                fixed = fix_json_format(response)
                data = json.loads(fixed)
                if all(f"pros_store_{i}" in data for i in range(1, 6)):
                    return data
            except:
                pass
        if attempt == 0: current_prompt += '\nIMPORTANT: Return ONLY valid JSON with quoted keys.'
        elif attempt == 1: current_prompt += '\nEnsure all property names are in double quotes.'
    return {}