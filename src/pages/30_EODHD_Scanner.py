
import streamlit as st, pandas as pd
from eodhd_client import get_eod_history
from utils import title_with_flag, ensure_token_notice

title_with_flag("EODHD Scanner", "")
ensure_token_notice()

st.caption("Simple EOD scanner — shows last close with 20/50 SMA.")
symbol = st.text_input("Symbol (e.g., AAPL). Suffix is added by exchange select.", "AAPL")
exch = st.selectbox("Exchange", ["US","TO","MX",""], index=0)
go = st.button("Run")

if go:
    data = get_eod_history(symbol, exch, period="d", from_="2023-01-01")
    if "error" in data:
        st.error(data["error"])
    else:
        import pandas as pd
        df = pd.DataFrame(data)
        if not df.empty and {"close","date"}.issubset(df.columns):
            df["date"] = pd.to_datetime(df["date"])
            df = df.sort_values("date")
            df["sma20"] = df["close"].rolling(20).mean()
            df["sma50"] = df["close"].rolling(50).mean()
            st.line_chart(df.set_index("date")[["close","sma20","sma50"]])
            last = df.iloc[-1][["close","sma20","sma50"]]
            st.write("Last:", last.to_dict())
        else:
            st.warning("No EOD data returned.")
