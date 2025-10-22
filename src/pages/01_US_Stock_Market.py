import os, pandas as pd, streamlit as st
from src.components.tradingview_widgets import advanced_chart, economic_calendar
from src.engine.smart_money import make_light_badge, passes_rules
from src.components.today_queue import add as add_to_queue, render as render_queue
from src.engine.vector_metrics import compute_from_df

st.set_page_config(page_title="USA Text Dashboard", page_icon="🗺️", layout="wide")
st.title("USA Text Dashboard")
st.success(make_light_badge("USA"))

st.markdown("### 🔎 Scanner & Chart")
left, right = st.columns([3, 2], gap="large")

# =========================
# LEFT: CHART + METRICS
# =========================
with left:
    scan_kind = st.radio(
        "Scan type",
        ["Rising Wedge", "Falling Wedge", "Vega Smart Money (Today)"],
        horizontal=True,
    )

    default_symbol = st.text_input("Symbol (TradingView format)", value="NASDAQ:QQQ")
    st.link_button(
        "🔗 Open in TradingView",
        f"https://www.tradingview.com/chart/?symbol={default_symbol}",
        use_container_width=True,
    )
    advanced_chart(default_symbol, height=720)

    # Vector metrics for the selected symbol (requires a local CSV)
    csv_path = os.path.join(
        "data/eod/us",
        (default_symbol.split(":")[-1] if ":" in default_symbol else default_symbol) + ".csv",
    )
    if os.path.exists(csv_path):
        df = pd.read_csv(csv_path)
        m = compute_from_df(df)
        c1, c2, c3, c4, c5 = st.columns(5)
        c1.metric("RT", m["RT"])
        c2.metric("RV", m["RV"])
        c3.metric("RS", m["RS"])
        c4.metric("CI", m["CI"])
        c5.metric("VST", m["VST"])
    else:
        st.caption("Vector metrics appear when a local CSV exists for the selected symbol (data/eod/us/).")

# =========================
# RIGHT: SCANNER + ACTIONS
# =========================
with right:
    st.subheader("Local Scans")

    # Map UI option -> scanner key
    kind_map = {
        "Rising Wedge": "rising_wedge",
        "Falling Wedge": "falling_wedge",
        "Vega Smart Money (Today)": "vega_smart_today",
    }
    kind_key = kind_map[scan_kind]

    # Session storage for results so they persist after reruns
    if "us_scan_results" not in st.session_state:
        st.session_state["us_scan_results"] = pd.DataFrame()

    # Run / Clear buttons
    run_col, clear_col = st.columns([2, 1])
    if run_col.button("🔍 Run Scanner", use_container_width=True):
        try:
            from tools.scanners.pattern_scanners import run_scan
            res = run_scan(data_dir="data/eod/us", kind=kind_key, limit=50)
            st.session_state["us_scan_results"] = res
            st.success("Scanner finished successfully.")
        except Exception as e:
            st.error(f"Scanner error: {e}")

    if clear_col.button("🗑️ Clear", use_container_width=True):
        st.session_state["us_scan_results"] = pd.DataFrame()

    # Display results (if any)
    res = st.session_state["us_scan_results"]
    if not res.empty:
        # Smart Money pass/fail column
        res = res.copy()
        res["pass"] = ["✅" if passes_rules(sym, "USA").get("pass") else "⛔" for sym in res["symbol"]]
        st.dataframe(res, use_container_width=True, hide_index=True)

        pick = st.selectbox("Send to chart", res["symbol"].tolist())
        a, b = st.columns(2)
        if a.button("Set Chart to Selection"):
            st.session_state["sel_us"] = pick
            st.experimental_rerun()
        if b.button("Add to Today's Trades"):
            add_to_queue(pick, "USA")
            st.toast(f"Added {pick} to Today's Trades")
    else:
        st.info("Click **Run Scanner** to generate results. (Make sure CSVs exist in `data/eod/us/`.)")

# If a symbol was sent from the scan results, update the chart
sel = st.session_state.get("sel_us")
if sel:
    st.success(f"Chart updated to: {sel}")
    advanced_chart(sel if ":" in sel else sel, height=720)
    st.markdown(f"[Open in TradingView ↗](https://www.tradingview.com/chart/?symbol={sel})")

st.markdown("---")
st.header("🗓️ Economic Calendar")
economic_calendar(country="US", height=520)

st.markdown("---")
render_queue()
