
import streamlit as st, pandas as pd
from utils import title_with_flag
from src.eodhd_client import get_eod_history

title_with_flag("Relative Strength Momentum Dashboard", "")
st.caption("26-week RS trendlines with 4w/12w MAs — country or sector vs benchmark.")

symbol = st.text_input("Symbol", "SPY")
exch = st.selectbox("Exchange", ["US","TO","MX",""], index=0)
benchmark = st.text_input("Benchmark (reference)", "SPY")
bench_exch = st.selectbox("Benchmark Exchange", ["US","TO","MX",""], index=0)

if st.button("Compute RS"):
    s = get_eod_history(symbol, exch, period="d", from_="2023-01-01")
    b = get_eod_history(benchmark, bench_exch, period="d", from_="2023-01-01")
    if isinstance(s, dict) and "error" in s:
        st.error(f"Symbol error: {s['error']}")
    elif isinstance(b, dict) and "error" in b:
        st.error(f"Benchmark error: {b['error']}")
    else:
        ds = pd.DataFrame(s); db = pd.DataFrame(b)
        if {"date","close"}.issubset(ds.columns) and {"date","close"}.issubset(db.columns):
            ds["date"] = pd.to_datetime(ds["date"]); db["date"]=pd.to_datetime(db["date"])
            m = pd.merge(ds[["date","close"]].rename(columns={"close":"s"}),
                         db[["date","close"]].rename(columns={"close":"b"}), on="date", how="inner")
            m["RS"] = m["s"] / (m["b"] + 1e-9)
            m = m.sort_values("date")
            m["RS_4w"] = m["RS"].rolling(20).mean()
            m["RS_12w"]= m["RS"].rolling(60).mean()
            st.line_chart(m.set_index("date")[["RS","RS_4w","RS_12w"]])
        else:
            st.warning("No EOD data for symbol/benchmark.")
