import requests
import json
import time
import os

class ShopifyClient:
    def __init__(self, shop_url: str, access_token: str):
        self.shop_url = shop_url.replace("https://", "").replace("/", "")
        self.access_token = access_token
        self.rest_url = f"https://{self.shop_url}/admin/api/2025-01"
        self.graphql_url = f"https://{self.shop_url}/admin/api/2025-01/graphql.json"
        self.headers = {
            "X-Shopify-Access-Token": self.access_token,
            "Content-Type": "application/json"
        }

    def upload_local_file(self, file_path: str, mime_type: str = "application/zip") -> str:
        """Uploads local file (ZIP) to Shopify Staged Uploads."""
        if not os.path.exists(file_path):
            print(f"❌ File not found: {file_path}")
            return None

        filename = os.path.basename(file_path)
        file_size = str(os.path.getsize(file_path))

        # 1. Request Target
        mutation = """
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
                "resource": "FILE",
                "fileSize": file_size
            }]
        }
        
        resp = requests.post(self.graphql_url, headers=self.headers, json={"query": mutation, "variables": variables})
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
        if "policy" in param_dict or "key" in param_dict:
            with open(file_path, "rb") as f:
                files = {"file": (filename, f, mime_type)}
                upload_resp = requests.post(upload_url, data=param_dict, files=files)
        else:
            headers = {"Content-Type": mime_type}
            for p in parameters:
                headers[p["name"]] = p["value"]
            with open(file_path, "rb") as f:
                upload_resp = requests.put(upload_url, data=f, headers=headers)
        
        if upload_resp.status_code not in [200, 201, 204]:
            print(f"❌ Bucket Upload Failed: {upload_resp.status_code}")
            return None

        # 3. Register File
        mutation_create = """
        mutation fileCreate($files: [FileCreateInput!]!) {
          fileCreate(files: $files) {
            files { id }
          }
        }
        """
        variables_create = {
            "files": [{"originalSource": resource_url, "contentType": "FILE", "alt": filename}]
        }
        
        resp = requests.post(self.graphql_url, headers=self.headers, json={"query": mutation_create, "variables": variables_create})
        create_data = resp.json()
        
        try:
            file_id = create_data["data"]["fileCreate"]["files"][0]["id"]
        except Exception:
            print(f"❌ File Register Failed: {create_data}")
            return None

        # 4. Poll
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
          }
        }
        """
        for _ in range(30):
            resp = requests.post(self.graphql_url, headers=self.headers, json={"query": query, "variables": {"id": file_id}})
            data = resp.json()
            node = data.get("data", {}).get("node")
            
            if node and node["fileStatus"] == "READY":
                return node["url"]
            elif node and node["fileStatus"] == "FAILED":
                return None
            time.sleep(2)
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
        
        query = """
        query ($id: ID!) {
          node(id: $id) {
            ... on MediaImage {
              id
              fileStatus
              image { url }
            }
          }
        }
        """
        for _ in range(15):
            resp = requests.post(self.graphql_url, headers=self.headers, json={"query": query, "variables": {"id": file_id}})
            node = resp.json().get("data", {}).get("node")
            if node and node["fileStatus"] == "READY":
                filename_part = node["image"]["url"].split('/')[-1].split('?')[0]
                return f"shopify://shop_images/{filename_part}"
            time.sleep(2)
        return None

    def upload_theme(self, zip_url: str, theme_name: str) -> str:
        endpoint = f"{self.rest_url}/themes.json"
        payload = {
            "theme": {
                "name": theme_name,
                "src": zip_url,
                "role": "unpublished"
            }
        }
        response = requests.post(endpoint, json=payload, headers=self.headers)
        if response.status_code == 201:
            return response.json()["theme"]["id"]
        print(f"❌ Theme Upload Error: {response.text}")
        return None

    def publish_theme(self, theme_id: str):
        """Waits for theme to process, then publishes it."""
        
        # 1. Wait for Processing
        print(f"⏳ Waiting for Theme {theme_id} to process...")
        endpoint_get = f"{self.rest_url}/themes/{theme_id}.json"
        
        for _ in range(20):
            resp = requests.get(endpoint_get, headers=self.headers)
            if resp.status_code == 200:
                theme_data = resp.json().get("theme", {})
                if not theme_data.get("processing", True):
                    # Processing is False (Done)
                    break
            time.sleep(3)
        
        # 2. Publish
        endpoint_put = f"{self.rest_url}/themes/{theme_id}.json"
        payload = {"theme": {"role": "main"}}
        resp = requests.put(endpoint_put, json=payload, headers=self.headers)
        
        if resp.status_code == 200:
            print(f"✅ Theme {theme_id} Published Successfully")
        else:
            print(f"❌ Failed to Publish Theme: {resp.status_code} - {resp.text}")

    def create_product(self, title: str, html_body: str, image_urls: list, brand: str):
        endpoint = f"{self.rest_url}/products.json"
        images = [{"src": url} for url in image_urls] if image_urls else []
        
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