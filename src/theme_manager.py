import os
import json
import shutil
import uuid
import re

class ThemeManager:
    def __init__(self, base_theme_path: str, temp_dir: str):
        self.base_theme_path = base_theme_path
        self.temp_dir = temp_dir
        
        self.reviews_blocks = {}
        self.reviews_order = []
        self.faq_data = {}
        self.comparison_data = {}

    def setup_workspace(self, order_id: str) -> str:
        workspace_path = os.path.join(self.temp_dir, f"order_{order_id}")
        if os.path.exists(workspace_path):
            shutil.rmtree(workspace_path)
            
        src_theme = os.path.join(self.base_theme_path, "new-new")
        if not os.path.exists(src_theme):
            raise FileNotFoundError(f"Base theme not found at {src_theme}")
            
        shutil.copytree(src_theme, workspace_path)

        # --- CRITICAL FIX: Use the correct files from root ---
        # The files inside new-new/templates are outdated/wrong. 
        # We overwrite them with the ones from assets/base-theme/
        files_to_repair = {
            "index.json": "templates",
            "product.json": "templates",
            "page.contact.json": "templates",
            "settings_data.json": "config",
            "footer-group.json": "sections"
        }

        print("🔧 Repairing theme structure (Forcing correct template copies)...")
        for fname, dest_sub in files_to_repair.items():
            dest_file_path = os.path.join(workspace_path, dest_sub, fname)
            loose_source = os.path.join(self.base_theme_path, fname)
            
            if os.path.exists(loose_source):
                os.makedirs(os.path.dirname(dest_file_path), exist_ok=True)
                shutil.copy(loose_source, dest_file_path)
                print(f"   -> Overwrote {fname} from base-theme root")
            else:
                print(f"   ⚠️ Warning: Could not find {fname} in base-theme root")

        return workspace_path

    def prepare_data(self, ai_content: dict):
        self.reviews_blocks = {}
        self.reviews_order = []
        raw_reviews = ai_content.get("NEW_THEME_MULTICOLUMN_REVIEWS_LIST", [])
        if not raw_reviews:
             raw_reviews = [{"stars": "★★★★★", "review_headline": "Great", "review_body": "Amazing product", "author_info": "Customer"}] * 3

        for i, r in enumerate(raw_reviews[:6]):
            bid = f"review_{uuid.uuid4().hex[:8]}"
            self.reviews_order.append(bid)
            self.reviews_blocks[bid] = {
                "type": "column",
                "settings": {
                    "title": r.get("stars", "★★★★★"),
                    "text": f"<h1>{r.get('review_headline','')}</h1><p></p><p>{r.get('review_body','')}</p><h6><strong>{r.get('author_info','')}</strong></h6>"
                }
            }

        self.comparison_data = {}
        comp_ids = ["testimonial_dPRTJq", "testimonial_EzR6nx"]
        raw_comp = ai_content.get("NEW_THEME_COMPARISON_LIST", [])
        for i, c in enumerate(raw_comp[:2]):
            self.comparison_data[comp_ids[i]] = {
                "type": "testimonial",
                "settings": {
                    "caption": c.get("caption", ""),
                    "heading": c.get("testimonial_text", ""),
                    "text": f"<p><strong>{c.get('caption','')}</strong><br/>— <em>{c.get('author_info','')}</em></p>"
                }
            }
            
        self.faq_data = {}
        faq_ids = ["collapsible_row_1", "collapsible_row_2", "collapsible_row_3", "collapsible_row_4"]
        raw_faq = ai_content.get("NEW_THEME_FAQ_LIST", [])
        for i, f in enumerate(raw_faq[:4]):
            self.faq_data[faq_ids[i]] = {
                "type": "collapsible_row",
                "settings": {
                    "heading": f.get("question", ""),
                    "row_content": f"<p>{f.get('answer', '')}</p>"
                }
            }

    def cleanup_placeholders(self, content: str) -> str:
        """
        CRITICAL: Removes any remaining NEW_... placeholders.
        If these are left in fields like 'image', Shopify deletes the file.
        """
        # Replace "NEW_THEME_..." or "NEW_..._CONTENT" with empty string
        # We try to catch quotes around them if possible to avoid empty strings in JSON where null might be better,
        # but empty string "" is generally safe for Shopify image/text fields.
        content = re.sub(r'NEW_THEME_[A-Z0-9_]+', '', content)
        content = re.sub(r'NEW_[A-Z0-9_]+_CONTENT', '', content)
        return content

    def process_notebook_logic(self, workspace_path: str, ai_content: dict, images_map: dict, main_color: str, brand_name: str, product_handle: str):
        self.prepare_data(ai_content)
        
        f_index = os.path.join(workspace_path, "templates", "index.json")
        f_settings = os.path.join(workspace_path, "config", "settings_data.json")
        f_product = os.path.join(workspace_path, "templates", "product.json")
        f_footer = os.path.join(workspace_path, "sections", "footer-group.json")
        f_contact = os.path.join(workspace_path, "templates", "page.contact.json")

        # 1. SETTINGS
        if os.path.exists(f_settings):
            with open(f_settings, 'r') as f: content = f.read()
            content = content.replace("NEW_THEME_PRIMARY_COLOR", main_color)
            content = content.replace("NEW_THEME_BRAND_NAME", brand_name)
            for k, v in ai_content.items():
                if k.startswith("NEW_THEME_COLOR_SCHEME"):
                    content = content.replace(k, str(v))
            for k in ["NEW_THEME_SECONDARY_COLOR", "NEW_THEME_SECTION1_HEADING", "NEW_THEME_SECTION1_DESCRIPTION", 
                      "NEW_THEME_MAIN_TITLE_HERO_SLOGAN", "NEW_THEME_SECTION2_HEADING", "NEW_THEME_SECTION2_DESCRIPTION"]:
                content = content.replace(k, str(ai_content.get(k, "")))
            
            content = self.cleanup_placeholders(content)
            with open(f_settings, 'w') as f: f.write(content)

        # 2. INDEX
        if os.path.exists(f_index):
            with open(f_index, 'r') as f: content = f.read()
            for k, v in images_map.items():
                content = content.replace(k, v)
            
            pattern = r'"product":\s*"[^"]*"'
            replacement = f'"product": "{product_handle}"'
            content = re.sub(pattern, replacement, content)

            # Use lambda for regex replacement to prevent JSON corruption
            blocks_json = json.dumps(self.reviews_blocks, ensure_ascii=False)
            pattern = r'"blocks"\s*:\s*"NEW_THEME_MULTICOLUMN_REVIEWS_BLOCKS"'
            content = re.sub(pattern, lambda m: f'"blocks": {blocks_json}', content)

            order_json = json.dumps(self.reviews_order, ensure_ascii=False)
            pattern = r'"block_order"\s*:\s*"NEW_THEME_MULTICOLUMN_REVIEWS_BLOCK_ORDER"'
            content = re.sub(pattern, lambda m: f'"block_order": {order_json}', content)

            content = content.replace("NEW_THEME_COMPARISON_DATA", json.dumps(self.comparison_data, ensure_ascii=False))
            
            text_keys = [
                "NEW_THEME_INITIAL_REVIEW_TITLE", "NEW_THEME_INITIAL_REVIEW_SUBTITLE",
                "NEW_THEME_ANNOUNCEMENT_TEXT1", "NEW_THEME_ANNOUNCEMENT_TEXT2",
                "NEW_THEME_PRODUCT_PHILOSOPHY", "NEW_THEME_IMAGE_WITH_TEXT_TITLE1",
                "NEW_THEME_IMAGE_WITH_TEXT_TEXT1", "NEW_THEME_COMPARISON_TABLE_WHY_OUR_PRODUCT",
                "NEW_THEME_COMPARISON_TABLE_TEXT", "NEW_THEME_BRAND_NAME",
                "NEW_THEME_MAIN_TITLE_HERO_SLOGAN", "NEW_THEME_SUBTITLE_HERO",
                "NEW_THEME_MAIN_TITLE_FEATURE", "NEW_THEME_TEXT_FEATURE",
                "NEW_THEME_VIDEO_DESCRIPTION", "NEW_THEME_MAIN_TITLE_VIDEO",
                "NEW_THEME_VIDEO_BUTTON_TEXT", "NEW_THEME_PRODUCT_SHOWCASE_REVIEW",
                "NEW_THEME_PRODUCT_IMAGE_CAPTION_1", "NEW_THEME_PRODUCT_IMAGE_CAPTION_2",
                "NEW_THEME_REVIEWS_SECTION_HEADLINE", "NEW_THEME_CUSTOMERS_REVIEW_TEXT_DESCRIPTION",
                "NEW_THEME_PRODUCT_IMAGE_TITLE", "NEW_THEME_BENIFIT_AND_FEATURE",
                "NEW_THEME_SHOP_COLLECTION_TRANSLATION", "NEW_THEME_PRODUCT_IMAGE_TITLE_2",
                "NEW_THEME_HELP_SECTION_HEADLINE", "NEW_THEME_HELP_SECTION_SUBHEADING"
            ]
            for k in text_keys:
                content = content.replace(k, str(ai_content.get(k, "")))
            content = content.replace("HERO_BUTTON_TEXT", str(ai_content.get("NEW_THEME_SUBTITLE_BUTTON_TEXT", "Shop Now")))
            
            # Remove any left-over placeholders
            content = self.cleanup_placeholders(content)
            
            with open(f_index, 'w') as f: f.write(content)

        # 3. PRODUCT
        if os.path.exists(f_product):
            with open(f_product, 'r') as f: content = f.read()
            content = content.replace("NEW_THEME_FAQ_DATA", json.dumps(self.faq_data, ensure_ascii=False))
            p_keys = ["NEW_THEME_WHAT_MAKES_OUR_PRODUCT_UNIQUE_TITLE", "NEW_THEME_PRODUCT_PAGE_IT1_TITLE",
                      "NEW_THEME_PRODUCT_PAGE_IT1_TEXT", "NEW_THEME_PRODUCT_PAGE_IT2_TITLE",
                      "NEW_THEME_PRODUCT_PAGE_IT2_TEXT", "NEW_THEME_TABLE_COMPARISON_WHY",
                      "NEW_THEME_VIDEO_TEXT_HEADING_PRODUCT_PAGE", "NEW_THEME_VIDEO_TEXT_TEXT_PRODUCT_PAGE",
                      "NEW_THEME_PRODUCT_BLURB_CONTENT"]
            for k in p_keys:
                content = content.replace(k, str(ai_content.get(k, "")))
            
            content = self.cleanup_placeholders(content)
            with open(f_product, 'w') as f: f.write(content)

        # 4. FOOTER
        if os.path.exists(f_footer):
            with open(f_footer, 'r') as f: content = f.read()
            f_keys = ["NEW_THEME_FOOTER_FEATURE_1_TITLE", "NEW_THEME_FOOTER_FEATURE_1_DESCRIPTION",
                      "NEW_THEME_FOOTER_FEATURE_2_TITLE", "NEW_THEME_FOOTER_FEATURE_2_DESCRIPTION",
                      "NEW_THEME_FOOTER_FEATURE_3_TITLE", "NEW_THEME_FOOTER_FEATURE_3_DESCRIPTION",
                      "NEW_THEME_FOOTER_FEATURE_4_TITLE", "NEW_THEME_FOOTER_FEATURE_4_DESCRIPTION",
                      "FOOTER_ANNOUNCEMENT_1", "FOOTER_ANNOUNCEMENT_2", "FOOTER_NEWSLETTER_HEADING",
                      "FOOTER_NEWSLETTER_SUBHEADING", "FOOTER_NEWSLETTER_PRIVACY_NOTE",
                      "FOOTER_GET_IN_TOUCH_TITLE", "FOOTER_GET_IN_TOUCH_DESCRIPTION"]
            for k in f_keys:
                content = content.replace(k, str(ai_content.get(k, "")))
            
            content = self.cleanup_placeholders(content)
            with open(f_footer, 'w') as f: f.write(content)

        # 5. CONTACT
        if os.path.exists(f_contact):
            with open(f_contact, 'r') as f: content = f.read()
            c_keys = ["CONTACT_US_PAGE_HEADING", "CONTACT_US_BANNER_SUBHEADING", "GET_IN_TOUCH_TRANSLATION",
                      "CONTACT_US_GET_IN_TOUCH_DESCRIPTION", "SUMMER_SALE_TRANSLATION", "SALE_BANNER_SUBHEADING",
                      "SHOP_SALE_NOW", "BUNDLE_AND_SALE_TRANSLATION", "BUNDLE_BANNER_SUBHEADING",
                      "SHOP_BUNDLE_TRANSLATION"]
            for k in c_keys:
                content = content.replace(k, str(ai_content.get(k, "")))
            content = content.replace("NEW_CONTACT_PAGE_IMAGE_BANNER", images_map.get("NEW_THEME_HERO_BANNER", ""))
            
            content = self.cleanup_placeholders(content)
            with open(f_contact, 'w') as f: f.write(content)

    def zip_theme(self, workspace_path: str) -> str:
        zip_base = workspace_path
        shutil.make_archive(zip_base, 'zip', workspace_path)
        return f"{zip_base}.zip"