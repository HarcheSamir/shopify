import os
import sys
import json
import uuid
import shutil
import argparse
import re
from dotenv import load_dotenv

load_dotenv()

sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from src.ai_content import AIContentGenerator
from src.media_processor import MediaProcessor
from src.shopify_client import ShopifyClient
from src.theme_manager import ThemeManager

def print_progress(step, message):
    print(json.dumps({"status": "progress", "step": step, "message": message}), flush=True)

# --- MOCK DATA FOR TEST MODE ---
MOCK_CONTENT = {
    "NEW_THEME_BRAND_NAME": "Lumin Test",
    "NEW_THEME_MAIN_TITLE_HERO_SLOGAN": "Radiance Redefined",
    "NEW_THEME_SUBTITLE_HERO": "Experience the ultimate hydration with our premium Rose Face Cream.",
    "NEW_THEME_SUBTITLE_BUTTON_TEXT": "Shop The Sale",
    "NEW_THEME_MAIN_TITLE_FEATURE": "Why Lumin?",
    "NEW_THEME_TEXT_FEATURE": "Our formula uses organic rose extracts to soothe and revitalize dry skin.",
    "NEW_THEME_PRODUCT_BLURB_CONTENT": "Hydration meets Luxury.",
    "NEW_THEME_REVIEWS_SECTION_HEADLINE": "Loved by Thousands",
    "NEW_THEME_CUSTOMERS_REVIEW_TEXT_DESCRIPTION": "See what our community has to say.",
    "NEW_THEME_PRODUCT_PHILOSOPHY": "We believe in clean, sustainable beauty that delivers real results.",
    "NEW_THEME_SHOP_COLLECTION_TRANSLATION": "View Collection",
    "NEW_THEME_FAQ_LIST": [
        {"question": "Is this vegan?", "answer": "Yes, 100% vegan and cruelty-free."},
        {"question": "How long does shipping take?", "answer": "Usually 3-5 business days."},
        {"question": "Can I return it?", "answer": "We offer a 30-day money-back guarantee."},
        {"question": "Is it good for sensitive skin?", "answer": "Yes, it is dermatologist tested."}
    ],
    "NEW_THEME_MULTICOLUMN_REVIEWS_LIST": [
        {"stars": "★★★★★", "review_headline": "Amazing!", "review_body": "Best cream I have ever used.", "author_info": "Sarah J."},
        {"stars": "★★★★★", "review_headline": "So Soft", "review_body": "My skin feels incredible.", "author_info": "Mike T."},
        {"stars": "★★★★☆", "review_headline": "Great Scent", "review_body": "Smells like fresh roses.", "author_info": "Emily R."}
    ],
    "NEW_THEME_COMPARISON_LIST": [
        {"caption": "Before", "testimonial_text": "Dry and dull skin.", "author_info": "Alice"},
        {"caption": "After", "testimonial_text": "Glowing and radiant.", "author_info": "Alice"}
    ]
}

