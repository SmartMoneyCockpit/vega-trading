import os
import json
import pandas as pd
import numpy as np
import streamlit as st

from src.components.tradingview_widgets import advanced_chart, economic_calendar
from src.engine.smart_money import make_light_badge, passes_rules
from src.components.today_queue import add as add_to_queue, render as render_queue
from src.engine.vector_metrics import compute_from_df

# -----------------------------
# Page header
# -----------------------------
st.set_page_config(page_title="USA Text Dashboard", page_icon="🗺️", layout="wide")
st.title("USA Text Dashboard")
st.success(make_light_badge("USA"))

st.markdown("### 🔎 Scanner & Chart")
left, right = st.columns([3, 2], gap="large")

# =========================
# LEFT: CHART + METRICS
# =========================
with left:
    scan_kind = st.radio(
        "Scan type",
        ["Rising Wedge", "Falling Wedge", "Both (Wedges)", "Vega Smart Money (Today)"],
        horizontal=True,
    )

    default_symbol = st.text_input("Symbol (TradingView format)", value="NASDAQ:QQQ")

    st.link_button(
        "🔗 Open in TradingView",
        f"https://www.tradingview.com/chart/?symbol={default_symbol}",
        use_container_width=True,
    )

    # Main chart
    advanced_chart(default_symbol, height=720)

    # Vector metrics for the selected symbol (requires a local CSV)
    csv_path = os.path.join(
        "data/eod/us",
        (default_symbol.split(":")[-1] if ":" in default_symbol else default_symbol) + ".csv",
    )
    if os.path.exists(csv_path):
        try:
            df = pd.read_csv(csv_path)
            m = compute_from_df(df)
            c1, c2, c3, c4, c5 = st.columns(5)
            c1.metric("RT", m["RT"])
            c2.metric("RV", m["RV"])
            c3.metric("RS", m["RS"])
            c4.metric("CI", m["CI"])
            c5.metric("VST", m["VST"])
        except Exception as e:
            st.caption(f"Vector metrics unavailable (CSV read/parse issue): {e}")
    else:
        st.caption("Vector metrics appear when a local CSV exists for the selected symbol (data/eod/us/).")

