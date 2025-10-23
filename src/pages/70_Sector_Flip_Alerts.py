
import os, io, json
import pandas as pd
import numpy as np
import streamlit as st
from pathlib import Path
from src.engine import sector_flip as sf

st.set_page_config(page_title="Sector Flip Alerts", page_icon="🚦", layout="wide")
st.title("🚦 Sector Flip Alerts")
st.caption("Detect intraday sector flips using relative-return sign change and EMA cross + volume. Upload intraday CSVs or point to paths.")

with st.expander("Inputs", expanded=True):
    c1, c2 = st.columns(2)
    with c1:
        idx_path = st.text_input("Benchmark index CSV (intraday)", "data/intraday/SPY_1min.csv")
        st.caption("Format: columns include datetime, close, [volume].")
        threshold = st.number_input("Relative-return threshold (±%)", min_value=0.1, max_value=5.0, value=0.6, step=0.1) / 100.0
        window_min = st.number_input("Window (minutes) for relative-return calc", min_value=5, max_value=60, value=15, step=1)
    with c2:
        vol_mult = st.number_input("Volume multiplier (x 20-bar avg)", min_value=1.0, max_value=3.0, value=1.2, step=0.1)
        fast = st.number_input("EMA fast", min_value=5, max_value=20, value=10, step=1)
        slow = st.number_input("EMA slow", min_value=20, max_value=60, value=30, step=1)
        boost = st.checkbox("Boost mode (5‑min cadence guideline)", value=False)

with st.expander("Upload intraday CSVs", expanded=False):
    idx_up = st.file_uploader("Index CSV", type=["csv"], key="idx")
    sector_files = st.file_uploader("Sector CSVs (multiple)", type=["csv"], accept_multiple_files=True, key="sectors")

st.divider()

run = st.button("Run Flip Scan", type="primary")

def _save_upload(f, outdir="data/intraday/uploads"):
    if not f: return None
    os.makedirs(outdir, exist_ok=True)
    p = os.path.join(outdir, Path(f.name).name)
    with open(p, "wb") as o: o.write(f.read())
    return p

if run:
    # Resolve file paths
    idx_res = _save_upload(idx_up) or idx_path
    sector_map = {}
    if sector_files:
        for f in sector_files:
            sector_map[f.name] = _save_upload(f)
    else:
        st.warning("No sector CSV uploads; you can still run if sector paths are set manually below.")

    # Manual sector paths (optional, JSON mapping)
    manual_json = st.text_area("Optional JSON mapping of sector file paths (name -> path)", value="", help='{"XLK.csv":"data/intraday/XLK_1min.csv"}')
    if manual_json.strip():
        try:
            sector_map.update(json.loads(manual_json))
        except Exception as e:
            st.error(f"Invalid JSON: {e}")

    if not sector_map:
        st.error("No sector files provided.")
    else:
        df = sf.evaluate_flips(
            sector_files=sector_map, index_file=idx_res,
            window_min=int(window_min), threshold=float(threshold),
            vol_mult=float(vol_mult), fast=int(fast), slow=int(slow)
        )
        if df.empty:
            st.info("No flips detected with the current parameters.")
        else:
            st.subheader("Detected Flips")
            st.dataframe(df, use_container_width=True)
            # Persist to alerts dir
            path = sf.write_alerts(df, alerts_dir="data/alerts", tag="sector_flips_intraday")
            st.success(f"Alerts saved → {path}")
            # Export
            csv_buf = io.StringIO()
            df.to_csv(csv_buf, index=False)
            st.download_button("Download alerts (CSV)", data=csv_buf.getvalue(), file_name="sector_flip_alerts.csv", mime="text/csv")
else:
    st.info("Set inputs, upload CSVs, and run the scan.")

st.caption("Default rules per your cockpit: (1) relative return sign flip ±0.6% over ≥15 min; OR (2) EMA10-EMA30 cross with volume ≥ 1.2× 20‑bar average. Polling cadence: hourly default; Boost mode = 5‑min for 60 minutes.")
