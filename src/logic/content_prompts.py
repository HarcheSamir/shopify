import json
from src.clients.openai_client import client

def get_new_theme_content(product_title, product_description, language):
    prompt = f"""
    PS: GENERATE THE CONTENT STRICTLY IN {language}.
    ... [Paste the massive prompt from the 'get_new_theme_content' function in the notebook] ...
    """
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}],
        temperature=1.0,
    )
    content = response.choices[0].message.content
    # Extract JSON logic
    try:
        json_str = content[content.find('{'):content.rfind('}')+1]
        return json.loads(json_str)
    except:
        return None

def generate_about_us_content(brand, title, language):
    # Implementation of generate_about_us_content
    pass