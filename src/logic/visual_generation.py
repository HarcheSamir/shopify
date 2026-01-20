import os
import uuid
import requests
from src.clients.openai_client import generate_prompts_struct, edit_images_with_openai
from src.clients.imgbb import upload_to_imgbb
from src.clients.runway_client import generate_video, poll_video

def download_file(url, output_path):
    """Helper to download the video from Runway."""
    try:
        response = requests.get(url, stream=True)
        response.raise_for_status()
        with open(output_path, "wb") as f:
            for chunk in response.iter_content(1024):
                f.write(chunk)
        return output_path
    except Exception as e:
        print(f"❌ Failed to download file from {url}: {e}")
        return None

def generate_all_visuals(product_title, product_description, input_image_path, temp_dir):
    """
    Orchestrates the full AI visual pipeline:
    1. Generate 6 Prompts.
    2. Edit Images (Inpainting).
    3. Generate Video (from Studio shot).
    4. Return mapping of Placeholders -> Local File Paths.
    """
    
    print("🎨 Generating Photography Prompts (GPT-4o)...")
    prompts_data = generate_prompts_struct(product_title, product_description)
    
    if not prompts_data or not prompts_data.prompts:
        print("❌ Failed to generate prompts structure.")
        return {}, None

    generated_assets = {}
    video_path = None
    
    # Mapping Notebook Logic: Prompt Type -> Theme Placeholder
    # Note: We need to handle them carefully.
    
    for item in prompts_data.prompts:
        print(f"📸 Generating {item.prompt_type}: {item.purpose}...")
        
        # 1. Define Output Path
        unique_filename = f"{item.prompt_type}_{str(uuid.uuid4())[:8]}.png"
        output_path = os.path.join(temp_dir, unique_filename)
        
        # 2. Generate Image (Edit/Inpaint)
        # Note: The notebook passes the *same* input product image for every edit
        generated_image_path = edit_images_with_openai(
            image_path=input_image_path,
            prompt=item.prompt,
            size=item.image_size, # e.g. 1024x1024 or 1024x1536
            output_path=output_path
        )
        
        if not generated_image_path:
            continue

        # 3. Map to Theme Placeholders
        # Logic extracted directly from notebook loop
        if item.prompt_type == "studio_enhancement":
            generated_assets["NEW_THEME_PRODUCT_IMAGE_LUMIN_SECTION"] = generated_image_path
            
            # --- VIDEO BRANCH ---
            print("🎥 Starting Video Generation Pipeline (RunwayML)...")
            # A. Upload to ImgBB to get public URL
            public_img_url = upload_to_imgbb(generated_image_path)
            
            if public_img_url:
                # B. Trigger Runway
                task_id = generate_video(public_img_url)
                if task_id:
                    # C. Poll for result
                    video_url = poll_video(task_id)
                    if video_url:
                        # D. Download Video
                        vid_filename = f"video_{str(uuid.uuid4())[:8]}.mp4"
                        local_vid_path = os.path.join(temp_dir, vid_filename)
                        download_file(video_url, local_vid_path)
                        video_path = local_vid_path
                        print(f"✅ Video ready at: {local_vid_path}")
            # --------------------

        elif item.prompt_type == "banner_landscape":
            generated_assets["NEW_THEME_HERO_BANNER"] = generated_image_path
            
        elif item.prompt_type == "banner_square":
            generated_assets["NEW_THEME_COLLECTION_IMAGE"] = generated_image_path
            
        elif item.prompt_type == "in_use_1":
            generated_assets["NEW_THEME_PRODUCT_SHOWCASE_IMAGE_1"] = generated_image_path
            
        elif item.prompt_type == "in_use_2":
            generated_assets["NEW_THEME_PRODUCT_SHOWCASE_IMAGE_2"] = generated_image_path
            
        elif item.prompt_type == "in_use_3":
            generated_assets["NEW_THEME_IMAGE_LUMIN_GRID_1"] = generated_image_path

    return generated_assets, video_path