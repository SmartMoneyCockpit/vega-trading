# src/pages/45_News_Updates.py
import os, streamlit as st
from pathlib import Path

# 🔹 MUST BE FIRST STREAMLIT COMMAND
st.set_page_config(page_title="News Updates", page_icon="📰", layout="wide")

# ---- SILENT SECRET HANDLER (NO st.secrets ACCESS) ----
def get_secret(name: str, default=None):
    """Environment-first; does NOT touch st.secrets to avoid Streamlit warnings."""
    val = os.getenv(name, None)
    if val is not None:
        return val
    # No env var; return default silently (avoids Streamlit's 'No secrets found' banners)
    return default

ADMIN_KEY = get_secret("VEGA_ADMIN_KEY", None)
NEWS_ROOT = Path(get_secret("VEGA_NEWS_PATH", "data/news"))
(NEWS_ROOT / "posts").mkdir(parents=True, exist_ok=True)

st.title("📰 News Updates")

if not ADMIN_KEY:
    # Soft notice (not an error): page still works read-only
    st.info("No `VEGA_ADMIN_KEY` in environment; page is in read-only mode.")

# ---- Load recent news posts ----
posts_dir = NEWS_ROOT / "posts"
posts = sorted(posts_dir.glob("*.md"), reverse=True)
if not posts:
    st.info("No news posts found yet.")
else:
    st.success(f"Loaded {len(posts)} posts from {posts_dir}")
    for p in posts[:30]:
        with open(p, "r", encoding="utf-8") as f:
            st.markdown(f.read())
        st.divider()
