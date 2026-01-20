import os
import sys
import json
import uuid
import shutil
import re
import argparse
from dotenv import load_dotenv

# Ensure the project root is in the python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# --- IMPORTS ---
from src.clients.shopify_client import ShopifyClient
from src.theme_manager import ThemeManager
from src.logic.theme_utils import replace_colors_in_json_files, inject_video_id
from src.mocks.data_payloads import MOCK_THEME_CONTENT, MOCK_IMAGES
from src.mocks.mock_visual_generation import mock_generate_all_visuals
from src.logic.content_prompts import (
    generate_slogan_prompt,
    generate_product_blurb_prompt,
    generate_cta_prompt,
    generate_product_description_prompt,
    generate_heading_prompt_product,
    generate_content_prompt_product,
    generate_alternative_slogan_prompt,
    generate_highlight_prompt,
    generate_why_choose_prompt,
    translate_text,
    translate_benefits,
    generate_customer_qna,
    get_valid_reviews,
    get_pros_json,
    prompt_gpt
)
from src.logic.visual_generation import generate_all_visuals
from src.logic.color_optimizer import generate_new_color_schemas, fix_color_schema, ShopifyColorSchemeOptimizer

# Load env vars
load_dotenv()

def print_progress(step, message):
    print(f"[{step.upper()}] {message}", flush=True)

