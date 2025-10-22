# src/pages/00_Home.py
import streamlit as st
from pathlib import Path

st.set_page_config(page_title="Home", page_icon="🏠", layout="wide")
st.title("🏠 Home")

# Use only make_light_badge to avoid ImportError on compute_status
try:
    from src.engine.smart_money import make_light_badge  # compute_status optional
except Exception as e:
    st.error(f"Smart Money import error: {e}")
    make_light_badge = lambda region: "🟡 Wait / Selective • Score 0.50 • Breadth 50% • RS 50% • Vol 2.00"

st.success(make_light_badge("USA"))

st.markdown("""
Welcome to Vega. Use the left sidebar to open a region dashboard and run scanners.  
Key pages:
- **USA / Canada / Mexico / LATAM** Text Dashboards (charts + local scans)
- **Daily Digest RunNow** and **Morning Post RunNow** for quick News posts
- **News Updates** to view recent digests
""")
