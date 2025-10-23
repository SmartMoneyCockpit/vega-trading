
import os, io, json
import pandas as pd
import numpy as np
import streamlit as st
from datetime import datetime
from src.engine import risk_scoring as rs

st.set_page_config(page_title="Risk & Return Scoring", page_icon="📊", layout="wide")
st.title("📊 Risk Return Scoring")
st.caption("Upload price history (CSV with columns: **date**, **close**). Optional: upload a benchmark CSV to compute beta/alpha.")

with st.expander("Upload CSV", expanded=True):
    c1, c2 = st.columns(2)
    with c1:
        f_asset = st.file_uploader("Asset CSV", type=["csv"], accept_multiple_files=False)
    with c2:
        f_bench = st.file_uploader("Benchmark CSV (optional)", type=["csv"], accept_multiple_files=False)

    st.write("**Expected columns:** `date`, `close` (other columns ignored). Dates will be parsed with `pd.to_datetime`.")

st.divider()

c1, c2, c3, c4 = st.columns(4)
with c1:
    freq = st.selectbox("Frequency", ["D","W","M"], index=0)
with c2:
    rf = st.number_input("Risk-free (annual, decimal)", value=0.0, step=0.005, format="%.4f")
with c3:
    price_col = st.text_input("Price column", value="close")
with c4:
    go = st.button("Compute Score", type="primary")

with st.expander("Weights (0..1, auto-normalized)", expanded=False):
    w_defaults = rs.DEFAULT_WEIGHTS.copy()
    weights = {}
    cols = st.columns(len(w_defaults))
    for i, (k,v) in enumerate(w_defaults.items()):
        with cols[i]:
            weights[k] = st.number_input(k, value=float(v), min_value=0.0, max_value=1.0, key=f"w_{k}")
    if sum(weights.values()) == 0:
        st.warning("All weights are zero. Using defaults.")
        weights = w_defaults

def _load_csv(uploaded):
    df = pd.read_csv(uploaded)
    # Flexible parsing
    if "date" in df.columns:
        df["date"] = pd.to_datetime(df["date"], errors="coerce")
        df = df.sort_values("date").set_index("date")
    else:
        # try first column
        df.iloc[:,0] = pd.to_datetime(df.iloc[:,0], errors="coerce")
        df = df.rename(columns={df.columns[0]:"date"}).sort_values("date").set_index("date")
    return df

if go:
    if not f_asset:
        st.error("Please upload an Asset CSV.")
    else:
        try:
            asset = _load_csv(f_asset)
            bench = _load_csv(f_bench) if f_bench else None

            metrics = rs.score_from_prices(
                df=asset, benchmark=bench, price_col=price_col, rf=rf, freq=freq, weights=weights
            )

            st.subheader("Results")
            cA, cB = st.columns([1,1])
            with cA:
                st.metric("Composite Score", f"{metrics['score']:.1f} / 100")
                st.metric("Sharpe", f"{metrics['sharpe']:.2f}")
                st.metric("Sortino", f"{metrics['sortino']:.2f}")
                st.metric("Volatility (ann.)", f"{metrics['vol']:.2%}")
            with cB:
                st.metric("Max Drawdown", f"{metrics['mdd']:.2%}")
                st.metric("CVaR (5%)", f"{metrics['cvar']:.2%}")
                if not np.isnan(metrics.get("beta", np.nan)):
                    st.metric("Beta vs Benchmark", f"{metrics['beta']:.2f}")
                    st.metric("Jensen's Alpha (ann.)", f"{metrics['alpha']:.2%}")
                st.metric("CAGR", f"{metrics['cagr']:.2%}")

            # Charts
            st.subheader("Charts")
            r = asset[price_col].pct_change().dropna()
            eq = (1 + r).cumprod()
            st.line_chart(eq.rename("Equity Curve"))
            st.line_chart(r.rename("Daily Returns"))

            st.success("Done. Adjust weights above to recompute the composite score.")
        except Exception as e:
            st.exception(e)
else:
    st.info("Upload data to score.")
