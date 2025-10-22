
import streamlit as st
from utils import title_with_flag, ensure_token_notice

st.set_page_config(page_title="Vega Cockpit — EODHD", page_icon="📈", layout="wide")

title_with_flag("Vega Cockpit — Home")
st.success("Clean rebuild: EODHD pricing + TradingView charts. IBKR removed.")
ensure_token_notice()

st.markdown("### Quick Links")
st.markdown("- Canada Text Dashboard\n- Mexico Text Dashboard\n- United States Text Dashboard\n- EODHD Scanner\n- Unified Scanner\n- TradingView Charts\n- Owners Daily Digest\n- Breadth Grid\n- Risk Return Scoring\n- Sector Momentum Tiles\n- Defensive Overlay Status\n- A+ Digest Builder\n- System Status")