# =========================
# RIGHT: SCANNER + ACTIONS
# =========================
with right:
    st.subheader("Local Scans")

    # Symbols to scan (no CSV required; uses yfinance internally)
    symbols_txt = st.text_area(
        "Symbols (comma or newline separated)",
        "AAPL, MSFT, NVDA, AMZN, META, TSLA, QQQ, SPY",
        height=80
    )
    lookback = st.number_input("Lookback bars", min_value=100, max_value=3000, value=400, step=50)

    # Session storage for results
    if "us_scan_results" not in st.session_state:
        st.session_state["us_scan_results"] = pd.DataFrame()

    # --- Helpers ---
    def parse_symbols(s: str):
        if not s:
            return []
        raw = [x.strip().upper() for x in s.replace("\n", ",").split(",")]
        return [x for x in raw if x]

    # Simple wedge detector (self-contained)
    def _load_ohlc(symbol: str, lookback: int = 400):
        try:
            import yfinance as yf
            df = yf.download(symbol, period="2y", interval="1d", auto_adjust=True, progress=False)
        except Exception:
            df = pd.DataFrame()
        if df is None or df.empty:
            return pd.DataFrame()
        df = df.tail(lookback).rename(columns=str.title)
        if "Close" not in df.columns and "Adj Close" in df.columns:
            df["Close"] = df["Adj Close"]
        cols = [c for c in ["Open", "High", "Low", "Close"] if c in df.columns]
        return df[cols].copy() if cols else pd.DataFrame()

    def _linreg(x, y):
        x = np.asarray(x, dtype=float)
        y = np.asarray(y, dtype=float)
        n = len(x)
        if n < 2:
            return (0.0, 0.0)
        A = np.vstack([x, np.ones(n)]).T
        m, b = np.linalg.lstsq(A, y, rcond=None)[0]
        return (m, b)

    def _channel_slope_quality(highs, lows):
        idx = np.arange(len(highs))
        m_hi, b_hi = _linreg(idx, highs)
        m_lo, b_lo = _linreg(idx, lows)
        fit_hi = -np.mean(np.abs((m_hi*idx + b_hi) - highs))
        fit_lo = -np.mean(np.abs((m_lo*idx + b_lo) - lows))
        fit = (fit_hi + fit_lo) / 2.0
        return (m_hi, b_hi, m_lo, b_lo, fit)

    def _is_rising_wedge(df):
        highs = df["High"].values
        lows  = df["Low"].values
        m_hi, b_hi, m_lo, b_lo, fit = _channel_slope_quality(highs, lows)
        cond = (m_hi > 0) and (m_lo > 0) and (m_hi < m_lo)
        score = float(fit + (m_lo - m_hi))
        return cond, score

    def _is_falling_wedge(df):
        highs = df["High"].values
        lows  = df["Low"].values
        m_hi, b_hi, m_lo, b_lo, fit = _channel_slope_quality(highs, lows)
        cond = (m_hi < 0) and (m_lo < 0) and (m_lo > m_hi)
        score = float(fit + (m_lo - m_hi))
        return cond, score

    @st.cache_data(show_spinner=False, ttl=300)
    def run_wedge_scan(symbols, which="Both", lookback=400):
        out = []
        for sym in symbols:
            try:
                dfp = _load_ohlc(sym, lookback=lookback)
                if dfp.empty or len(dfp) < 100:
                    continue
                row = {"symbol": sym, "rising": 0, "falling": 0, "score": 0.0}
                if which in ("Rising Wedge", "Both (Wedges)"):
                    ok, sc = _is_rising_wedge(dfp)
                    if ok:
                        row["rising"] = 1
                        row["score"] = max(row["score"], sc)
                if which in ("Falling Wedge", "Both (Wedges)"):
                    ok, sc = _is_falling_wedge(dfp)
                    if ok:
                        row["falling"] = 1
                        row["score"] = max(row["score"], sc)
                if row["rising"] or row["falling"]:
                    out.append(row)
            except Exception:
                continue
        if not out:
            return pd.DataFrame(columns=["symbol", "rising", "falling", "score"])
        return pd.DataFrame(out).sort_values("score", ascending=False).reset_index(drop=True)

    def safe_passes_rules(sym: str, region: str = "USA"):
        """Safely call passes_rules; swallow the known datetime mismatch crash."""
        try:
            return passes_rules(sym, region) or {"pass": False}
        except TypeError:
            # Known bug in older within_earnings_window() (datetime64 vs Timestamp)
            return {"pass": False}
        except Exception:
            return {"pass": False}

    # Run / Clear buttons
    run_col, clear_col = st.columns([2, 1])
    if run_col.button("🔍 Run Scanner", use_container_width=True):
        symbols = parse_symbols(symbols_txt)
        if not symbols:
            st.warning("Please provide at least one symbol.")
        else:
            with st.spinner("Scanning patterns..."):
                if scan_kind in ("Rising Wedge", "Falling Wedge", "Both (Wedges)"):
                    res = run_wedge_scan(symbols, which=scan_kind, lookback=lookback)
                else:
                    # Vega Smart Money (Today) — delegate to your engine on the same symbols if available
                    # Fallback: run wedges and mark pass via engine
                    res = run_wedge_scan(symbols, which="Both (Wedges)", lookback=lookback)
            st.session_state["us_scan_results"] = res
            st.success("Scanner finished successfully.")

    if clear_col.button("🗑️ Clear", use_container_width=True):
        st.session_state["us_scan_results"] = pd.DataFrame()

    # Display results
    res = st.session_state["us_scan_results"]
    if not res.empty:
        res = res.copy()
        # Smart Money pass/fail column (safe)
        res["pass"] = [
            "✅" if safe_passes_rules(sym, "USA").get("pass") else "⛔"
            for sym in res["symbol"]
        ]
        st.dataframe(res, use_container_width=True, hide_index=True)

        pick = st.selectbox("Send to chart", res["symbol"].tolist())
        a, b = st.columns(2)
        if a.button("Set Chart to Selection"):
            st.session_state["sel_us"] = pick
            st.experimental_rerun()
        if b.button("Add to Today's Trades"):
            add_to_queue(pick, "USA")
            st.toast(f"Added {pick} to Today's Trades")
    else:
        st.info("Click **Run Scanner** to generate results.")

# If a symbol was sent from the scan results, update the chart
sel = st.session_state.get("sel_us")
if sel:
    st.success(f"Chart updated to: {sel}")
    advanced_chart(sel if ":" in sel else sel, height=720)
    st.markdown(f"[Open in TradingView ↗](https://www.tradingview.com/chart/?symbol={sel})")

st.markdown("---")
st.header("🗓️ Economic Calendar")
economic_calendar(country="US", height=520)

# =========================
# === NEWS & MORNING REPORT
# =========================
st.markdown("---")
st.header("📰 USA Morning Report & News")
col1, col2 = st.columns(2)

with col1:
    st.subheader("🇺🇸 Morning Report (Latest)")
    report_path = "reports/usa_morning.md"
    if os.path.exists(report_path):
        with open(report_path, "r", encoding="utf-8") as f:
            st.markdown(f.read())
    else:
        st.info("No `reports/usa_morning.md` file yet — it will appear once your Morning Digest cron runs.")

with col2:
    st.subheader("Market News (from data/news.json)")
    news = {}
    try:
        with open("data/news.json", "r", encoding="utf-8") as f:
            news = json.load(f)
    except Exception:
        news = {"items": []}
    items = news.get("items", [])
    if items:
        for n in items[:12]:
            title = n.get("title", "(no title)")
            src   = n.get("source", "")
            ts    = n.get("ts", "")
            url   = n.get("url", "")
            with st.container(border=True):
                st.markdown(f"**{title}**")
                meta = " • ".join([x for x in [src, ts] if x])
                if meta:
                    st.caption(meta)
                if url:
                    st.link_button("Open", url, use_container_width=True)
    else:
        st.info("`data/news.json` is empty. Your `vega-home-feeds` cron will populate this automatically.")

st.markdown("---")
render_queue()

