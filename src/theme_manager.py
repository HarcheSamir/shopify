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
                print(f"   -> Overwrote {fname} from shopify-template root")
            else:
                print(f"   ⚠️ Warning: Could not find {fname} in shopify-template root")

        return workspace_path

    def prepare_data(self, ai_content: dict):
        # --- REVIEWS ---
        self.reviews_blocks = {}
        self.reviews_order = []
        raw_reviews = ai_content.get("NEW_THEME_MULTICOLUMN_REVIEWS_LIST", [])

        if not raw_reviews:
            print("   ⚠️ No reviews found in ai_content, skipping injection.")
        
        for i, r in enumerate(raw_reviews[:6]):
            bid = f"review_{uuid.uuid4().hex[:8]}"
            self.reviews_order.append(bid)

            headline = r.get('review_headline', '')
            body = r.get('review_body', '')
            author = r.get('author_info', '')
            stars = r.get("stars", "★★★★★")

            review_html = f"<p><strong>{headline}</strong></p><p>{body}</p><p><small>{author}</small></p>"

            self.reviews_blocks[bid] = {
                "type": "column",
                "settings": {
                    "title": stars,
                    "text": review_html,
                    "link_label": "",
                    "link": ""
                }
            }

        # --- COMPARISON ---
        self.comparison_data = {}
        comp_ids = ["testimonial_dPRTJq", "testimonial_EzR6nx"]
        raw_comp = ai_content.get("NEW_THEME_COMPARISON_LIST", [])
        for i, c in enumerate(raw_comp[:2]):
            caption = c.get("caption", "Before/After")
            heading = c.get("testimonial_text", "Great result")
            author = c.get("author_info", "Verified")

            self.comparison_data[comp_ids[i]] = {
                "type": "testimonial",
                "settings": {
                    "caption": caption,
                    "heading": heading,
                    "text": f"<p><strong>{caption}</strong><br/>— <em>{author}</em></p>"
                }
            }

        # --- FAQ ---
        self.faq_data = {}
        faq_ids = ["collapsible_row_1", "collapsible_row_2", "collapsible_row_3", "collapsible_row_4"]
        raw_faq = ai_content.get("NEW_THEME_FAQ_LIST", [])
        for i, f in enumerate(raw_faq[:4]):
            self.faq_data[faq_ids[i]] = {
                "type": "collapsible_row",
                "settings": {
                    "heading": f.get("question", "FAQ"),
                    "row_content": f"<p>{f.get('answer', 'Answer')}</p>"
                }
            }

    def cleanup_placeholders(self, content: str) -> str:
        content = re.sub(r'NEW_THEME_[A-Z0-9_]+', '', content)
        content = re.sub(r'NEW_[A-Z0-9_]+_CONTENT', '', content)
        return content

    def escape_json_string(self, text: str) -> str:
        if not text:
            return ""
        text_str = str(text).strip()
        if text_str.startswith('"') and text_str.endswith('"') and len(text_str) > 1:
            text_str = text_str[1:-1]
        return text_str.replace('\\', '\\\\').replace('"', '\\"')

    def process_notebook_logic(self, workspace_path: str, ai_content: dict, images_map: dict, main_color: str, brand_name: str, product_handle:str):
        self.prepare_data(ai_content)

        f_index = os.path.join(workspace_path, "templates", "index.json")
        f_settings = os.path.join(workspace_path, "config", "settings_data.json")
        f_product = os.path.join(workspace_path, "templates", "product.json")
        f_footer = os.path.join(workspace_path, "sections", "footer-group.json")
        f_contact = os.path.join(workspace_path, "templates", "page.contact.json")

        def apply_safe_replacements(content, keys_list):
            for k in keys_list:
                raw_val = ai_content.get(k, "")
                safe_val = self.escape_json_string(raw_val)
                content = content.replace(k, safe_val)
            return content

        # 1. SETTINGS
        if os.path.exists(f_settings):
            with open(f_settings, 'r') as f: content = f.read()
            content = content.replace("NEW_THEME_PRIMARY_COLOR", main_color)
            content = content.replace("NEW_THEME_BRAND_NAME", self.escape_json_string(brand_name))

            for k, v in ai_content.items():
                if k.startswith("NEW_THEME_COLOR_SCHEME"):
                    content = content.replace(k, str(v))

            misc_keys = ["NEW_THEME_SECONDARY_COLOR", "NEW_THEME_SECTION1_HEADING", "NEW_THEME_SECTION1_DESCRIPTION",
                      "NEW_THEME_MAIN_TITLE_HERO_SLOGAN", "NEW_THEME_SECTION2_HEADING", "NEW_THEME_SECTION2_DESCRIPTION"]
            
            content = apply_safe_replacements(content, misc_keys)
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

            blocks_json = json.dumps(self.reviews_blocks, ensure_ascii=False)
            pattern_blocks = r'"blocks"\s*:\s*"NEW_THEME_MULTICOLUMN_REVIEWS_BLOCKS"'
            content = re.sub(pattern_blocks, lambda m: f'"blocks": {blocks_json}', content)

            order_json = json.dumps(self.reviews_order, ensure_ascii=False)
            pattern_order = r'"block_order"\s*:\s*"NEW_THEME_MULTICOLUMN_REVIEWS_BLOCK_ORDER"'
            content = re.sub(pattern_order, lambda m: f'"block_order": {order_json}', content)

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
                "NEW_THEME_HELP_SECTION_HEADLINE", "NEW_THEME_HELP_SECTION_SUBHEADING",
                "NEW_BRAND_SLOGAN_CONTENT", "NEW_PRODUCT_BLURB_CONTENT", "NEW_CTA_HERO_BUTTON_CONTENT",
                "NEW_PRODUCT_DESCRIPTION_1_CONTENT", "NEW_PRODUCT_HEADING_1_CONTENT", "NEW_SECOND_SLOGAN_CONTENT",
                "NEW_NEED_HELP_CONTENT", "NEW_OUR_TEAM_IS_HERE_CONTENT", "NEW_CONTACT_US_BUTTON_CONTENT",
                "NEW_FREE_SHIPPING_TEXT_CONTENT", "NEW_WATCH_DEMONSTRATION_CONTENT", "NEW_SEE_COLLECTION_BUTTON_CONTENT",
                "NEW_GET_THIS_OFFER_BUTTON_CONTENT", "NEW_EXCELLENT_CONTENT", "NEW_PRODUCT_REVIEWS_HEADING_CONTENT",
                "NEW_RATED_BY_CONTENT", "NEW_REVIEW_1_HOME_CONTENT", "NEW_REVIEW_2_HOME_CONTENT",
                "NEW_REVIEW_3_HOME_CONTENT", "NEW_REVIEW_4_HOME_CONTENT"
            ]
            content = apply_safe_replacements(content, text_keys)

            hero_btn = self.escape_json_string(ai_content.get("NEW_THEME_SUBTITLE_BUTTON_TEXT", "Shop Now"))
            content = content.replace("HERO_BUTTON_TEXT", hero_btn)

            content = self.cleanup_placeholders(content)
            with open(f_index, 'w') as f: f.write(content)

        # 3. PRODUCT
        if os.path.exists(f_product):
            with open(f_product, 'r') as f: content = f.read()
            content = content.replace("NEW_THEME_FAQ_DATA", json.dumps(self.faq_data, ensure_ascii=False))

            # --- PRE-PROCESS: Standard Replacements ---
            p_keys = [
                "NEW_THEME_WHAT_MAKES_OUR_PRODUCT_UNIQUE_TITLE", "NEW_THEME_PRODUCT_PAGE_IT1_TITLE",
                "NEW_THEME_PRODUCT_PAGE_IT1_TEXT", "NEW_THEME_PRODUCT_PAGE_IT2_TITLE",
                "NEW_THEME_PRODUCT_PAGE_IT2_TEXT", "NEW_THEME_TABLE_COMPARISON_WHY",
                "NEW_THEME_VIDEO_TEXT_HEADING_PRODUCT_PAGE", "NEW_THEME_VIDEO_TEXT_TEXT_PRODUCT_PAGE",
                "NEW_THEME_PRODUCT_BLURB_CONTENT", "NEW_THEME_BENEFITS_PRODUCT_CONTENT",
                "NEW_PEOPLE_PURCHASED_CONTENT", "NEW_WANT_IT_BY_CONTENT", "NEW_ORDER_WITHIN_CONTENT",
                "NEW_FREE_SHIPPING_CONTENT_ST", "NEW_REVIEWS_NUMBER_CONTENT", "NEW_SAFE_SECURE_PAYEMENT_CONTENT",
                "NEW_FREE_SHIPPING_GLOBLY_CONTENT", "NEW_FDA_CLEARED_CONTENT", "NEW_TRY_IT_RISK_FREE_FOR_90_DAYS_CONTENT",
                "NEW_LOOK_AT_OTHERS_CONTENT", "NEW_CLAIM_OFFER_CONTENT", "NEW_REAL_OFFER_PEOPLE_CONTENT",
                "NEW_HIGHLIGHT_PRODUCT_FEATURES_CONTENT", "NEW_WHY_CHOOSE_US_CONTENT", "NEW_WHY_CHOOSE_US_BRAND_TEXT_CONTENT",
                "NEW_THEME_FAQ_HEADING_1", "NEW_THEME_FAQ_CONTENT_1", "NEW_THEME_FAQ_HEADING_2", "NEW_THEME_FAQ_CONTENT_2",
                "NEW_THEME_FAQ_HEADING_3", "NEW_THEME_FAQ_CONTENT_3", "NEW_THEME_FAQ_HEADING_4", "NEW_THEME_FAQ_CONTENT_4",
                "NEW_FAQs_CONTENT", "NEW_CUSTOMER_QA_CONTENT", "NEW_758_PURCHASED_CONTENT", "NEW_HEADING_PRODUCT_NAME_CONTENT",
                "NEW_30DAY_GUARANTEE_CONTENT", "NEW_WHAT_OUR_CUSTOMERS_SAY_CONTENT", "NEW_PARAGRAPH_PRODUCT_TEXT_VIDEO",
                "NEW_HEADING_PRODUCT_TEXT_VIDEO", "NEW_CUSTOMER_SERVICE_TEXT_CONTENT", "NEW_CUSTOMER_SERVICE_PARAGRAPH_CONTENT",
                "PRODUCT_SOLDOUT_TEXT", "PRODUCT_UNTRACKED_TEXT", "PRODUCT_LOW_ONE_TEXT", "PRODUCT_LOW_MANY_TEXT",
                "PRODUCT_NORMAL_TEXT", "PRODUCT_SHARE_LABEL", "PRODUCT_OTHERS_LABEL", "PRODUCT_RELATED_HEADING"
            ]
            content = apply_safe_replacements(content, p_keys)
            content = self.cleanup_placeholders(content)

            # --- POST-PROCESS: Surgical Replacement for Table Rows & Header ---
            # This overwrites the hardcoded Drone text
            try:
                data = json.loads(content)
                if "sections" in data:
                    for section_id, section in data["sections"].items():
                        # Find the Comparison Table Section
                        # Usually identifies by type or specific blocks
                        if section.get("type") == "comparison-table" or "comparison" in section_id:
                            
                            # 1. Update Header (Fixing "dycom-test-01")
                            if "settings" in section:
                                if "us_heading" in section["settings"]:
                                    section["settings"]["us_heading"] = self.escape_json_string(brand_name)
                                if "product_heading" in section["settings"]:
                                    section["settings"]["product_heading"] = self.escape_json_string(brand_name)

                            # 2. Update Rows (Fixing Drone Text)
                            if "blocks" in section:
                                # Map IDs to keys. NOTE: These IDs must match your base template.
                                row_map = {
                                    "row_gGix3c": "NEW_PROS_1_CONTENT",
                                    "row_GD4keD": "NEW_PROS_2_CONTENT",
                                    "row_RjxJwy": "NEW_PROS_3_CONTENT",
                                    "row_UCwzEV": "NEW_PROS_4_CONTENT",
                                    "row_WrB3M7": "NEW_PROS_5_CONTENT"
                                }
                                for bid, key in row_map.items():
                                    if bid in section["blocks"]:
                                        new_text = ai_content.get(key, "")
                                        if new_text:
                                            # Update "benefit" or "text" depending on schema
                                            if "settings" in section["blocks"][bid]:
                                                section["blocks"][bid]["settings"]["benefit"] = self.escape_json_string(new_text)

                content = json.dumps(data, indent=2, ensure_ascii=False)
            except Exception as e:
                print(f"   ⚠️ Error during surgical JSON update: {e}")

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
            content = apply_safe_replacements(content, f_keys)
            content = self.cleanup_placeholders(content)
            with open(f_footer, 'w') as f: f.write(content)

        # 5. CONTACT
        if os.path.exists(f_contact):
            with open(f_contact, 'r') as f: content = f.read()
            c_keys = ["CONTACT_US_PAGE_HEADING", "CONTACT_US_BANNER_SUBHEADING", "GET_IN_TOUCH_TRANSLATION",
                      "CONTACT_US_GET_IN_TOUCH_DESCRIPTION", "SUMMER_SALE_TRANSLATION", "SALE_BANNER_SUBHEADING",
                      "SHOP_SALE_NOW", "BUNDLE_AND_SALE_TRANSLATION", "BUNDLE_BANNER_SUBHEADING",
                      "SHOP_BUNDLE_TRANSLATION"]
            content = apply_safe_replacements(content, c_keys)
            content = content.replace("NEW_CONTACT_PAGE_IMAGE_BANNER", images_map.get("NEW_THEME_HERO_BANNER", ""))

            content = self.cleanup_placeholders(content)
            with open(f_contact, 'w') as f: f.write(content)

    def zip_theme(self, workspace_path: str) -> str:
        zip_base = workspace_path
        shutil.make_archive(zip_base, 'zip', workspace_path)
        return f"{zip_base}.zip"