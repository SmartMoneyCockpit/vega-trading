
import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# Optional: project-native chart widget
try:
    from src.components.tradingview_widgets import advanced_chart
except Exception:
    advanced_chart = None

st.set_page_config(page_title="USA Scanner Pro", page_icon="🛰️", layout="wide")
st.title("USA Scanner Pro")

st.caption("Fast pattern scans (Rising/Falling Wedge) + Smart Money hooks, with News & Morning Report.")

# ----------------------------
# Inputs
# ----------------------------
with st.container(border=True):
    c1, c2, c3 = st.columns([1.2,1,1])
    with c1:
        symbols_txt = st.text_area("Symbols to scan (comma or newline separated)", "AAPL, MSFT, NVDA, AMZN, META, TSLA, QQQ, SPY")
    with c2:
        pattern = st.selectbox("Pattern", ["Rising Wedge", "Falling Wedge", "Both"])
    with c3:
        lookback = st.number_input("Lookback bars", min_value=100, max_value=3000, value=400, step=50)

    run = st.button("Run Scanner", use_container_width=True)

# ----------------------------
# Pattern detection
# ----------------------------
def parse_symbols(s: str):
    if not s:
        return []
    raw = [x.strip().upper() for x in s.replace("\\n", ",").split(",")]
    return [x for x in raw if x]

@st.cache_data(show_spinner=False, ttl=300)
def detect_patterns(symbols, pattern, lookback):
    from src.scanner.patterns import find_wedges_batch
    return find_wedges_batch(symbols, pattern=pattern, lookback=lookback)

if run:
    symbols = parse_symbols(symbols_txt)
    if not symbols:
        st.warning("Please provide at least one symbol.")
    else:
        with st.spinner("Scanning..."):
            df = detect_patterns(symbols, pattern, lookback)
        st.success(f"Scan complete: {len(df)} results")
        st.dataframe(df, use_container_width=True)

        # Quick send-to-chart
        if len(df):
            pick = st.selectbox("Send to chart", df["symbol"])
            if pick:
                with st.container(border=True):
                    st.markdown(f"**{pick}**")
                    if advanced_chart:
                        try:
                            advanced_chart(symbol=pick, height=420, studies=["EMA 20", "EMA 50", "RSI"])
                        except Exception as e:
                            st.info(f"Widget error: {e}")
                    else:
                        st.code("advanced_chart not available in this build.")

# ----------------------------
# News + Morning Report
# ----------------------------
left, right = st.columns([1,1])

with left:
    st.markdown("#### USA Morning Report (latest)")
    # Load from reports/usa_morning.md if present
    import os, json
    report_path = "reports/usa_morning.md"
    if os.path.exists(report_path):
        with open(report_path, "r", encoding="utf-8") as f:
            st.markdown(f.read())
    else:
        st.info("No `reports/usa_morning.md` found yet. The Morning Digest job will populate this.")

with right:
    st.markdown("#### News (Latest)")
    news = {}
    try:
        with open("data/news.json", "r", encoding="utf-8") as f:
            import json
            news = json.load(f)
    except Exception:
        news = {"items":[]}
    items = news.get("items", [])
    if items:
        for n in items[:12]:
            t = n.get("title","(no title)")
            s = n.get("source","")
            ts = n.get("ts","")
            url = n.get("url","")
            with st.container(border=True):
                st.markdown(f"**{t}**")
                meta = " • ".join([x for x in [s, ts] if x])
                if meta:
                    st.caption(meta)
                if url:
                    st.link_button("Open", url, use_container_width=True)
    else:
        st.info("`data/news.json` is empty. The `vega-home-feeds` cron will populate this.")
