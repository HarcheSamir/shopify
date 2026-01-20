import os
import requests
import uuid

def download_mock_image(text, size, output_path):
    """Downloads a placeholder image with specific text."""
    # Using placehold.co which generates images on the fly
    # text is URL encoded
    url = f"https://placehold.co/{size}/EFB7C6/ffffff/png?text={text.replace(' ', '+')}"
    try:
        response = requests.get(url)
        if response.status_code == 200:
            with open(output_path, "wb") as f:
                f.write(response.content)
            return True
    except:
        pass
    return False

def mock_generate_all_visuals(product_title, product_description, input_image_path, temp_dir):
    """
    Simulates the AI generation process by creating local placeholder files.
    Returns: generated_assets (dict), video_path (str)
    """
    print("🧪 [MOCK] Generating Mock Assets locally...")
    
    generated_assets = {}
    
    # Define the assets we expect from the AI
    mock_map = [
        ("studio_enhancement", "NEW_THEME_PRODUCT_IMAGE_LUMIN_SECTION", "1024x1536"),
        ("banner_landscape", "NEW_THEME_HERO_BANNER", "1536x1024"),
        ("banner_square", "NEW_THEME_COLLECTION_IMAGE", "1024x1024"),
        ("in_use_1", "NEW_THEME_PRODUCT_SHOWCASE_IMAGE_1", "1024x1024"),
        ("in_use_2", "NEW_THEME_PRODUCT_SHOWCASE_IMAGE_2", "1024x1024"),
        ("in_use_3", "NEW_THEME_IMAGE_LUMIN_GRID_1", "1024x1024")
    ]

    for prompt_type, placeholder, size in mock_map:
        filename = f"mock_{prompt_type}_{str(uuid.uuid4())[:6]}.png"
        path = os.path.join(temp_dir, filename)
        
        print(f"   -> Creating mock image for {prompt_type}...")
        success = download_mock_image(f"MOCK+{prompt_type.upper()}", size, path)
        
        if success:
            generated_assets[placeholder] = path

    # Mock Video
    print("   -> Creating mock video...")
    video_filename = "mock_video.mp4"
    video_path = os.path.join(temp_dir, video_filename)
    # Create a valid dummy mp4 file (just text content, won't play but uploads fine)
    # OR better, if input video exists, copy it. If not, make dummy.
    with open(video_path, "wb") as f:
        f.write(b"Mock Video Content" * 1000)
    
    return generated_assets, video_path