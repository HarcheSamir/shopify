import os
from dotenv import load_dotenv

load_dotenv()

# Product Details (You can make these arguments in main.py later, but hardcoded for now as per notebook)
PRODUCT_TITLE = "Éclat Sublime – Crème Visage Hydratante Rose"
PRODUCT_DESCRIPTION = """
Une crème hydratante délicate, infusée d'extraits de rose et de vitamine E.
Elle nourrit intensément la peau, lisse les ridules et révèle un éclat radieux
tout en laissant une sensation soyeuse et raffinée.
"""
BRAND_NAME = "Luminelle Beauty"
EMAIL = "support@LuminelleBeauty.com"

# Theme Config
THEME_NAME = "Beauty by LuminTheme"
THEME_PRIMARY_COLOR = "#EFB7C6"
THEME_DESCRIPTION = "Élégance, douceur et raffinement inspirés de l'univers de la beauté"
THEME_MOOD = "féminin, luxueux, délicat, apaisant, raffiné"
LANGUAGE = "French"

# API Keys
SHOPIFY_STORE_URL = os.getenv("SHOPIFY_STORE_URL")
SHOPIFY_ACCESS_TOKEN = os.getenv("SHOPIFY_ACCESS_TOKEN")
IMGBB_API_KEY = os.getenv("IMGBB_API_KEY")
RUNWAY_API_KEY = os.getenv("RUNWAY_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
NGROK_TOKEN = os.getenv("NGROK_TOKEN")

RUNWAY_VERSION = "2024-11-06"
SHOP_NAME = SHOPIFY_STORE_URL.split('.')[0] if SHOPIFY_STORE_URL else ""

# Paths
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
ASSETS_DIR = os.path.join(BASE_DIR, "assets", "base-theme")
OUTPUT_DIR = os.path.join(BASE_DIR, "output")
TEMP_DIR = os.path.join(BASE_DIR, "temp_theme_build")

# Mappings
FOOTER_JSON_PATH = "sections/footer-group.json"
PRODUCT_JSON_PATH = "templates/product.json"
HOME_JSON_PATH = "templates/index.json"
SETTINGS_JSON_PATH = "config/settings_data.json"
CONTACT_JSON_PATH = "templates/page.contact.json"