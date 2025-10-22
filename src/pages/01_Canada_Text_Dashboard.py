
import streamlit as st
import pandas as pd
from utils import title_with_flag, ensure_token_notice
from eodhd_client import get_price_quote

title_with_flag("Canada Text Dashboard", "Canada")
ensure_token_notice()

st.write("**Scope**: Country-focused text dashboard. Replace the sample tickers with your watchlist.")
default_tickers = ['ZEB','CPD','ZPR','HPR','ZGRO']

col1, col2 = st.columns([1,3])
with col1:
    tickers = st.text_area("Tickers (one per line)", "\n".join(default_tickers)).splitlines()
    exch = st.selectbox("Exchange suffix", ['TO','CN',''], index=0)
    run = st.button("Fetch Latest")

with col2:
    if run:
        data = []
        for t in tickers:
            t = t.strip()
            if not t:
                continue
            q = get_price_quote(t, exch)
            if "error" in q:
                data.append({"ticker": t, "exchange": exch, "error": q["error"]})
            else:
                data.append({
                    "ticker": t,
                    "exchange": exch,
                    "price": q.get("close") or q.get("previousClose") or q.get("lastTradePrice"),
                    "change": q.get("change"),
                    "change_p": q.get("change_p"),
                    "timestamp": q.get("timestamp")
                })
        st.dataframe(pd.DataFrame(data), use_container_width=True)
    else:
        st.info("Enter tickers and click **Fetch Latest**.")
