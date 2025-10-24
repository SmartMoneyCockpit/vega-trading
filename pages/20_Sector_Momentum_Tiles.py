# pages/20_Sector_Momentum_Tiles.py
# Sector Momentum Tiles — compact, fast, and dependency-light
import os, math, pandas as pd, numpy as np, streamlit as st
from datetime import date, timedelta

# Optional widgets from your codebase
HAS_TV = False
try:
    from src.components.tradingview_widgets import advanced_chart
    HAS_TV = True
except Exception:
    pass

# Optional queue integration
HAS_QUEUE = False
try:
    from src.components.today_queue import add as add_to_queue
    HAS_QUEUE = True
except Exception:
    pass

# Data: SPDR US sector ETFs (robust + liquid)
SECTORS_US = {
    "XLY":"Consumer Discretionary",
    "XLP":"Consumer Staples",
    "XLE":"Energy",
    "XLF":"Financials",
    "XLV":"Health Care",
    "XLI":"Industrials",
    "XLB":"Materials",
    "XLK":"Technology",
    "XLU":"Utilities",
    "XLC":"Communication Services",
    "XLRE":"Real Estate",
}
BENCH = "SPY"

st.set_page_config(page_title="Sector Momentum Tiles", page_icon="🧩", layout="wide")
st.title("📊 Sector Momentum Tiles")

with st.expander("Settings", expanded=False):
    scope = st.selectbox("Universe", ["USA (SPDR)"], index=0)
    period = st.selectbox("History window", ["6mo", "1y", "2y"], index=1)
    topn = st.slider("Show top N by short momentum", 3, 11, 11, step=2)
    show_tv = st.checkbox("Show TradingView chart when opening a tile (if available)", value=True)
    show_links = st.checkbox("Show external chart links", value=True)
    allow_add = st.checkbox("Enable 'Add to Today's Queue' (if module present)", value=HAS_QUEUE)

# ------------- Data fetch (cached) -------------
@st.cache_data(show_spinner=True, ttl=900)
def fetch(prds: list[str], period: str = "1y"):
    import yfinance as yf
    tickers = " ".join(prds)
    df = yf.download(tickers=tickers, period=period, interval="1d", auto_adjust=True, progress=False, threads=True)["Close"]
    if isinstance(df, pd.Series):
        df = df.to_frame()
    return df.dropna(how="all")

tickers = list(SECTORS_US.keys()) + [BENCH]
try:
    prices = fetch(tickers, period=period).ffill().dropna(how="all")
except Exception as e:
    st.error(f"Data download failed: {e}")
    st.stop()

# ------------- Metrics -------------
def ema(a: pd.Series, n: int) -> pd.Series:
    return a.ewm(span=n, adjust=False).mean()

def sma(a: pd.Series, n: int) -> pd.Series:
    return a.rolling(n).mean()

def pct(a: pd.Series, n: int) -> float:
    if len(a) < n+1: return np.nan
    return (a.iloc[-1]/a.iloc[-1-n]-1.0)*100.0

def rs_vs_bench(sym: str, bench: str="SPY", window: int=20) -> float:
    s = prices[sym].dropna()
    b = prices[bench].dropna()
    idx = s.index.intersection(b.index)
    if len(idx) < window+1: return np.nan
    s = s.loc[idx]; b = b.loc[idx]
    return ((s.iloc[-1]/b.iloc[-1])/(s.iloc[-1-window]/b.iloc[-1-window]) - 1.0)*100.0

def score_short(sym: str) -> float:
    s = prices[sym].dropna()
    e10, e30 = ema(s,10), ema(s,30)
    if len(s) < 35: return -999
    mom = (e10.iloc[-1]-e30.iloc[-1]) / s.iloc[-1] * 100.0
    rs20 = rs_vs_bench(sym, BENCH, window=20)
    return mom + 0.5*rs20

def status_flag(sym: str) -> tuple[str,str]:
    s = prices[sym].dropna()
    if len(s) < 60:
        return "🟡 Wait","Short history"
    e10, e30 = ema(s,10), ema(s,30)
    above = s.iloc[-1] > sma(s,50).iloc[-1]
    short_up = (e10.iloc[-1] > e30.iloc[-1])
    if short_up and above: return "🟢 Buy Today","Short↑ & >SMA50"
    if short_up or above: return "🟡 Wait","Mixed"
    return "🔴 Avoid","Short↓ & <SMA50"

def quick_row(sym: str) -> dict:
    s = prices[sym].dropna()
    last = float(s.iloc[-1]) if len(s) else np.nan
    row = {
        "symbol": sym,
        "name": SECTORS_US.get(sym, sym),
        "last": last,
        "d1": pct(s,1),
        "d5": pct(s,5),
        "d20": pct(s,20),
        "d60": pct(s,60),
        "rs20": rs_vs_bench(sym, BENCH, 20),
        "short_score": score_short(sym),
    }
    stt, why = status_flag(sym)
    row["status"] = stt
    row["why"] = why
    return row

data = pd.DataFrame([quick_row(t) for t in SECTORS_US.keys()]).sort_values("short_score", ascending=False)
data_disp = data.head(topn)

st.caption("Rule: 🟢 if EMA10>EMA30 and price > SMA50; 🟡 if mixed; 🔴 if both negative. RS20 = 20-day relative strength vs SPY.")

# ------------- Tiles -------------
def fmt(v):
    if pd.isna(v): return "—"
    return f"{v:,.2f}"

def fmtp(v):
    if pd.isna(v): return "—"
    sign = "+" if v >= 0 else ""
    return f"{sign}{v:,.2f}%"

cols_per_row = 3
rows = math.ceil(len(data_disp)/cols_per_row)
idx = 0

for _ in range(rows):
    cols = st.columns(cols_per_row)
    for c in cols:
        if idx >= len(data_disp): break
        r = data_disp.iloc[idx]
        with c.container(border=True):
            st.markdown(f"### {r['status']}  {r['name']}  `{r['symbol']}`")
            st.write(
                f"**Last:** ${fmt(r['last'])}  •  "
                f"**1D:** {fmtp(r['d1'])}  •  **5D:** {fmtp(r['d5'])}  •  "
                f"**20D:** {fmtp(r['d20'])}  •  **60D:** {fmtp(r['d60'])}  •  "
                f"**RS20 vs SPY:** {fmtp(r['rs20'])}"
            )
            st.caption(r["why"])
            cc1, cc2, cc3 = st.columns([1,1,1])
            with cc1:
                if HAS_QUEUE and allow_add and st.button("➕ Add to Queue", key=f"q_{r['symbol']}"):
                    add_to_queue(r["symbol"], "USA")
                    st.success("Added")
            with cc2:
                if st.button("📈 Open Chart", key=f"ch_{r['symbol']}"):
                    if HAS_TV and show_tv:
                        advanced_chart(r["symbol"], interval="D", autosize=True)
                    elif show_links:
                        st.link_button("Open TradingView", f"https://www.tradingview.com/symbols/{r['symbol']}/", use_container_width=True)
                    else:
                        st.info("Chart widget not available.")
            with cc3:
                st.metric("Short Score", f"{r['short_score']:.2f}")
        idx += 1

# ------------- Full Table -------------
with st.expander("View full table"):
    showcols = ["symbol","name","status","why","last","d1","d5","d20","d60","rs20","short_score"]
    st.dataframe(data[showcols].reset_index(drop=True), use_container_width=True)