def convert_cdn_to_shopify_schema(cdn_url):
    """Converts a raw CDN URL to the internal shopify:// schema."""
    if not cdn_url: return ""
    filename_part = cdn_url.split('/')[-1].split('?')[0]
    return f"shopify://shop_images/{filename_part}"

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--brand_name", default="Luminelle Beauty")
    parser.add_argument("--product_title", default="Éclat Sublime")
    parser.add_argument("--product_description", default="Crème Visage Hydratante Rose")
    parser.add_argument("--shopify_url", default=os.getenv("SHOPIFY_STORE_URL"))
    parser.add_argument("--access_token", default=os.getenv("SHOPIFY_ACCESS_TOKEN"))
    parser.add_argument("--primary_color", default="#EFB7C6")
    parser.add_argument("--language", default="fr")
    parser.add_argument("--input_image", default=os.path.join("input", "product.png"), help="Path to source product image")
    parser.add_argument("--test", action="store_true", help="Run in test mode (No AI costs)")
    args = parser.parse_args()

    if not args.shopify_url or not args.access_token:
        print("❌ Error: SHOPIFY_STORE_URL and SHOPIFY_ACCESS_TOKEN are required.")
        sys.exit(1)

    # Validate Input Image for Production Mode
    if not args.test and not os.path.exists(args.input_image):
        print(f"❌ Error: Input image not found at {args.input_image}. Required for AI generation.")
        sys.exit(1)

    job_id = str(uuid.uuid4())[:8]
    print_progress("setup", f"Starting Job: {job_id}")

    # Paths
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    PROJECT_ROOT = os.path.dirname(BASE_DIR)
    BASE_THEME_PATH = os.path.join(PROJECT_ROOT, "assets", "shopify-template")
    TEMP_DIR = os.path.join(PROJECT_ROOT, "temp_theme_build")

    if os.path.exists(TEMP_DIR): shutil.rmtree(TEMP_DIR)
    os.makedirs(TEMP_DIR, exist_ok=True)

    # Initialize
    client = ShopifyClient(args.shopify_url, args.access_token)
    theme_manager = ThemeManager(BASE_THEME_PATH, TEMP_DIR)

    ai_content = {}
    images_map = {} # Maps Placeholder -> shopify:// URL
    product_image_urls = [] # List of https:// CDN URLs for Product API
    video_shopify_url = None

    # ==============================================================================
    # 1. CONTENT GENERATION
    # ==============================================================================
    if args.test:
        print_progress("ai_text", "🧪 TEST MODE: Using Rich Mock Data...")
        ai_content = MOCK_THEME_CONTENT.copy()
        if args.brand_name != "Luminelle Beauty":
            ai_content["NEW_THEME_BRAND_NAME"] = args.brand_name
    else:
        print_progress("ai_text", "🧠 Generating Marketing Copy with OpenAI...")

        # A. Slogans & Blurbs
        ai_content["NEW_BRAND_SLOGAN_CONTENT"] = generate_slogan_prompt(args.product_title, args.product_description, args.language)
        first_slogan = ai_content["NEW_BRAND_SLOGAN_CONTENT"]

        ai_content["NEW_PRODUCT_BLURB_CONTENT"] = generate_product_blurb_prompt(args.product_title, args.product_description, args.language)
        ai_content["NEW_CTA_HERO_BUTTON_CONTENT"] = generate_cta_prompt(args.product_title, args.product_description, args.language)

        # B. Product Descriptions
        ai_content["NEW_PRODUCT_DESCRIPTION_1_CONTENT"] = generate_product_description_prompt(args.product_title, args.product_description, args.language)

        heading_prompt = f"Based on product title {args.product_title} and description {ai_content['NEW_PRODUCT_DESCRIPTION_1_CONTENT']} give me a 3 to 4 words heading in {args.language}. Return ONLY the text."
        ai_content["NEW_PRODUCT_HEADING_1_CONTENT"] = prompt_gpt(heading_prompt)

        ai_content["NEW_SECOND_SLOGAN_CONTENT"] = generate_alternative_slogan_prompt(args.product_title, args.product_description, first_slogan, args.language)

        # C. HTML Content
        ai_content["NEW_HIGHLIGHT_PRODUCT_FEATURES_CONTENT"] = generate_highlight_prompt(args.language, args.product_title, args.product_description)
        ai_content["NEW_WHY_CHOOSE_US_BRAND_TEXT_CONTENT"] = generate_why_choose_prompt(args.language, args.brand_name)

        # D. Video Text
        ai_content["NEW_PARAGRAPH_PRODUCT_TEXT_VIDEO"] = generate_content_prompt_product(args.product_title, args.product_description, args.language)
        ai_content["NEW_HEADING_PRODUCT_TEXT_VIDEO"] = generate_heading_prompt_product(args.product_title, args.product_description, args.language)

        # E. Complex Structures (JSON)
        
        print("   -> Generating Reviews (Structured)...")
        # 1. Get List of Dicts
        reviews_list = get_valid_reviews(args.product_title, args.product_description, args.language)
        
        # 2. Assign list directly for Multicolumn section
        ai_content["NEW_THEME_MULTICOLUMN_REVIEWS_LIST"] = reviews_list

        # 3. Construct HTML strings for Home Page placeholders
        for i in range(4):
            if i < len(reviews_list):
                r = reviews_list[i]
                html_review = f"<h2>{r['review_headline']}</h2><p></p><p>{r['review_body']}</p><h6><strong>{r['author_info']}</strong></h6>"
                ai_content[f"NEW_REVIEW_{i+1}_HOME_CONTENT"] = html_review
            else:
                ai_content[f"NEW_REVIEW_{i+1}_HOME_CONTENT"] = ""

        print("   -> Generating Q&A...")
        qna = generate_customer_qna(args.product_title, args.product_description, args.language)
        if qna:
            for i, item in enumerate(qna):
                idx = i + 1
                ai_content[f"NEW_THEME_FAQ_HEADING_{idx}"] = item.get("Question", "")
                ai_content[f"NEW_THEME_FAQ_CONTENT_{idx}"] = item.get("Answer", "")

        print("   -> Generating Pros...")
        pros = get_pros_json(args.product_title, args.product_description, args.language)
        if pros:
            ai_content["NEW_PROS_1_CONTENT"] = pros.get("pros_store_1", "")
            ai_content["NEW_PROS_2_CONTENT"] = pros.get("pros_store_2", "")
            ai_content["NEW_PROS_3_CONTENT"] = pros.get("pros_store_3", "")
            ai_content["NEW_PROS_4_CONTENT"] = pros.get("pros_store_4", "")
            ai_content["NEW_PROS_5_CONTENT"] = pros.get("pros_store_5", "")

        # --- F. FOOTER & TRUST BADGES (MISSING BLOCK ADDED HERE) ---
        print("   -> Generating Footer Features...")
        
        # 1. Shipping
        ai_content["NEW_THEME_FOOTER_FEATURE_1_TITLE"] = translate_text("Free Shipping", args.language)
        ai_content["NEW_THEME_FOOTER_FEATURE_1_DESCRIPTION"] = translate_text("On all orders over $50", args.language)
        
        # 2. Returns
        ai_content["NEW_THEME_FOOTER_FEATURE_2_TITLE"] = translate_text("Satisfied or Refunded", args.language)
        ai_content["NEW_THEME_FOOTER_FEATURE_2_DESCRIPTION"] = translate_text("30-day money-back guarantee", args.language)
        
        # 3. Support
        ai_content["NEW_THEME_FOOTER_FEATURE_3_TITLE"] = translate_text("Support 24/7", args.language)
        ai_content["NEW_THEME_FOOTER_FEATURE_3_DESCRIPTION"] = translate_text("Our team is here to help", args.language)
        
        # 4. Security
        ai_content["NEW_THEME_FOOTER_FEATURE_4_TITLE"] = translate_text("Secure Checkout", args.language)
        ai_content["NEW_THEME_FOOTER_FEATURE_4_DESCRIPTION"] = translate_text("100% Secure Payment", args.language)

        # Footer Misc
        ai_content["FOOTER_ANNOUNCEMENT_1"] = translate_text("Limited Time Offer: 20% OFF", args.language)
        ai_content["FOOTER_ANNOUNCEMENT_2"] = translate_text("New Arrivals Weekly", args.language)
        ai_content["FOOTER_NEWSLETTER_HEADING"] = translate_text("Join Our Newsletter", args.language)
        ai_content["FOOTER_NEWSLETTER_SUBHEADING"] = translate_text("Get exclusive deals and updates.", args.language)
        ai_content["FOOTER_NEWSLETTER_PRIVACY_NOTE"] = translate_text("We respect your privacy.", args.language)
        ai_content["FOOTER_GET_IN_TOUCH_TITLE"] = translate_text("Get In Touch", args.language)
        ai_content["FOOTER_GET_IN_TOUCH_DESCRIPTION"] = f"support@{args.brand_name.lower().replace(' ', '')}.com"

        # G. Translations (UI Elements)
        labels_to_translate = {
            "NEW_NEED_HELP_CONTENT": "Need Help ?",
            "NEW_OUR_TEAM_IS_HERE_CONTENT": "Our team is here to answer all your questions.",
            "NEW_CONTACT_US_BUTTON_CONTENT": "CONTACT US",
            "NEW_FREE_SHIPPING_TEXT_CONTENT": "FREE SHIPPING",
            "NEW_WATCH_DEMONSTRATION_CONTENT": "Watch The Demonstration",
            "NEW_SEE_COLLECTION_BUTTON_CONTENT": "SEE THE COLLECTION",
            "NEW_GET_THIS_OFFER_BUTTON_CONTENT": "GET THIS OFFER NOW",
            "NEW_EXCELLENT_CONTENT": "EXCELLENT",
            "NEW_PRODUCT_REVIEWS_HEADING_CONTENT": "Product Reviews and Ratings",
            "NEW_30DAY_GUARANTEE_CONTENT": "30-Day-Guarantee",
            "NEW_WHAT_OUR_CUSTOMERS_SAY_CONTENT": "what our customers say about us",
            "NEW_CUSTOMER_SERVICE_TEXT_CONTENT": "Customer Service",
            "NEW_CUSTOMER_SERVICE_PARAGRAPH_CONTENT": "Embrace the Freedom of Global Shipping with Every Purchase",
            "PRODUCT_SOLDOUT_TEXT": "Unfortunately this item is sold-out!",
            "PRODUCT_UNTRACKED_TEXT": "Currently this item has stock!",
            "PRODUCT_LOW_ONE_TEXT": "Hurry up! Only 1 item is in stock",
            "PRODUCT_LOW_MANY_TEXT": "Hurry up! Only [qty] items are in stock.",
            "PRODUCT_NORMAL_TEXT": "Currently <b>[qty] items</b> are in stock!",
            "PRODUCT_SHARE_LABEL": "Share",
            "PRODUCT_OTHERS_LABEL": "Others",
            "PRODUCT_RELATED_HEADING": "You may also like",
            "NEW_WANT_IT_BY_CONTENT": "Want it by",
            "NEW_ORDER_WITHIN_CONTENT": "ORDER WITHIN",
            "NEW_FREE_SHIPPING_CONTENT_ST": "FREE SHIPPING",
            "NEW_REVIEWS_NUMBER_CONTENT": "4.8 - 1356 Reviews",
            "NEW_SAFE_SECURE_PAYEMENT_CONTENT": "Safe & Secure payments",
            "NEW_FREE_SHIPPING_GLOBLY_CONTENT": "FREE SHIPPING GLOBLY",
            "NEW_FDA_CLEARED_CONTENT": "FDA CLEARED",
            "NEW_TRY_IT_RISK_FREE_FOR_90_DAYS_CONTENT": "TRY IT RISK-FREE FOR 90 DAYS",
            "NEW_LOOK_AT_OTHERS_CONTENT": "Look At How Others Are Loving Their Product!",
            "NEW_CLAIM_OFFER_CONTENT": "CLAIM OFFER",
            "NEW_REAL_OFFER_PEOPLE_CONTENT": "Real Reviews From Real People",
            "NEW_WHY_CHOOSE_US_CONTENT": "Why Choose Us ?",
            "NEW_FAQs_CONTENT": "FAQs",
            "NEW_CUSTOMER_QA_CONTENT": "CUSTOMERS Q&A",
            "NEW_758_PURCHASED_CONTENT": "and 758 people purchased"
        }

        print("   -> Translating Labels...")
        for key, text in labels_to_translate.items():
            ai_content[key] = translate_text(text, args.language)

        original_benefits = r"<p>🚚 Free shipping with every order<br\/>☎️ 24\/7 Customer support<br\/>🗓️ 30-Day-Guarantee<br\/>✨ 4.9\/5 Customer rating<\/p>"
        ai_content["NEW_THEME_BENEFITS_PRODUCT_CONTENT"] = translate_benefits(original_benefits, args.language)


    # ==============================================================================
    # 2. IMAGES & VIDEO GENERATION
    # ==============================================================================

    generated_assets = {}
    local_video_path = None

    if args.test:
        print_progress("images", "🧪 TEST MODE: Generating Local Mock Assets...")
        generated_assets, local_video_path = mock_generate_all_visuals(
            args.product_title,
            args.product_description,
            args.input_image,
            TEMP_DIR
        )
    else:
        print_progress("images", "🎨 Generating AI Visuals (DALL-E 2 + RunwayML)...")
        generated_assets, local_video_path = generate_all_visuals(
            args.product_title,
            args.product_description,
            args.input_image,
            TEMP_DIR
        )

    if generated_assets:
        print("   -> Uploading assets to Shopify Storage...")
        for placeholder, local_path in generated_assets.items():
            cdn_url = client.upload_local_file(local_path, mime_type="image/png", resource="IMAGE")
            if cdn_url:
                theme_schema_url = convert_cdn_to_shopify_schema(cdn_url)
                images_map[placeholder] = theme_schema_url
                product_image_urls.append(cdn_url)
            else:
                print(f"      ❌ Failed to upload {placeholder}")

    if local_video_path and os.path.exists(local_video_path):
        print("   -> Uploading video to Shopify...")
        video_shopify_url = client.upload_video_to_shopify(local_video_path, "Product Video")
        if video_shopify_url:
            print(f"      ✅ Video Ready: {video_shopify_url}")
        else:
            print("      ❌ Video upload failed.")
    else:
        print("   ⚠️ No video was generated.")


    # ==============================================================================
    # 3. CREATE PRODUCT
    # ==============================================================================
    print_progress("shopify_product", "Creating product...")
    product = client.create_product(
        title=args.product_title,
        html_body=f"<p>{args.product_description}</p>",
        image_urls=product_image_urls,
        brand=args.brand_name
    )
    product_handle = product["handle"] if product else "test-product"

    # ==============================================================================
    # 4. CREATE PAGES
    # ==============================================================================
    print_progress("shopify_pages", "Creating Pages...")
    about_html = f"""
    <div class="about-us">
        <h1>À propos de {args.brand_name}</h1>
        <p>Bienvenue chez {args.brand_name}. Nous sommes dédiés à l'excellence.</p>
    </div>
    """
    page_id = client.create_page(f"À propos", about_html)
    if page_id: client.add_page_to_menu(str(page_id), "À propos")

    # ==============================================================================
    # 5. THEME INJECTION & PROCESSING
    # ==============================================================================
    print_progress("inject", "Injecting content into theme...")
    workspace_path = theme_manager.setup_workspace(job_id)

    # A. Standard replacement
    theme_manager.process_notebook_logic(
        workspace_path, ai_content, images_map, args.primary_color, args.brand_name, product_handle
    )

    # ==============================================================================
    # 6. COLOR INTELLIGENCE
    # ==============================================================================
    print_progress("colors", "Applying Color Intelligence...")

    color_replacements = {
        "#7069BC": args.primary_color,
        "#6E65BC": args.primary_color,
        "NEW_WAVE_COLOR": args.primary_color
    }

    if args.test:
        print("   🧪 Test Mode: Running hex replacement only.")
        replace_colors_in_json_files(workspace_path, color_replacements)
    else:
        print("   🧠 Production Mode: Generating Full Color Schema (GPT-4o)...")

        settings_path = os.path.join(workspace_path, "config", "settings_data.json")
        index_path = os.path.join(workspace_path, "templates", "index.json")
        product_path = os.path.join(workspace_path, "templates", "product.json")

        try:
            with open(settings_path, 'r') as f:
                settings_content = f.read()

            # 1. Generate Schema
            new_schema_str = generate_new_color_schemas(
                original_color_schema=settings_content,
                theme_primary_color=args.primary_color,
                theme_description="Luxury Brand",
                index_json_path=index_path,
                images_folder_path=TEMP_DIR
            )

            # 2. Sanitize & Write
            fixed_schema = fix_color_schema(new_schema_str)
            # Verify JSON valid before writing
            json.loads(fixed_schema)

            with open(settings_path, 'w') as f:
                f.write(fixed_schema)
            print("   ✅ Applied AI Schema.")

            # 3. Optimize Sections
            optimizer = ShopifyColorSchemeOptimizer()
            optimizer.optimize_theme_colors(fixed_schema, index_path, TEMP_DIR)
            optimizer.optimize_theme_colors(fixed_schema, product_path, TEMP_DIR)

        except Exception as e:
            print(f"   ❌ Color Generation Failed ({e}). Falling back to simple replacement.")

        # 4. Run cleanup replacement anyway
        replace_colors_in_json_files(workspace_path, color_replacements)


    # ==============================================================================
    # 7. VIDEO & FINALIZATION
    # ==============================================================================
    if video_shopify_url:
        print_progress("video", "Injecting Video ID into JSONs...")
        inject_video_id(workspace_path, video_shopify_url)

    # ==============================================================================
    # 8. UPLOAD & PUBLISH
    # ==============================================================================
    print_progress("zip", "Zipping theme...")
    zip_path = theme_manager.zip_theme(workspace_path)

    print_progress("hosting", "Uploading to Shopify Storage...")
    uploaded_file_url = client.upload_local_file(zip_path, mime_type="application/zip", resource="FILE")

    if not uploaded_file_url:
        raise Exception("Upload failed")

    print_progress("shopify_upload", "Installing theme...")
    theme_id = client.upload_theme(uploaded_file_url, f"AutoTheme-{job_id}")

    if theme_id:
        print(f"✅ Theme ID: {theme_id}")
        client.publish_theme(theme_id)

        print_progress("language", f"Activating Language: {args.language}")
        client.enable_store_language(args.language)

        print("DONE! 🚀")
    else:
        print("❌ Theme upload failed")

if __name__ == "__main__":
    main()