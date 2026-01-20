import os
import sys
import json
import uuid
import shutil
import argparse
from dotenv import load_dotenv

# Ensure the project root is in the python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# --- IMPORTS ---
from src.clients.shopify_client import ShopifyClient
from src.theme_manager import ThemeManager
from src.logic.theme_utils import replace_colors_in_json_files, inject_video_id
from src.mocks.data_payloads import MOCK_THEME_CONTENT, MOCK_IMAGES # Imported Rich Data

# Load env vars
load_dotenv()

def print_progress(step, message):
    print(f"[{step.upper()}] {message}", flush=True)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--brand_name", default="Luminelle Beauty")
    parser.add_argument("--product_title", default="Éclat Sublime")
    parser.add_argument("--product_description", default="Crème Visage Hydratante Rose")
    parser.add_argument("--shopify_url", default=os.getenv("SHOPIFY_STORE_URL"))
    parser.add_argument("--access_token", default=os.getenv("SHOPIFY_ACCESS_TOKEN"))
    parser.add_argument("--primary_color", default="#EFB7C6") 
    parser.add_argument("--language", default="fr") 
    parser.add_argument("--test", action="store_true", help="Run in test mode (No AI costs)")
    args = parser.parse_args()

    if not args.shopify_url or not args.access_token:
        print("❌ Error: SHOPIFY_STORE_URL and SHOPIFY_ACCESS_TOKEN are required.")
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
    images_map = {}
    product_image_urls = []
    
    # --- 1. CONTENT ---
    if args.test:
        print_progress("ai_text", "🧪 TEST MODE: Using Rich Mock Data (from src/mocks/data_payloads.py)...")
        # Load the rich content from the separate file
        ai_content = MOCK_THEME_CONTENT.copy()
        
        # Optional: Override brand name if user provided a specific one via CLI, 
        # otherwise keep the rich "Luminelle Beauty" from mock
        if args.brand_name != "Luminelle Beauty":
            ai_content["NEW_THEME_BRAND_NAME"] = args.brand_name
    else:
        # Real AI Logic would go here
        print("Real AI not implemented in this snippet, use --test")
        sys.exit(1)

    # --- 2. IMAGES & VIDEO ---
    video_shopify_url = None
    
    if args.test:
        print_progress("images", "🧪 TEST MODE: Uploading Mock Images/Video...")
        
        # 1. Images
        for placeholder, url in MOCK_IMAGES.items():
            print(f"   -> Uploading {placeholder}...")
            shopify_url = client.upload_image_from_url(url, f"mock_{placeholder[:5]}.jpg")
            if shopify_url:
                images_map[placeholder] = shopify_url
                product_image_urls.append(url) 

        # 2. Video (Mock upload of a dummy file to get a valid Shopify Video ID)
        dummy_video_path = os.path.join(TEMP_DIR, "mock_video.mp4")
        with open(dummy_video_path, "wb") as f:
            f.write(b"dummy content" * 1024) 
        
        # We need a real video ID for the theme to work. 
        # We try to upload the local dummy file.
        video_shopify_url = client.upload_video_to_shopify(dummy_video_path, "Product Video")
        if video_shopify_url:
             print(f"   -> Video Uploaded: {video_shopify_url}")
        else:
             print("   ⚠️ Video upload failed or skipped.")

    # --- 3. CREATE PRODUCT ---
    print_progress("shopify_product", "Creating product...")
    product = client.create_product(
        title=args.product_title,
        html_body=f"<p>{args.product_description}</p>",
        image_urls=product_image_urls,
        brand=args.brand_name
    )
    product_handle = product["handle"] if product else "test-product"
    
    # --- 4. PAGES ---
    print_progress("shopify_pages", "Creating Pages...")
    # Basic About Us HTML (could also be moved to payloads if very complex)
    about_html = f"""
    <div class="about-us">
        <h1>À propos de {args.brand_name}</h1>
        <p>Bienvenue chez {args.brand_name}. Nous sommes dédiés à l'excellence.</p>
    </div>
    """
    page_id = client.create_page(f"À propos", about_html)
    if page_id: client.add_page_to_menu(str(page_id), "À propos")

    # --- 5. THEME INJECTION ---
    print_progress("inject", "Injecting content into theme...")
    workspace_path = theme_manager.setup_workspace(job_id)
    
    # A. Standard replacement (Text & Images)
    theme_manager.process_notebook_logic(
        workspace_path, ai_content, images_map, args.primary_color, args.brand_name, product_handle
    )

    # B. RECURSIVE COLOR REPLACEMENT
    print_progress("colors", "Applying Deep Color Replacement...")
    color_replacements = {
        "#7069BC": args.primary_color,
        "#6E65BC": args.primary_color,
        "NEW_WAVE_COLOR": args.primary_color
    }
    replace_colors_in_json_files(workspace_path, color_replacements)

    # C. VIDEO INJECTION
    if video_shopify_url:
        print_progress("video", "Injecting Video ID into JSONs...")
        inject_video_id(workspace_path, video_shopify_url)

    # --- 6. UPLOAD & PUBLISH ---
    print_progress("zip", "Zipping theme...")
    zip_path = theme_manager.zip_theme(workspace_path)
    
    print_progress("hosting", "Uploading to Shopify Storage...")
    uploaded_file_url = client.upload_local_file(zip_path)
    
    if not uploaded_file_url:
        raise Exception("Upload failed")

    print_progress("shopify_upload", "Installing theme...")
    theme_id = client.upload_theme(uploaded_file_url, f"AutoTheme-{job_id}")
    
    if theme_id:
        print(f"✅ Theme ID: {theme_id}")
        client.publish_theme(theme_id)
        
        # D. LANGUAGE ACTIVATION
        print_progress("language", f"Activating Language: {args.language}")
        client.enable_store_language(args.language)
        
        print("DONE! 🚀")
    else:
        print("❌ Theme upload failed")

if __name__ == "__main__":
    main()