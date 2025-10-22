
import streamlit as st, pandas as pd
from eodhd_client import get_price_quote
from utils import title_with_flag, ensure_token_notice

title_with_flag("Unified Scanner", "")
ensure_token_notice()

st.caption("Quick multi-country spot-check. Enter tickers and choose exchange suffix.")
tickers = st.text_area("Tickers", "SPY\nAMZN\nNEE\nZEB\nCPD\nZPR\nWALMEX").splitlines()
exch = st.selectbox("Exchange suffix", ["US","TO","MX",""], index=0)
go = st.button("Scan")

if go:
    rows = []
    for t in tickers:
        t = t.strip()
        if not t: continue
        q = get_price_quote(t, exch)
        if "error" in q:
            rows.append({"ticker": t, "error": q["error"]})
        else:
            rows.append({"ticker": t, "price": q.get("close"), "change": q.get("change"), "change_p": q.get("change_p")})
    if rows:
        st.dataframe(pd.DataFrame(rows), use_container_width=True)
