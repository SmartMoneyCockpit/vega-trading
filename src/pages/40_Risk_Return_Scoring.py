
import os, io, json
import pandas as pd
import numpy as np
import streamlit as st
from datetime import datetime
from src.engine import risk_scoring as rs

st.set_page_config(page_title="Risk & Return Scoring", page_icon="📊", layout="wide")
st.title("📊 Risk Return Scoring")
st.caption("Upload price history (CSV with columns: **date**, **close**). Optional: upload a benchmark CSV to compute beta/alpha. Batch mode supports multiple asset CSVs.")

with st.expander("Upload CSV", expanded=True):
    c1, c2 = st.columns(2)
    with c1:
        f_asset = st.file_uploader("Asset CSV", type=["csv"], accept_multiple_files=False, key="single_asset")
    with c2:
        f_bench = st.file_uploader("Benchmark CSV (optional)", type=["csv"], accept_multiple_files=False, key="bench_csv")
    st.write("**Expected columns:** `date`, `close` (other columns ignored). Dates parsed with `pd.to_datetime`.")

with st.expander("Batch Upload (multi-asset)", expanded=False):
    batch_files = st.file_uploader("Upload multiple asset CSVs (filenames used as symbols)", type=["csv"], accept_multiple_files=True, key="batch_assets")

st.divider()

c0, c1, c2, c3, c4 = st.columns([1,1,1,1,1])
with c0:
    preset = st.selectbox("Weight preset", list(rs.PRESETS.keys()) + ["Custom"], index=0)
with c1:
    freq = st.selectbox("Frequency", ["D","W","M"], index=0)
with c2:
    rf = st.number_input("Risk-free (annual, decimal)", value=0.0, step=0.005, format="%.4f")
with c3:
    price_col = st.text_input("Price column", value="close")
with c4:
    run_single = st.button("Compute Score (single)", type="primary")

with st.expander("Custom Weights (0..1, auto-normalized)", expanded=(preset=="Custom")):
    if preset == "Custom":
        w_defaults = rs.DEFAULT_WEIGHTS.copy()
    else:
        w_defaults = rs.PRESETS[preset].copy()
    weights = {}
    cols = st.columns(len(w_defaults))
    for i, (k,v) in enumerate(w_defaults.items()):
        with cols[i]:
            weights[k] = st.number_input(k, value=float(v), min_value=0.0, max_value=1.0, key=f"w_{k}")
    if sum(weights.values()) == 0:
        st.warning("All weights are zero. Using defaults.")
        weights = w_defaults

with st.expander("Rolling Metrics", expanded=False):
    c5, c6 = st.columns(2)
    with c5:
        roll_window = st.number_input("Rolling window (trading days)", value=63, min_value=10, max_value=252, step=1)
    with c6:
        show_rolling = st.checkbox("Show rolling Sharpe/Vol and Rolling Beta (if benchmark provided)", value=True)

@st.cache_data(show_spinner=False)
def _load_csv(uploaded):
    df = pd.read_csv(uploaded)
    if "date" in df.columns:
        df["date"] = pd.to_datetime(df["date"], errors="coerce")
        df = df.sort_values("date").set_index("date")
    else:
        df.iloc[:,0] = pd.to_datetime(df.iloc[:,0], errors="coerce")
        df = df.rename(columns={df.columns[0]:"date"}).sort_values("date").set_index("date")
    return df

def _symbol_from_name(uploaded):
    name = getattr(uploaded, "name", "ASSET")
    base = os.path.splitext(os.path.basename(name))[0]
    return base.upper()

# ===== Single-asset mode =====
if run_single:
    if not f_asset:
        st.error("Please upload an Asset CSV.")
    else:
        try:
            asset = _load_csv(f_asset)
            bench = _load_csv(f_bench) if f_bench else None

            metrics = rs.score_from_prices(df=asset, benchmark=bench, price_col=price_col, rf=rf, freq=freq, weights=weights)

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
            st.line_chart(eq.rename("Equity Curve (Asset)"))

            if bench is not None:
                rb = bench[price_col].pct_change().dropna()
                eq_b = (1 + rb).cumprod()
                combined = pd.concat([eq.rename("Asset"), eq_b.rename("Benchmark")], axis=1).dropna()
                st.line_chart(combined)

            st.line_chart(r.rename("Periodic Returns (Asset)"))

            if show_rolling:
                rm = rs.rolling_metrics(r, window=int(roll_window))
                st.line_chart(rm["roll_sharpe"].rename("Rolling Sharpe (Asset)"))
                st.line_chart(rm["roll_vol"].rename("Rolling Volatility (ann., Asset)"))
                if bench is not None:
                    rb = bench[price_col].pct_change().dropna()
                    roll_beta = rs.rolling_beta(r, rb, window=int(roll_window))
                    st.line_chart(roll_beta.rename("Rolling Beta vs Benchmark"))

            # Exports
            st.subheader("Export")
            jbuf = io.StringIO()
            json.dump(metrics, jbuf, indent=2, default=lambda x: None)
            st.download_button("Download metrics (JSON)", data=jbuf.getvalue(), file_name="risk_metrics.json", mime="application/json")

            sym_guess = _symbol_from_name(f_asset)
            row_df = rs.metrics_to_row(sym_guess, metrics)
            csv_buf = io.StringIO()
            row_df.to_csv(csv_buf, index=False)
            st.download_button("Download summary (CSV)", data=csv_buf.getvalue(), file_name=f"{sym_guess}_risk_metrics_summary.csv", mime="text/csv")

            st.success("Single-asset scoring complete.")
        except Exception as e:
            st.exception(e)
else:
    st.info("Upload data to score (single) or use Batch mode below.")

# ===== Batch mode =====
st.subheader("Batch Scoring")
run_batch = st.button("Run Batch Scoring", type="secondary", disabled=(len(batch_files)==0))
if run_batch:
    try:
        assets = {}
        for f in batch_files:
            df = _load_csv(f)
            sym = _symbol_from_name(f)
            assets[sym] = df
        bench = _load_csv(f_bench) if f_bench else None
        results = rs.batch_score(assets, benchmark=bench, price_col=price_col, rf=rf, freq=freq, weights=weights)
        results = results.sort_values("score", ascending=False)
        st.dataframe(results, use_container_width=True)

        # Download
        csv_buf = io.StringIO()
        results.to_csv(csv_buf, index=False)
        st.download_button("Download batch results (CSV)", data=csv_buf.getvalue(), file_name="batch_risk_scoring.csv", mime="text/csv")

        st.success("Batch scoring complete.")
    except Exception as e:
        st.exception(e)