MOCK_IMAGES = {
    "NEW_THEME_HERO_BANNER": "https://images.unsplash.com/photo-1616683693504-3ea7e9ad6fec?auto=format&fit=crop&w=1600&q=80",
    "NEW_THEME_PRODUCT_IMAGE_LUMIN_SECTION": "https://images.unsplash.com/photo-1620916566398-39f1143ab7be?auto=format&fit=crop&w=800&q=80",
    "NEW_THEME_COLLECTION_IMAGE": "https://images.unsplash.com/photo-1556228578-8c89e6adf883?auto=format&fit=crop&w=800&q=80",
    "NEW_THEME_PRODUCT_SHOWCASE_IMAGE_1": "https://images.unsplash.com/photo-1571781535607-432029050f65?auto=format&fit=crop&w=800&q=80",
    "NEW_THEME_PRODUCT_SHOWCASE_IMAGE_2": "https://images.unsplash.com/photo-1599305090598-fe179d501227?auto=format&fit=crop&w=800&q=80",
    "NEW_THEME_IMAGE_LUMIN_GRID_1": "https://images.unsplash.com/photo-1608248597279-f99d160bfbc8?auto=format&fit=crop&w=800&q=80"
}

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--brand_name", required=True)
    parser.add_argument("--product_title", required=True)
    parser.add_argument("--product_description", required=True)
    parser.add_argument("--shopify_url", required=True)
    parser.add_argument("--access_token", required=True)
    parser.add_argument("--logo_path", required=True)
    # Test flag
    parser.add_argument("--test", action="store_true", help="Run in test mode (No AI costs)")
    args = parser.parse_args()

    job_id = str(uuid.uuid4())[:8]
    print_progress("setup", f"Job ID: {job_id}")

    # Load Keys
    OPENAI_KEY = os.getenv("OPENAI_API_KEY")
    IMGBB_KEY = os.getenv("IMGBB_API_KEY")
    RUNWAY_KEY = os.getenv("RUNWAY_API_KEY")

    # Paths
    BASE_THEME_PATH = "./assets/base-theme"
    TEMP_DIR = "./temp"
    if os.path.exists(TEMP_DIR): shutil.rmtree(TEMP_DIR)
    os.makedirs(TEMP_DIR, exist_ok=True)

    # Initialize
    # Only init AI if NOT in test mode to avoid init errors if keys are missing
    ai = AIContentGenerator(OPENAI_KEY) if not args.test else None
    media = MediaProcessor(OPENAI_KEY, RUNWAY_KEY, IMGBB_KEY)
    client = ShopifyClient(args.shopify_url, args.access_token)
    theme_manager = ThemeManager(BASE_THEME_PATH, TEMP_DIR)

    ai_content = {}
    images_map = {}
    product_image_urls = []
    primary_color = "#EFB7C6"

    # --- 1. CONTENT GENERATION ---
    if args.test:
        print_progress("ai_text", "🧪 TEST MODE: Using Mock Text Data...")
        ai_content = MOCK_CONTENT.copy()
        ai_content["NEW_THEME_BRAND_NAME"] = args.brand_name # Use arg override
    else:
        print_progress("ai_text", "Generating marketing copy (OpenAI)...")
        if not OPENAI_KEY: raise Exception("Missing OpenAI Key")
        ai_content = ai.generate_marketing_copy(args.brand_name, args.product_title, args.product_description, "English")
        if not ai_content: raise Exception("AI Text Generation Failed")

    # Colors (Applied in both modes)
    print_progress("ai_color", f"Applying Theme Color: {primary_color}")
    ai_content.update({
        "NEW_THEME_PRIMARY_COLOR": primary_color,
        "NEW_THEME_SECONDARY_COLOR": "#F5F5F5",
        "NEW_THEME_COLOR_SCHEME_1_BACKGROUND": "#ffffff", "NEW_THEME_COLOR_SCHEME_1_TEXT": "#000000",
        "NEW_THEME_COLOR_SCHEME_1_BUTTON": primary_color, "NEW_THEME_COLOR_SCHEME_1_BUTTON_LABEL": "#ffffff",
        "NEW_THEME_COLOR_SCHEME_1_SECONDARY_BUTTON_LABEL": primary_color,
        "NEW_THEME_COLOR_SCHEME_2_BACKGROUND": primary_color, "NEW_THEME_COLOR_SCHEME_2_TEXT": "#ffffff",
        "NEW_THEME_COLOR_SCHEME_2_BUTTON": "#ffffff", "NEW_THEME_COLOR_SCHEME_2_BUTTON_LABEL": primary_color,
        "NEW_THEME_COLOR_SCHEME_3_BACKGROUND": "#2e2a39", "NEW_THEME_COLOR_SCHEME_3_TEXT": "#ffffff",
        "NEW_THEME_COLOR_SCHEME_3_BUTTON": primary_color,
    })

    # --- 2. IMAGE GENERATION ---
    if args.test:
        print_progress("ai_images", "🧪 TEST MODE: Using Mock Images...")
        # Populate product images
        product_image_urls = [
            MOCK_IMAGES["NEW_THEME_PRODUCT_IMAGE_LUMIN_SECTION"],
            MOCK_IMAGES["NEW_THEME_PRODUCT_SHOWCASE_IMAGE_1"],
            MOCK_IMAGES["NEW_THEME_COLLECTION_IMAGE"]
        ]
        
        # Upload mocks to Shopify to get internal handles
        for placeholder, url in MOCK_IMAGES.items():
            print(f"   -> Uploading mock for {placeholder}...")
            shopify_url = client.upload_image_from_url(url, f"mock_{placeholder[:5]}.jpg")
            if shopify_url:
                images_map[placeholder] = shopify_url
    else:
        print_progress("ai_images", "Generating images (OpenAI DALL-E)...")
        prompts = ai.generate_image_prompts(args.product_title, args.product_description, "Beauty", primary_color)
        
        PROMPT_MAPPING = {
            "studio_enhancement": "NEW_THEME_PRODUCT_IMAGE_LUMIN_SECTION",
            "banner_landscape": "NEW_THEME_HERO_BANNER",
            "banner_square": "NEW_THEME_COLLECTION_IMAGE",
            "in_use_1": "NEW_THEME_PRODUCT_SHOWCASE_IMAGE_1",
            "in_use_2": "NEW_THEME_PRODUCT_SHOWCASE_IMAGE_2",
            "in_use_3": "NEW_THEME_IMAGE_LUMIN_GRID_1"
        }

        if prompts and prompts.prompts:
            for i, p_item in enumerate(prompts.prompts):
                print(f"   -> Generating: {p_item.prompt_type}...")
                output_path = os.path.join(TEMP_DIR, f"img_{i}.png")
                edited_path = media.edit_image(args.logo_path, p_item.prompt, output_path)
                
                if edited_path:
                    imgbb_url = media.upload_to_imgbb(edited_path)
                    if imgbb_url:
                        product_image_urls.append(imgbb_url)
                        placeholder = PROMPT_MAPPING.get(p_item.prompt_type)
                        if placeholder:
                            shopify_url = client.upload_image_from_url(imgbb_url, f"img_{i}.jpg")
                            if shopify_url: images_map[placeholder] = shopify_url
        else:
            raise Exception("AI Prompt Gen Failed")

    # --- 3. CREATE PRODUCT ---
    print_progress("shopify_product", "Creating product...")
    product = client.create_product(
        title=args.product_title,
        html_body=f"<p>{args.product_description}</p>",
        image_urls=product_image_urls,
        brand=args.brand_name
    )
    if not product: raise Exception("Product creation failed")
    product_handle = product["handle"]
    product_id = product["id"]
    print(f"DEBUG: Created Product Handle: {product_handle}")

    # --- 4. PAGES & MENU ---
    print_progress("shopify_product", "Creating Pages...")
    about_html = f"<h1>About {args.brand_name}</h1><p>Welcome to {args.brand_name}.</p>"
    page_id = client.create_page(f"About {args.brand_name}", about_html)
    if page_id: client.add_page_to_menu(str(page_id), f"About {args.brand_name}")

    # --- 5. THEME INJECTION ---
    print_progress("inject", "Injecting content into theme...")
    workspace_path = theme_manager.setup_workspace(job_id)
    theme_manager.process_notebook_logic(workspace_path, ai_content, images_map, primary_color, args.brand_name, product_handle)

    # --- 6. ZIP & UPLOAD ---
    print_progress("zip", "Zipping theme...")
    zip_path = theme_manager.zip_theme(workspace_path)
    
    print_progress("hosting", "Uploading theme to Shopify Storage...")
    zip_shopify_url = client.upload_local_file(zip_path)
    if not zip_shopify_url: raise Exception("Failed to upload theme ZIP")

    print_progress("shopify_upload", "Installing theme...")
    theme_id = client.upload_theme(zip_shopify_url, f"Auto-{job_id}")
    if not theme_id: raise Exception("Theme installation failed")

    # Publish
    client.publish_theme(theme_id)

    print(json.dumps({
        "status": "success", 
        "store_url": f"https://{args.shopify_url}", 
        "job_id": job_id,
        "theme_id": theme_id,
        "product_id": product_id,
        "product_handle": product_handle
    }))

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(json.dumps({"status": "error", "message": str(e)}))
        sys.exit(1)