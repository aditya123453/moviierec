"""
Configuration — works on Replit, local, and Streamlit Cloud
"""

import os
from dotenv import load_dotenv

load_dotenv()

# ── TMDB API Key ──
# Priority: Streamlit Cloud secrets → env var → hardcoded fallback
def _get_tmdb_key():
    try:
        import streamlit as st
        key = st.secrets.get("TMDB_API_KEY", "")
        if key:
            return key
    except Exception:
        pass
    return os.getenv("TMDB_API_KEY", "8265bd1679663a7ea12ac168da84d2e8")

TMDB_API_KEY   = _get_tmdb_key()
TMDB_BASE_URL  = "https://api.themoviedb.org/3"
TMDB_IMAGE_BASE = "https://image.tmdb.org/t/p"

# ── Timeouts / cache ──
API_TIMEOUT = int(os.getenv("API_TIMEOUT", 5))
CACHE_TTL   = int(os.getenv("CACHE_TTL", 86400))

# ── Model file paths ──
MODEL_PATHS = {
    "movies_list": "movies_list.pkl",
    "vectorizer":  "vectorizer.pkl",
}

# ── UI settings ──
APP_TITLE             = "CINEMAGIC | Hybrid AI Movie Recommender"
APP_ICON              = "🎬"
RECOMMENDATIONS_COUNT = 6
TRENDING_COUNT        = 12
CHAT_HISTORY_DISPLAY  = 3
ENABLE_TRAILER        = True
ENABLE_EXTERNAL_SEARCH = True
ENABLE_COLLABORATIVE_FILTERING = False

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
