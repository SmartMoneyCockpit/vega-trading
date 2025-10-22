# src/pages/03_CA_Text_Dashboard.py
import os, json, pandas as pd, streamlit as st
from src.components.tradingview_widgets import advanced_chart, economic_calendar
from src.engine.smart_money import make_light_badge, passes_rules
from src.components.today_queue import add as add_to_queue, render as render_queue

st.set_page_config(page_title="Canada Text Dashboard", page_icon="🗺️", layout="wide")
st.title("Canada Text Dashboard")

# Status light banner
st.success(make_light_badge("Canada"))

# Controls
st.markdown("### 🔎 Scanner & Chart")
left, right = st.columns([3,2], gap="large")

with left:
    scan_kind = st.radio("Scan type", ["Rising Wedge","Falling Wedge","Vega Smart Money (Today)"], horizontal=True)
    default_symbol = st.text_input("Symbol (TradingView format)", value="TSX:ZEB")
    if st.button("🔗 Open in TradingView"):
        st.link_button("Open Chart", f"https://www.tradingview.com/chart/?symbol={default_symbol}", use_container_width=True)
    advanced_chart(default_symbol, height=720)

with right:
    st.subheader("Local Scans")
    data_dir = "data/eod"
    if "USA" in "Canada": data_dir = "data/eod/us"
    elif "Mexico" in "Canada": data_dir = "data/eod/mx"
    elif "LATAM" in "Canada": data_dir = "data/eod/latam"
    else: data_dir = "data/eod/ca"
    try:
        from tools.scanners.pattern_scanners import run_scan
        kind_key = {"Rising Wedge":"rising_wedge","Falling Wedge":"falling_wedge","Vega Smart Money (Today)":"vega_smart_today"}[scan_kind]
        res = run_scan(data_dir=data_dir, kind=kind_key, limit=50)
        if not res.empty:
            # Apply Smart Money pass/fail
            def _judge(sym):
                chk = passes_rules(sym, "Canada")
                return "✅" if chk.get("pass") else "⛔"
            res["pass"] = [ _judge(s) for s in res["symbol"] ]
            st.dataframe(res, use_container_width=True, hide_index=True)
            pick = st.selectbox("Send to chart", res["symbol"].tolist())
            cols = st.columns(2)
            if cols[0].button("Set Chart to Selection"):
                st.session_state["sel_03_CA_Text_Dashboard.py"] = pick; st.experimental_rerun()
            if cols[1].button("Add to Today's Trades"):
                add_to_queue(pick, "Canada"); st.toast(f"Added {pick} to Today's Trades")
        else:
            st.info("No results yet. Add CSVs to the data folder.")
    except Exception as e:
        st.error(f"Scanner error: {e}")

sel = st.session_state.get("sel_03_CA_Text_Dashboard.py")
if sel:
    st.success(f"Chart updated to: {sel}")
    advanced_chart(sel if ":" in sel else sel, height=720)
    st.markdown(f"[Open in TradingView ↗](https://www.tradingview.com/chart/?symbol={sel})")

st.markdown("---")
st.header("🗓️ Economic Calendar")
if "USA" in "Canada":
    economic_calendar(country="US", height=520)
elif "Mexico" in "Canada":
    economic_calendar(country="MX,US", height=520)
elif "LATAM" in "Canada":
    economic_calendar(country="BR,CL,AR,PE,CO", height=520)
else:
    economic_calendar(country="CA,US,MX", height=520)

st.markdown("---")
render_queue()
