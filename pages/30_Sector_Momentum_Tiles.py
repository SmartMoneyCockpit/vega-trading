import streamlit as st
import pandas as pd

st.set_page_config(page_title="Sector Momentum Tiles", page_icon="🧩", layout="wide")
st.title("Sector Momentum Tiles")

try:
    from src.components.sector_momentum import load_region, score_from_df, grade_band, trend_emoji
    HAS_HELPER = True
except Exception:
    HAS_HELPER = False

try:
    from src.components.tradingview_widgets import advanced_chart
    HAS_TV = True
except Exception:
    HAS_TV = False

if not HAS_HELPER:
    st.warning("Helper not found. Drop in `src/components/sector_momentum.py` from the delta ZIP.")
else:
    cols = st.columns(4)
    region = cols[0].selectbox("Region", ["USA","Canada","Mexico"], index=0)
    window = cols[1].selectbox("Window", ["1D","5D","1M"], index=0, help="Momentum lookback used for sorting and tile color.")
    sort_by = cols[2].selectbox("Sort by", ["Momentum","RS Score"], index=0)
    show_tv = cols[3].checkbox("Show TradingView charts (if available)", value=False)

    df = load_region(region)
    df = score_from_df(df, window)

    if sort_by == "Momentum":
        df = df.sort_values("momentum", ascending=False)
    else:
        df = df.sort_values("rs_score", ascending=False)

    ncols = 3
    rows = (len(df) + ncols - 1) // ncols
    for r in range(rows):
        cols = st.columns(ncols, gap="large")
        for c in range(ncols):
            i = r*ncols + c
            if i >= len(df): break
            row = df.iloc[i]
            with cols[c]:
                st.markdown(f"### {row['name']}  {trend_emoji(float(row['momentum']))}")
                st.metric("Momentum", f"{row['momentum']:+.2f}%",
                          delta=f"RS {int(row['rs_score'])}/100 {grade_band(float(row['mom_norm']))}")
                st.progress(max(0, min(100, int(row['mom_norm']))))

                if show_tv and 'HAS_TV' in globals() and HAS_TV:
                    try:
                        advanced_chart(symbol=row['symbol'], exchange="", height=260)
                    except Exception:
                        st.caption("TradingView widget not available here.")

    st.divider()
    st.caption("Notes: Momentum uses the selected window (1D, 5D, 1M). RS Score is a 0–100 placeholder for now; "
               "wire to your authenticated TradingView sector feed in a weekly upgrade.")
