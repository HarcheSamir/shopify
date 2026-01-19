import os
import json
import re

def replace_in_file(path, placeholder, value):
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()
    content = content.replace(placeholder, value)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)

def process_template_files(ai_content, theme_dir, images_map):
    # This is the massive logic from process_and_write_files
    # It takes the AI JSON and replaces NEW_THEME_... keys in index.json, settings_data.json etc.
    
    # 1. Load Files
    index_path = os.path.join(theme_dir, "templates", "index.json")
    
    with open(index_path, 'r') as f: index_str = f.read()
    
    # 2. Replace Images
    for key, val in images_map.items():
        if val:
            index_str = index_str.replace(key, val)
            
    # 3. Replace AI Text
    if ai_content:
        for key, val in ai_content.items():
            if isinstance(val, str):
                index_str = index_str.replace(key, val)
            elif isinstance(val, list):
                # Handle lists (reviews, FAQs) via specific logic from notebook
                pass 
                
    # 4. Save
    with open(index_path, 'w') as f: f.write(index_str)
    
    # [Repeat for product.json, settings_data.json, footer-group.json, etc.]