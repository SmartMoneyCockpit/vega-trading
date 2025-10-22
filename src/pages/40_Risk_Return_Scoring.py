
import streamlit as st, pandas as pd, numpy as np
from utils import title_with_flag
title_with_flag("Risk Return Scoring", "")
st.caption("Placeholder for Risk & Return Scoring. Upload CSV with columns date, close.")

uploaded = st.file_uploader("Upload CSV", type=["csv"])
if uploaded:
    df = pd.read_csv(uploaded)
    if {"date","close"}.issubset(df.columns):
        df["date"] = pd.to_datetime(df["date"])
        df = df.sort_values("date").reset_index(drop=True)
        df["ret"] = df["close"].pct_change()
        sharpe = float((df["ret"].mean() / (df["ret"].std() + 1e-9)) * (252**0.5))
        st.write({"sharpe": round(sharpe, 3)})
        st.line_chart(df.set_index("date")[["close"]])
    else:
        st.error("CSV must contain 'date' and 'close'.")
else:
    st.info("Upload data to score.")
