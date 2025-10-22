
import streamlit as st, pandas as pd
from typing import List, Tuple
from src.eodhd_client import get_price_quote

def render_morning_report(title: str, benchmarks: List[Tuple[str, str]], notes: str = ""):
    st.subheader(f"📰 {title}")
    rows = []
    for ticker, exch in benchmarks:
        q = get_price_quote(ticker, exch)
        if "error" in q:
            rows.append({"symbol": f"{ticker}.{exch}" if exch else ticker, "price": None, "change%": None, "status": q["error"]})
        else:
            rows.append({
                "symbol": f"{ticker}.{exch}" if exch else ticker,
                "price": q.get("close") or q.get("previousClose") or q.get("lastTradePrice"),
                "change%": q.get("change_p"),
                "status": q.get("timestamp")
            })
    st.dataframe(pd.DataFrame(rows), use_container_width=True)
    if notes:
        st.caption(notes)
