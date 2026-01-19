import os
import json
import re

def strip_json_comments(content):
    """
    Removes C-style comments from JSON content (/* ... */)
    so that the standard json parser can read it.
    """
    # Regex to match /* ... */ comments
    pattern = r'/\*[\s\S]*?\*/'
    return re.sub(pattern, '', content)

def replace_colors_in_json_files(folder_path: str, color_replacements: dict):
    """
    Recursively replaces hex codes in all JSON files (Settings, Templates, Sections).
    Handles files with comments gracefully.
    """
    if not os.path.exists(folder_path):
        return

    print(f"🎨 Running Recursive Color Replacement in {folder_path}...")

    def replace_in_value(value):
        replacements_made = 0
        if isinstance(value, str):
            original_value = value
            for original_color, new_color in color_replacements.items():
                pattern = re.escape(original_color)
                # Case insensitive replacement
                value = re.sub(pattern, new_color, value, flags=re.IGNORECASE)
            if value != original_value:
                replacements_made = 1
        elif isinstance(value, dict):
            for key, val in value.items():
                new_val, count = replace_in_value(val)
                value[key] = new_val
                replacements_made += count
        elif isinstance(value, list):
            for i, item in enumerate(value):
                new_item, count = replace_in_value(item)
                value[i] = new_item
                replacements_made += count
        return value, replacements_made

    for root, dirs, files in os.walk(folder_path):
        json_files = [f for f in files if f.lower().endswith('.json')]
        for filename in json_files:
            file_path = os.path.join(root, filename)
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Clean content before parsing
                clean_content = strip_json_comments(content)
                
                if not clean_content.strip():
                    continue # Skip empty files

                data = json.loads(clean_content)

                modified_data, count = replace_in_value(data)

                if count > 0:
                    with open(file_path, 'w', encoding='utf-8') as f:
                        json.dump(modified_data, f, indent=2, ensure_ascii=False)
            except json.JSONDecodeError:
                # Still warn, but clarify it's a parsing error
                print(f"   ⚠️ Skipping invalid JSON: {filename}")
            except Exception as e:
                print(f"   ⚠️ Error processing {filename}: {e}")

def inject_video_id(theme_root: str, video_id: str):
    """
    Injects the Shopify Video ID into index.json and product.json.
    """
    if not video_id:
        return

    print(f"🎥 Injecting Video ID ({video_id}) into templates...")
    
    files_to_check = [
        os.path.join(theme_root, "templates", "index.json"),
        os.path.join(theme_root, "templates", "product.json")
    ]

    for file_path in files_to_check:
        if not os.path.exists(file_path):
            continue

        try:
            # 1. String Replacement
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Replace placeholder if exists
            updated_content = content.replace("NEW_THEME_PRODUCT_VIDEO", video_id)
            updated_content = updated_content.replace("NEW_VIDEO_SOURCE_PRODUCT", video_id)

            # 2. JSON Object Replacement (Logic for specific section types)
            # Remove comments before parsing to be safe
            clean_content = strip_json_comments(updated_content)
            data = json.loads(clean_content)
            
            if "sections" in data:
                for section_id, section_data in data["sections"].items():
                    # Match video-with-text or similar video sections
                    if section_data.get("type") in ["video-with-text", "video", "video-text"]:
                        if "settings" in section_data:
                            section_data["settings"]["video"] = video_id
                            print(f"   -> Updated section {section_id} in {os.path.basename(file_path)}")

            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

        except Exception as e:
            print(f"   ⚠️ Error injecting video in {os.path.basename(file_path)}: {e}")