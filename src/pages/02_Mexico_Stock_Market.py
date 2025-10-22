import os, pandas as pd, streamlit as st
from src.components.tradingview_widgets import advanced_chart, economic_calendar
from src.engine.smart_money import make_light_badge, passes_rules
from src.components.today_queue import add as add_to_queue, render as render_queue
from src.engine.vector_metrics import compute_from_df

st.set_page_config(page_title="Mexico Text Dashboard", page_icon="🇲🇽", layout="wide")
st.title("Mexico Text Dashboard")
st.success(make_light_badge("Mexico"))

st.markdown("### 🔎 Scanner & Chart")
left, right = st.columns([3,2], gap="large")
with left:
    scan_kind = st.radio("Scan type", ["Rising Wedge","Falling Wedge","Vega Smart Money (Today)"], horizontal=True)
    default_symbol = st.text_input("Symbol (TradingView format)", value="BMV:WALMEX")
    if st.button("🔗 Open in TradingView"):
        st.link_button("Open Chart", f"https://www.tradingview.com/chart/?symbol={default_symbol}", use_container_width=True)
    advanced_chart(default_symbol, height=720)

    import os
    path = os.path.join("data/eod/mx", (default_symbol.split(":")[-1] if ":" in default_symbol else default_symbol) + ".csv")
    if os.path.exists(path):
        import pandas as pd
        df = pd.read_csv(path)
        m = compute_from_df(df)
        c1,c2,c3,c4,c5 = st.columns(5)
        c1.metric("RT", m["RT"]); c2.metric("RV", m["RV"]); c3.metric("RS", m["RS"]); c4.metric("CI", m["CI"]); c5.metric("VST", m["VST"])
    else:
        st.caption("Vector metrics appear when local CSV exists for the selected symbol.")

with right:
    st.subheader("Local Scans")
    try:
        from tools.scanners import pattern_scanners as ps
        res = ps.run_scan("data/eod/mx", kind="vega_smart_today", limit=50)
        if not res.empty:
            def _judge(sym):
                chk = passes_rules(sym, "Mexico")
                return "✅" if chk.get("pass") else "⛔"
            res["pass"] = [ _judge(s) for s in res["symbol"] ]
            st.dataframe(res, use_container_width=True, hide_index=True)
            pick = st.selectbox("Send to chart", res["symbol"].tolist())
            cols = st.columns(2)
            if cols[0].button("Set Chart to Selection"):
                st.session_state["sel_mx"] = pick; st.experimental_rerun()
            if cols[1].button("Add to Today's Trades"):
                add_to_queue(pick, "Mexico"); st.toast(f"Added {pick} to Today's Trades")
        else:
            st.info("No results yet. Add CSVs to the data folder.")
    except Exception as e:
        st.error(f"Scanner error: {e}")

sel = st.session_state.get("sel_mx")
if sel:
    st.success(f"Chart updated to: {sel}")
    advanced_chart(sel if ":" in sel else sel, height=720)
    st.markdown(f"[Open in TradingView ↗](https://www.tradingview.com/chart/?symbol={sel})")

st.markdown("---")
st.header("🗓️ Economic Calendar")
economic_calendar(country="MX,US", height=520)

st.markdown("---")
render_queue()
