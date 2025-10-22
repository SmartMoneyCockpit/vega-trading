# src/pages/06_LATAM_Text_Dashboard.py
import os, json, pandas as pd, streamlit as st
from src.components.tradingview_widgets import advanced_chart, economic_calendar

st.set_page_config(page_title="LATAM (ex‑Mexico) Text Dashboard", page_icon="🗺️", layout="wide")
st.title("LATAM (ex‑Mexico) Text Dashboard")

# Controls
st.markdown("### 🔎 Scanner & Chart")
left, right = st.columns([3,2], gap="large")

with left:
    scan_kind = st.radio("Scan type", ["Rising Wedge","Falling Wedge","Vega Smart Money (Today)"], horizontal=True)
    default_symbol = st.text_input("Symbol (TradingView format)", value="BCBA:GGAL")
    if st.button("🔗 Open in TradingView"):
        st.link_button("Open Chart", f"https://www.tradingview.com/chart/?symbol={default_symbol}", use_container_width=True)
    advanced_chart(default_symbol, height=720)

with right:
    st.subheader("Local Scans")
    st.caption("Put OHLCV CSVs in `data/eod/latam` or set `VEGA_LATAM_EOD_DIR` env var.")
    try:
        from tools.scanners.pattern_scanners import run_scan
        kind_key = {"Rising Wedge":"rising_wedge","Falling Wedge":"falling_wedge","Vega Smart Money (Today)":"vega_smart_today"}[scan_kind]
        data_dir = os.getenv("VEGA_LATAM_EOD_DIR", "data/eod/latam")
        res = run_scan(data_dir=data_dir, kind=kind_key, limit=50)
        if not res.empty:
            st.dataframe(res, use_container_width=True, hide_index=True)
            pick = st.selectbox("Send to chart", res["symbol"].tolist())
            if st.button("Set Chart to Selection"):
                st.session_state["sel_06_LATAM_Text_Dashboard.py"] = pick
                st.experimental_rerun()
        else:
            st.info("No results yet. Add CSVs to the data folder.")
    except Exception as e:
        st.error(f"Scanner error: {e}")

sel = st.session_state.get("sel_06_LATAM_Text_Dashboard.py")
if sel:
    st.success(f"Chart updated to: {sel}")
    advanced_chart(sel if ":" in sel else sel, height=720)
    st.markdown(f"[Open in TradingView ↗](https://www.tradingview.com/chart/?symbol={sel})")

st.markdown("---")
st.header("🗓️ Economic Calendar")
st.caption("TradingView public calendar — free. Filters: BR,CL,AR,PE,CO")
economic_calendar(country="BR,CL,AR,PE,CO", height=520)
