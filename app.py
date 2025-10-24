# app.py — Clean Home (no warning banners) + Quick Links
import os
import streamlit as st
from pathlib import Path

st.set_page_config(page_title="Vega Cockpit – Home", page_icon="🧭", layout="wide")
st.title("Vega Cockpit – Home")

# Success banner
st.success("Clean rebuild: redundant global modules removed. Regional dashboards and core system tools are active.")

st.markdown("### ⚡ Quick Links")
st.caption("Only links to pages that actually exist are shown.")

# Resolve candidate page paths by name (we include multiple aliases and pick the first that exists)
CANDIDATES = {
    "Owners Daily Digest": [
        "pages/90_Owners_Daily_Digest.py",
        "pages/Owners Daily Digest.py",
        "src/pages/Owners Daily Digest.py",
    ],
    "US Stock Market": ["pages/US_Stock_Market.py", "pages/10_US_Stock_Market.py", "src/pages/US_Stock_Market.py"],
    "Mexico Stock Market": ["pages/Mexico_Stock_Market.py", "src/pages/Mexico_Stock_Market.py"],
    "Canada Stock Market": ["pages/Canada_Stock_Market.py", "src/pages/Canada_Stock_Market.py"],
    "Risk Return Scoring": ["pages/40_Risk_Return_Scoring.py", "src/pages/40_Risk_Return_Scoring.py"],
    "Sector Momentum Tiles": ["pages/Sector_Momentum_Tiles.py", "src/pages/Sector_Momentum_Tiles.py"],
    "Defensive Overlay Status": ["pages/Defensive_Overlay_Status.py", "src/pages/Defensive_Overlay_Status.py"],
    "Sector Flip Alerts": ["pages/Sector_Flip_Alerts.py", "src/pages/Sector_Flip_Alerts.py"],
    "News Updates": ["pages/News_Updates.py", "src/pages/News_Updates.py"],
    "System Status": ["pages/99_System_Status.py", "src/pages/99_System_Status.py"],
}

def existing_page(paths):
    for p in paths:
        if os.path.exists(p):
            return p
    return None

# Layout: show buttons/links for those that exist
cols = st.columns(3)
i = 0
for label, candidates in CANDIDATES.items():
    target = existing_page(candidates)
    if not target:
        continue
    with cols[i % 3]:
        st.page_link(target, label=label, icon="➡️")
    i += 1

if i == 0:
    st.info("No linked pages were detected. Ensure your pages are under the `pages/` or `src/pages/` folder.")

st.divider()
st.caption("Modules removed globally: Country Hub, EODHD Scanner, Relative Strength Momentum Dashboard, "
           "A+ Digest Builder, Scanner Unified, Daily Digest Scanner, Morning Post Review, Breadth Grid, Marker, TradingView Charts.")
