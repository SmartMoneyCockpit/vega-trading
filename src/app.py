# src/app.py
import os
from pathlib import Path
import streamlit as st

# Uses your existing helpers (leave as-is)
from utils import title_with_flag, ensure_token_notice

# ──────────────────────────────────────────────────────────────────────────────
#  Vega Smart Money Cockpit – Home
#   - Removed modules: Country Hub, EODHD Scanner, Relative Strength Momentum
#     Dashboard, A+ Digest Builder, Scanner Unified, Daily Digest Scanner,
#     Morning Post Review, Breadth Grid, Marker, TradingView Charts module.
#   - Kept modules: Country Dashboards (USA/Canada/Mexico), Risk & Return
#     Scoring, Sector Momentum Tiles, Defensive Overlay Status, System Status.
# ──────────────────────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="Vega Cockpit – Home",
    page_icon="🧭",
    layout="wide",
)

title_with_flag("Vega Cockpit – Home")
ensure_token_notice()

st.success(
    "✅ Clean rebuild: redundant global modules removed. "
    "Regional dashboards and core system tools are active."
)

# Where your Streamlit pages live (adjust if your structure differs)
PAGES_DIR = Path(__file__).resolve().parent / "pages"

def find_first_existing(candidates):
    """Return the first existing file path (string) from a list of candidate relative paths."""
    for rel in candidates:
        p = PAGES_DIR / rel
        if p.exists():
            # st.page_link expects a path relative to repo root (or the pages/ file)
            return f"pages/{rel}"
    return None

# Define ONLY the pages you want to expose
# Add multiple candidates to be robust to numbering/name changes
PAGES_TO_KEEP = {
    "🇨🇦 Canada Text Dashboard": [
        "Canada_Text_Dashboard.py",
        "02_Canada_Text_Dashboard.py",
        "20_Canada_Text_Dashboard.py",
        "Canada.py",
    ],
    "🇲🇽 Mexico Text Dashboard": [
        "Mexico_Text_Dashboard.py",
        "03_Mexico_Text_Dashboard.py",
        "21_Mexico_Text_Dashboard.py",
        "Mexico.py",
    ],
    "🇺🇸 United States Text Dashboard": [
        "United_States_Text_Dashboard.py",
        "USA_Text_Dashboard.py",
        "01_USA_Text_Dashboard.py",
        "United_States.py",
        "USA.py",
    ],
    "📊 Risk & Return Scoring": [
        "40_Risk_Return_Scoring.py",
        "Risk_Return_Scoring.py",
        "Risk_and_Return_Scoring.py",
    ],
    "🧭 Sector Momentum Tiles": [
        "Sector_Momentum_Tiles.py",
        "30_Sector_Momentum_Tiles.py",
        "SectorTiles.py",
    ],
    "🛡️ Defensive Overlay Status": [
        "Defensive_Overlay_Status.py",
        "35_Defensive_Overlay_Status.py",
        "DefensiveOverlay.py",
    ],
    "⚙️ System Status": [
        "System_Status.py",
        "99_System_Status.py",
        "SystemStatus.py",
    ],
}

# Build a map of label -> resolved path (only if the file exists)
resolved_pages = {}
for label, candidates in PAGES_TO_KEEP.items():
    path = find_first_existing(candidates)
    if path:
        resolved_pages[label] = path

# Sidebar navigation (only renders existing pages)
st.sidebar.markdown("## 📂 Navigation")
if resolved_pages:
    for label, path in resolved_pages.items():
        st.sidebar.page_link(path, label=label)
else:
    st.sidebar.info("No pages found yet in `src/pages/`. Double-check filenames.")

# Quick Links section on the home screen
st.markdown("### ⚡ Quick Links")
if resolved_pages:
    st.caption("Only links to pages that actually exist are shown.")
    for label, path in resolved_pages.items():
        # Use page_link in body too for consistency
        st.page_link(path, label=label)
else:
    st.warning(
        "I couldn’t find any of the kept pages under `src/pages/`. "
        "Verify the filenames (e.g., `USA_Text_Dashboard.py`, "
        "`Canada_Text_Dashboard.py`, `Mexico_Text_Dashboard.py`, "
        "`40_Risk_Return_Scoring.py`, etc.)."
    )

# Optional: small footnote
st.markdown(
    "<hr style='margin-top:2rem;margin-bottom:0.5rem'/>",
    unsafe_allow_html=True,
)
st.caption(
    "Modules removed globally: Country Hub, EODHD Scanner, Relative Strength Momentum Dashboard, "
    "A+ Digest Builder, Scanner Unified, Daily Digest Scanner, Morning Post Review, Breadth Grid, "
    "Marker, TradingView Charts."
)
