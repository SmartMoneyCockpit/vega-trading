# src/pages/03_CA_Text_Dashboard.py
import os, json, pandas as pd, streamlit as st
from src.components.tradingview_widgets import advanced_chart, economic_calendar

st.set_page_config(page_title="CA Canada Text Dashboard", page_icon="🇨🇦", layout="wide")
st.title("CA Canada Text Dashboard")

# --- Controls ----------------------------------------------------------------
st.markdown("### 🔎 Scanner & Chart")
left, right = st.columns([3,2], gap="large")

with left:
    scan_kind = st.radio("Scan type", ["Rising Wedge","Falling Wedge","Vega Smart Money (Today)"], horizontal=True)
    # Optional symbol override
    default_symbol = st.text_input("Symbol (TradingView format)", value="TSX:ZEB")
    if st.button("🔗 Open in TradingView", use_container_width=False):
        st.link_button("Open Chart", f"https://www.tradingview.com/chart/?symbol={default_symbol}", use_container_width=True)
    # Full-width, tall chart at the very top
    advanced_chart(default_symbol, height=720)

with right:
    st.subheader("Local Scans (Canada)")
    st.caption("Drop CSVs in `data/eod/ca/` (OHLCV).")
    try:
        from tools.scanners.pattern_scanners import run_scan
        kind_key = {"Rising Wedge":"rising_wedge","Falling Wedge":"falling_wedge","Vega Smart Money (Today)":"vega_smart"}[scan_kind]
        if kind_key == "vega_smart":
            kind_key = "vega_smart_today"
        results = run_scan(kind=kind_key, limit=50)
        if not results.empty:
            st.dataframe(results, use_container_width=True, hide_index=True)
            pick = st.selectbox("Send to chart", results["symbol"].tolist())
            if st.button("Set Chart to Selection"):
                st.session_state["selected_symbol"] = pick
                st.experimental_rerun()
        else:
            st.info("No results yet. Add CSVs to `data/eod/ca/`.")
    except Exception as e:
        st.error(f"Scanner error: {e}")

# If user selected a symbol from scanner, update chart symbol
sel = st.session_state.get("selected_symbol")
if sel:
    st.success(f"Chart updated to: {sel}")
    advanced_chart(sel if ":" in sel else f"TSX:{sel}", height=720)
    st.markdown(f"[Open in TradingView ↗](https://www.tradingview.com/chart/?symbol={'TSX:'+sel if ':' not in sel else sel})")

st.markdown("---")

# --- Morning Report with VectorVest-style metrics ----------------------------
st.header("📋 Canada Morning Report")
# Try to load a prepared JSON if available; otherwise show sample
report_path = os.getenv("VEGA_CA_REPORT_JSON", "data/vega/ca_morning_report.json")
columns = ["symbol","price","change%","status","RT","RV","RS","CI","VST","arrow"]
if os.path.exists(report_path):
    try:
        with open(report_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        df = pd.DataFrame(data).reindex(columns=columns)
    except Exception:
        df = pd.DataFrame(columns=columns)
else:
    df = pd.DataFrame([
        {"symbol":"ZEB.TO","price":52.72,"change%":0.019,"status":"ok","RT":1.17,"RV":1.91,"RS":0.30,"CI":0.00,"VST":0.98,"arrow":"▲"},
        {"symbol":"XIU.TO","price":44.64,"change%":-1.359,"status":"ok","RT":1.02,"RV":1.30,"RS":0.25,"CI":0.00,"VST":0.95,"arrow":"▼"},
        {"symbol":"ZGRO.TO","price":17.34,"change%":-0.6304,"status":"ok","RT":1.05,"RV":1.40,"RS":0.28,"CI":0.00,"VST":0.96,"arrow":"▼"},
    ], columns=columns)

st.dataframe(df, use_container_width=True, hide_index=True)
st.caption("RT/RV/RS/CI/VST are VectorVest-style proxies (placeholders); replace with your computed metrics.")

st.markdown("---")

# --- Economic Calendar (TradingView public widget) ---------------------------
with st.expander("🗓️ Economic Calendar (TradingView)", expanded=True):
    rng = st.radio("Range", ["Today","Tomorrow","This Week"], horizontal=True, key="econ_rng")
    st.caption("This uses TradingView's public calendar widget (no EODHD needed).")
    economic_calendar(country="CA,US,MX", height=520)
