import requests
import json
import time
import os

class ShopifyClient:
    def __init__(self, shop_url: str, access_token: str):
        # Clean URL
        if not shop_url:
            raise ValueError("Shopify Store URL is required")
        self.shop_url = shop_url.replace("https://", "").replace("/", "")
        self.access_token = access_token
        self.rest_url = f"https://{self.shop_url}/admin/api/2025-01"
        self.graphql_url = f"https://{self.shop_url}/admin/api/2025-01/graphql.json"
        self.headers = {
            "X-Shopify-Access-Token": self.access_token,
            "Content-Type": "application/json"
        }

    def upload_local_file(self, file_path: str, mime_type: str = "application/zip", resource: str = "FILE") -> str:
        """
        Uploads a local file to Shopify Staged Uploads. 
        Returns the public URL (target) that Shopify can download from.
        This bypasses the need for Ngrok.
        """
        if not os.path.exists(file_path):
            print(f"❌ File not found: {file_path}")
            return None

        filename = os.path.basename(file_path)
        file_size = str(os.path.getsize(file_path))

        # 1. Request Target
        query = """
        mutation stagedUploadsCreate($input: [StagedUploadInput!]!) {
          stagedUploadsCreate(input: $input) {
            stagedTargets {
              url
              resourceUrl
              parameters { name value }
            }
            userErrors { field message }
          }
        }
        """
        variables = {
            "input": [{
                "filename": filename,
                "mimeType": mime_type,
                "resource": resource,
                "fileSize": file_size
            }]
        }
        
        resp = requests.post(self.graphql_url, headers=self.headers, json={"query": query, "variables": variables})
        data = resp.json()
        
        try:
            if "errors" in data:
                print(f"❌ GraphQL Error: {data['errors']}")
                return None
            target = data["data"]["stagedUploadsCreate"]["stagedTargets"][0]
            upload_url = target["url"]
            resource_url = target["resourceUrl"]
            parameters = target.get("parameters", [])
        except Exception:
            print(f"❌ Staged Upload Error: {data}")
            return None

        # 2. Upload to Bucket
        param_dict = {p["name"]: p["value"] for p in parameters}
        
        # Check if we need POST (Multipart) or PUT (Raw)
        try:
            with open(file_path, "rb") as f:
                if "policy" in param_dict or "key" in param_dict:
                    # POST upload (usually AWS style)
                    files = {"file": (filename, f, mime_type)}
                    upload_resp = requests.post(upload_url, data=param_dict, files=files)
                else:
                    # PUT upload (GCS style)
                    headers = {"Content-Type": mime_type}
                    for p in parameters:
                        headers[p["name"]] = p["value"]
                    upload_resp = requests.put(upload_url, data=f, headers=headers)
        except Exception as e:
            print(f"❌ Upload Connection Error: {e}")
            return None
        
        if upload_resp.status_code not in [200, 201, 204]:
            print(f"❌ Bucket Upload Failed: {upload_resp.status_code} - {upload_resp.text}")
            return None

        # 3. Register File in Shopify (Only if it's a generic FILE or IMAGE, Videos are handled differently)
        # If resource is VIDEO, we usually wait to create the video object specifically.
        # But for Theme ZIPs (resource=FILE), we create a GenericFile.
        
        if resource == "VIDEO":
            # For videos, we return the resource_url so upload_video_to_shopify can create the specific Video object
            return resource_url

        mutation_create = """
        mutation fileCreate($files: [FileCreateInput!]!) {
          fileCreate(files: $files) {
            files { id }
            userErrors { field message }
          }
        }
        """
        variables_create = {
            "files": [{"originalSource": resource_url, "contentType": resource, "alt": filename}]
        }
        
        resp = requests.post(self.graphql_url, headers=self.headers, json={"query": mutation_create, "variables": variables_create})
        create_data = resp.json()
        
        try:
            files_list = create_data.get("data", {}).get("fileCreate", {}).get("files", [])
            if not files_list:
                print(f"❌ File Register Failed: {create_data}")
                return None
            file_id = files_list[0]["id"]
        except Exception as e:
            print(f"❌ Error parsing file ID: {e}")
            return None

        # 4. Poll for Readiness
        return self._poll_for_file_url(file_id)

    def _poll_for_file_url(self, file_id: str) -> str:
        query = """
        query ($id: ID!) {
          node(id: $id) {
            ... on GenericFile {
              id
              fileStatus
              url
            }
            ... on MediaImage {
              id
              fileStatus
              image { url }
            }
          }
        }
        """
        for _ in range(30):
            resp = requests.post(self.graphql_url, headers=self.headers, json={"query": query, "variables": {"id": file_id}})
            data = resp.json()
            node = data.get("data", {}).get("node")
            
            if node:
                status = node.get("fileStatus")
                if status == "READY":
                    # Handle both GenericFile and MediaImage
                    if "url" in node: return node["url"]
                    if "image" in node: return node["image"]["url"]
                elif status == "FAILED":
                    return None
            time.sleep(2)
        return None

    def upload_video_to_shopify(self, video_path: str, alt_text: str = "Product video") -> str:
        """
        Special wrapper for video uploads. 
        1. Uploads file to bucket.
        2. Creates 'VIDEO' resource in Shopify.
        3. Polls for CDN URL.
        """
        # Step 1 & 2: Upload to bucket, get the resource URL back (not the final CDN url yet)
        resource_url = self.upload_local_file(video_path, mime_type="video/mp4", resource="VIDEO")
        if not resource_url:
            return None

        # Step 3: Create Video Object
        mutation = """
        mutation fileCreate($files: [FileCreateInput!]!) {
          fileCreate(files: $files) {
            files { id fileStatus }
            userErrors { field message }
          }
        }
        """
        variables = {
            "files": [{
                "originalSource": resource_url,
                "contentType": "VIDEO",
                "alt": alt_text
            }]
        }
        
        resp = requests.post(self.graphql_url, headers=self.headers, json={"query": mutation, "variables": variables})
        data = resp.json()
        
        try:
            video_id = data["data"]["fileCreate"]["files"][0]["id"]
        except Exception:
            print(f"❌ Video Create Failed: {data}")
            return None

        # Step 4: Poll Video Specific Query
        query_vid = """
        query ($id: ID!) {
          node(id: $id) {
            ... on Video {
              id
              fileStatus
              sources { url }
            }
          }
        }
        """
        for _ in range(30):
            resp = requests.post(self.graphql_url, headers=self.headers, json={"query": query_vid, "variables": {"id": video_id}})
            node = resp.json().get("data", {}).get("node")
            if node and node.get("fileStatus") == "READY":
                sources = node.get("sources", [])
                if sources:
                    return sources[0]["url"]
            time.sleep(3)
        
        return None

    def upload_image_from_url(self, image_url: str, filename: str) -> str:
        mutation = """
        mutation fileCreate($files: [FileCreateInput!]!) {
          fileCreate(files: $files) {
            files { id }
          }
        }
        """
        variables = {"files": [{"originalSource": image_url, "contentType": "IMAGE", "alt": filename}]}
        response = requests.post(self.graphql_url, headers=self.headers, json={"query": mutation, "variables": variables})
        data = response.json()
        
        try:
            file_id = data["data"]["fileCreate"]["files"][0]["id"]
        except Exception:
            return None
        
        # Poll using internal helper
        cdn_url = self._poll_for_file_url(file_id)
        if cdn_url:
            # Convert to internal shopify:// schema for theme usage
            filename_part = cdn_url.split('/')[-1].split('?')[0]
            return f"shopify://shop_images/{filename_part}"
        return None

    def upload_theme(self, src_url: str, theme_name: str) -> str:
        """
        Creates a theme using a source URL.
        When using upload_local_file, src_url is the Shopify-hosted temporary URL.
        """
        endpoint = f"{self.rest_url}/themes.json"
        payload = {
            "theme": {
                "name": theme_name,
                "src": src_url,
                "role": "unpublished"
            }
        }
        response = requests.post(endpoint, json=payload, headers=self.headers)
        if response.status_code == 201:
            return response.json()["theme"]["id"]
        
        print(f"❌ Theme Upload Error: {response.status_code} {response.text}")
        return None

    def publish_theme(self, theme_id: str):
        print(f"⏳ Waiting for Theme {theme_id} to process...")
        endpoint_get = f"{self.rest_url}/themes/{theme_id}.json"
        
        # Wait for processing
        for _ in range(20):
            resp = requests.get(endpoint_get, headers=self.headers)
            if resp.status_code == 200:
                theme_data = resp.json().get("theme", {})
                if not theme_data.get("processing", True):
                    break
            time.sleep(3)
        
        # Publish
        endpoint_put = f"{self.rest_url}/themes/{theme_id}.json"
        payload = {"theme": {"role": "main"}}
        resp = requests.put(endpoint_put, json=payload, headers=self.headers)
        
        if resp.status_code == 200:
            print(f"✅ Theme {theme_id} Published Successfully")
        else:
            print(f"❌ Failed to Publish Theme: {resp.status_code} - {resp.text}")

    def create_product(self, title: str, html_body: str, image_urls: list, brand: str):
        endpoint = f"{self.rest_url}/products.json"
        # Ensure images are list of dicts
        images = [{"src": url} for url in image_urls if url] if image_urls else []
        
        payload = {
            "product": {
                "title": title,
                "body_html": html_body,
                "vendor": brand,
                "status": "active",
                "images": images,
                "variants": [{"price": "29.99", "inventory_management": "shopify", "inventory_quantity": 100}]
            }
        }
        response = requests.post(endpoint, json=payload, headers=self.headers)
        if response.status_code == 201:
            return response.json()["product"]
        print(f"❌ Product Creation Failed: {response.text}")
        return None

    def create_page(self, title: str, html_body: str) -> str:
        endpoint = f"{self.rest_url}/pages.json"
        payload = {
            "page": {
                "title": title,
                "body_html": html_body,
                "status": "active"
            }
        }
        response = requests.post(endpoint, json=payload, headers=self.headers)
        if response.status_code == 201:
            return response.json()["page"]["id"]
        return None

    def add_page_to_menu(self, page_id: str, page_title: str, menu_handle: str = "main-menu"):
        endpoint_get = f"{self.rest_url}/menus.json"
        resp = requests.get(endpoint_get, headers=self.headers)
        if resp.status_code != 200: return
        
        menus = resp.json().get("menus", [])
        menu_id = next((m["id"] for m in menus if m["handle"] == menu_handle), None)
        if not menu_id: return

        endpoint_post = f"{self.rest_url}/menus/{menu_id}/items.json"
        payload = {
            "menu_item": {
                "name": page_title,
                "subject_id": page_id,
                "subject_type": "page"
            }
        }
        requests.post(endpoint_post, json=payload, headers=self.headers)

    def enable_store_language(self, language_code: str):
        """Enables and publishes a language (locale) on the store."""
        print(f"🌐 Enabling language: {language_code}")
        
        # 1. Enable
        query_enable = """
        mutation shopLocaleEnable($locale: String!) {
            shopLocaleEnable(locale: $locale) {
                shopLocale { locale name }
                userErrors { field message }
            }
        }
        """
        self._graphql_request(query_enable, {'locale': language_code})

        # 2. Publish
        query_publish = """
        mutation shopLocaleUpdate($locale: String!, $shopLocale: ShopLocaleInput!) {
            shopLocaleUpdate(locale: $locale, shopLocale: $shopLocale) {
                shopLocale { locale published }
                userErrors { field message }
            }
        }
        """
        self._graphql_request(query_publish, {
            'locale': language_code,
            'shopLocale': {'published': True}
        })

    def _graphql_request(self, query, variables=None):
        resp = requests.post(self.graphql_url, headers=self.headers, json={'query': query, 'variables': variables or {}})
        return resp.json()