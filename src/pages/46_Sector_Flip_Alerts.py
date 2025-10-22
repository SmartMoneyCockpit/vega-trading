
import streamlit as st
from utils import title_with_flag

title_with_flag("Sector Flip Alerts", "")
st.write("""
**Rules (default):**
- Flip if sector ETF’s **relative return** vs its country index changes sign and exceeds **±0.6%** for ≥15 minutes; OR
- 15‑min momentum cross (EMA(10) – EMA(30) crosses zero) **and** volume ≥ **1.2×** 20‑day average.
**Polling:** Hourly by default, with an optional **Boost (5‑min for 60 min)** toggle (to be wired).
""")
st.info("This page is a functional placeholder. Hook your sector ETF list and polling when ready.")
