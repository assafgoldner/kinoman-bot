"""
Configuration — environment variables and constants.
"""

import os

# ── WhatsApp Cloud API ──────────────────────────────────────────────
WHATSAPP_TOKEN = os.environ.get("WHATSAPP_TOKEN", "")
PHONE_NUMBER_ID = os.environ.get("PHONE_NUMBER_ID", "")
VERIFY_TOKEN = os.environ.get("VERIFY_TOKEN", "")
WHATSAPP_API_VERSION = "v21.0"
WHATSAPP_API_URL = (
    f"https://graph.facebook.com/{WHATSAPP_API_VERSION}/{PHONE_NUMBER_ID}/messages"
)
WHATSAPP_MAX_MESSAGE_LENGTH = 4000
WHATSAPP_MAX_BUTTON_TITLE = 20
WHATSAPP_MAX_BUTTONS = 3
WHATSAPP_MAX_LIST_ITEMS = 10

# ── Movie APIs ─────────────────────────────────────────────────────
TMDB_API_KEY = os.environ.get("TMDB_API_KEY", "")
OMDB_API_KEY = os.environ.get("OMDB_API_KEY", "")

# ── OpenRouter (for plot-based identification) ─────────────────────
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY", "")
