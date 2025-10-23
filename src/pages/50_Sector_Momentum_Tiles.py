
import os, io, json
import pandas as pd
import numpy as np
import streamlit as st
from src.engine import sector_momentum as sm

st.set_page_config(page_title="Sector Momentum Tiles", page_icon="📈", layout="wide")
st.title("📈 Sector Momentum Tiles")
st.caption("Upload sector CSVs (filename used as sector name). Optional benchmark CSV to compute RS and rankings.")

tabs = st.tabs(["USA","Canada","Mexico","LATAM ex-MX"])

def region_ui(label: str):
    with st.expander(f"{label} — Uploads", expanded=True):
        c1, c2 = st.columns(2)
        with c1:
            files = st.file_uploader(f"{label}: Sector CSVs", type=["csv"], accept_multiple_files=True, key=f"{label}_files")
        with c2:
            bench = st.file_uploader(f"{label}: Benchmark CSV (optional)", type=["csv"], accept_multiple_files=False, key=f"{label}_bench")
        st.caption("CSV columns: `date, close` (other columns ignored).")
    st.divider()

    cA, cB, cC = st.columns([1,1,1])
    with cA:
        price_col = st.text_input("Price column", value="close", key=f"{label}_price")
    with cB:
        tile_limit = st.number_input("Show top N tiles", min_value=1, max_value=50, value=12, step=1, key=f"{label}_limit")
    with cC:
        run = st.button(f"Build Tiles — {label}", type="primary", key=f"{label}_run")

    if run:
        try:
            bench_df = None
            if bench is not None:
                bdf = pd.read_csv(bench)
                if "date" in bdf.columns:
                    bdf["date"] = pd.to_datetime(bdf["date"], errors="coerce")
                    bdf = bdf.sort_values("date").set_index("date")
                else:
                    bdf.iloc[:,0] = pd.to_datetime(bdf.iloc[:,0], errors="coerce")
                    bdf = bdf.rename(columns={bdf.columns[0]:"date"}).sort_values("date").set_index("date")
                bench_df = bdf

            df = sm.tiles_from_files(files, bench_df=bench_df, price_col=price_col)
            df = df.sort_values("score", ascending=False)
            df["grade"] = df["score"].apply(sm.grade)
            st.dataframe(df, use_container_width=True)

            # Tile grid
            st.subheader("Tiles")
            cols = st.columns(min(int(tile_limit), 6))
            for i, (_, r) in enumerate(df.head(int(tile_limit)).iterrows()):
                with cols[i % len(cols)]:
                    st.metric(f"{r['sector']}  {r['grade']}", f"{r['score']*100:.1f}")
                    st.caption(f"1w {r['h_1w']:.2%} • 1m {r['h_1m']:.2%} • 3m {r['h_3m']:.2%} • 6m {r['h_6m']:.2%} • RS {r['rs'] if np.isfinite(r['rs']) else 0:.2f}")

            # Download
            csv_buf = io.StringIO()
            df.to_csv(csv_buf, index=False)
            st.download_button(f"Download {label} tiles (CSV)", data=csv_buf.getvalue(), file_name=f"{label.lower().replace(' ','_')}_sector_tiles.csv", mime="text/csv")

            # Placeholder: TradingView embeds toggle
            with st.expander("TradingView Embeds (placeholder)", expanded=False):
                st.info("Authenticated TradingView sector layouts will render here in a future upgrade using stored cookies.")
        except Exception as e:
            st.exception(e)
    else:
        st.info("Upload sector CSVs and click **Build Tiles**.")

with tabs[0]:
    region_ui("USA")
with tabs[1]:
    region_ui("Canada")
with tabs[2]:
    region_ui("Mexico")
with tabs[3]:
    region_ui("LATAM ex-MX")
