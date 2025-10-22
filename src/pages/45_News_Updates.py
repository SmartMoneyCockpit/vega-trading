# src/pages/45_News_Updates.py
import os, streamlit as st
from pathlib import Path

# 🔹 MUST BE FIRST STREAMLIT COMMAND
st.set_page_config(page_title="News Updates", page_icon="📰", layout="wide")

# ---- SAFE SECRET HANDLER ----
def get_secret(name: str, default=None):
    """Read from Streamlit secrets if available; otherwise env; otherwise default."""
    try:
        return (st.secrets.get(name) if hasattr(st, "secrets") else None) or os.getenv(name, default)
    except Exception:
        return os.getenv(name, default)

ADMIN_KEY = get_secret("VEGA_ADMIN_KEY", None)
NEWS_ROOT = Path(get_secret("VEGA_NEWS_PATH", "data/news"))
(NEWS_ROOT / "posts").mkdir(parents=True, exist_ok=True)

st.title("📰 News Updates")

if not ADMIN_KEY:
    st.warning(
        "⚠️ No `VEGA_ADMIN_KEY` found. Set it in your Render environment or secrets.toml. "
        "This page is in read-only mode."
    )

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
