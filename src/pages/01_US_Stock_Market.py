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
st.set_page_config(page_title="USA Text Dashboard", page_icon="🗺", layout="wide")
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

    # Symbols to scan
    symbols_txt = st.text_area(
        "Symbols (comma or newline separated)",
        "AAPL, MSFT, NVDA, AMZN, META, TSLA, QQQ, SPY",
        height=80
    )
    lookback = st.number_input("Lookback bars", min_value=100, max_value=3000, value=400, step=50)

    if "us_scan_results" not in st.session_state:
        st.session_state["us_scan_results"] = pd.DataFrame()

    def parse_symbols(s: str):
        if not s:
            return []
        raw = [x.strip().upper() for x in s.replace("\n", ",").split(",")]
        return [x for x in raw if x]

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
        lows = df["Low"].values
        m_hi, b_hi, m_lo, b_lo, fit = _channel_slope_quality(highs, lows)
        cond = (m_hi > 0) and (m_lo > 0) and (m_hi < m_lo)
        score = float(fit + (m_lo - m_hi))
        return cond, score

    def _is_falling_wedge(df):
        highs = df["High"].values
        lows = df["Low"].values
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
        try:
            return passes_rules(sym, region) or {"pass": False}
        except TypeError:
            return {"pass": False}
        except Exception:
            return {"pass": False}

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
                    res = run_wedge_scan(symbols, which="Both (Wedges)", lookback=lookback)
            st.session_state["us_scan_results"] = res
            st.success("Scanner finished successfully.")

    if clear_col.button("🗑 Clear", use_container_width=True):
        st.session_state["us_scan_results"] = pd.DataFrame()

    res = st.session_state["us_scan_results"]
    if not res.empty:
        res = res.copy()
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
        st.info("Click *Run Scanner* to generate results.")

sel = st.session_state.get("sel_us")
if sel:
    st.success(f"Chart updated to: {sel}")
    advanced_chart(sel if ":" in sel else sel, height=720)
    st.markdown(f"[Open in TradingView ↗](https://www.tradingview.com/chart/?symbol={sel})")

st.markdown("---")

# ──────────────────────────────────────────────────────────────────────────────
# ECONOMIC CALENDAR + EARNINGS (Split View, Inline Section)
# Drop this block directly inside your existing Streamlit page.
# Toggle source:
USE_TRADINGVIEW = True  # True = TradingView widgets (no API key), False = EODHD tables

import os, json, time, requests, pandas as pd, streamlit as st
from datetime import date, timedelta
from typing import Optional, Dict, List

# ── Styles: black divider, compact tables
st.markdown("""
<style>
.inline-black-divider{width:100%;height:520px;min-height:520px;background:#000;border-radius:8px;}
.stDataFrame table td,.stDataFrame table th{font-size:.9rem !important;line-height:1.2 !important;}
.section-card{padding:.6rem .8rem;border:1px solid rgba(255,255,255,.08);border-radius:12px;background:rgba(255,255,255,.02);}
.metric-pill{padding:2px 8px;border-radius:999px;border:1px solid rgba(255,255,255,.12);font-size:.8rem;background:rgba(255,255,255,.04);}
</style>
""", unsafe_allow_html=True)

st.markdown("### 📅 Economic Calendar & 💼 Earnings (Split View)")

left, mid, right = st.columns([1, 0.05, 1])

# ── Common header (keeps your page context)
with left:
    st.caption("Economic Calendar (left)")
with right:
    st.caption("Earnings (right)")
with mid:
    st.markdown('<div class="inline-black-divider"></div>', unsafe_allow_html=True)

# ──────────────────────────────────────────────────────────────────────────────
# OPTION A: TradingView widgets (no API key)
# ──────────────────────────────────────────────────────────────────────────────
if USE_TRADINGVIEW:
    import streamlit.components.v1 as components

    tv_height = 560  # adjust to taste

    with left:
        st.markdown('<div class="section-card">', unsafe_allow_html=True)
        st.markdown("##### 📊 Economic Calendar (TradingView • USA/CAD/MXN)")
        components.html(f"""
        <div class="tradingview-widget-container">
          <div class="tradingview-widget-container__widget"></div>
          <script type="text/javascript" src="https://s3.tradingview.com/external-embedding/embed-widget-events.js" async>
          {{
            "colorTheme": "dark",
            "isTransparent": true,
            "width": "100%",
            "height": "{tv_height}",
            "locale": "en",
            "importanceFilter": "-1,0,1",
            "currencyFilter": "USD,CAD,MXN"
          }}
          </script>
        </div>
        """, height=tv_height, scrolling=False)
        st.markdown('</div>', unsafe_allow_html=True)

    with right:
        st.markdown('<div class="section-card">', unsafe_allow_html=True)
        st.markdown("##### 💼 Upcoming Earnings (TradingView • US)")
        components.html(f"""
        <div class="tradingview-widget-container">
          <div class="tradingview-widget-container__widget"></div>
          <script type="text/javascript" src="https://s3.tradingview.com/external-embedding/embed-widget-earnings.js" async>
          {{
            "colorTheme": "dark",
            "isTransparent": true,
            "width": "100%",
            "height": "{tv_height}",
            "locale": "en",
            "exchange": "US"
          }}
          </script>
        </div>
        """, height=tv_height, scrolling=False)
        st.markdown('</div>', unsafe_allow_html=True)

# ──────────────────────────────────────────────────────────────────────────────
# OPTION B: EODHD API tables (requires EODHD_API_TOKEN)
# ──────────────────────────────────────────────────────────────────────────────
else:
    def _get_token()->Optional[str]:
        token = os.getenv("EODHD_API_TOKEN")
        if token: return token
        try: return st.secrets.get("EODHD_API_TOKEN")  # type: ignore[attr-defined]
        except Exception: return None

    def _safe_request(url:str, params:Dict[str,str], timeout:int=20):
        try:
            r = requests.get(url, params=params, timeout=timeout)
            if r.status_code==200:
                data = r.json()
                if isinstance(data, list): return data
                if isinstance(data, dict):
                    for k in ("events","earnings","data","items"):
                        if k in data and isinstance(data[k], list): return data[k]
                    return [data]
            else:
                st.warning(f"EODHD HTTP {r.status_code}: {r.text[:200]}")
        except Exception as e:
            st.error(f"Request error: {e}")
        return []

    @st.cache_data(ttl=300, show_spinner=False)
    def fetch_economic_events(token:str, start:str, end:str):
        base = "https://eodhd.com/api/economic-events"
        params = {"from":start,"to":end,"api_token":token,"fmt":"json","limit":"2000"}
        data = _safe_request(base, params)
        if not data: return pd.DataFrame(columns=["date","country","event","impact","actual","estimate","previous","unit"])
        df = pd.DataFrame(data).rename(columns={"importance":"impact"})
        if "date" in df: df["date"] = pd.to_datetime(df["date"], errors="coerce")
        keep = [c for c in ["date","country","event","impact","actual","estimate","previous","unit","source"] if c in df.columns]
        return df[keep].sort_values("date").reset_index(drop=True)

    @st.cache_data(ttl=300, show_spinner=False)
    def fetch_earnings(token:str, start:str, end:str, symbols:str=""):
        base = "https://eodhd.com/api/calendar/earnings"
        params = {"from":start,"to":end,"api_token":token,"fmt":"json","limit":"5000"}
        if symbols.strip(): params["symbols"] = symbols.replace(" ","")
        data = _safe_request(base, params)
        if not data: return pd.DataFrame(columns=["reportDate","time","symbol","exchange","name","epsEstimated","epsActual"])
        df = pd.DataFrame(data).rename(columns={"code":"symbol","epsEstimate":"epsEstimated"})
        if "reportDate" in df: df["reportDate"] = pd.to_datetime(df["reportDate"], errors="coerce")
        keep = [c for c in ["reportDate","time","symbol","exchange","name","epsEstimated","epsActual","revenueEstimated","revenueActual","currency"] if c in df.columns]
        return df[keep].sort_values(["reportDate","symbol"] if "symbol" in df.columns else ["reportDate"]).reset_index(drop=True)

    # Controls (compact, inline)
    start_default = date.today() - timedelta(days=3)
    end_default   = date.today() + timedelta(days=14)
    with left:
        st.markdown('<div class="section-card">', unsafe_allow_html=True)
        d1, d2 = st.columns(2)
        with d1:
            econ_dates = st.date_input("Date range", (start_default, end_default), key="econ_dates_inline")
        with d2:
            econ_impact = st.multiselect("Impact filter", ["low","medium","high"], key="econ_impact_inline")
        st.markdown('</div>', unsafe_allow_html=True)
    with right:
        st.markdown('<div class="section-card">', unsafe_allow_html=True)
        s1, s2 = st.columns([2,1])
        with s1:
            earn_symbols = st.text_input("Symbols (comma, optional)", key="earn_symbols_inline", placeholder="AAPL,MSFT,TSLA")
        with s2:
            st.write(" ")  # spacing
            if st.button("🔄 Refresh", key="earn_refresh_inline"):
                st.cache_data.clear()
        st.markdown('</div>', unsafe_allow_html=True)

    # Dates
    if isinstance(econ_dates, tuple) and len(econ_dates)==2:
        start_date, end_date = econ_dates
    else:
        start_date, end_date = start_default, end_default

    token = _get_token()
    if not token:
        with left:  st.error("Set *EODHD_API_TOKEN* in env or st.secrets.")
        with right: st.stop()

    # Fetch + show
    econ_df = fetch_economic_events(token, start_date.strftime("%Y-%m-%d"), end_date.strftime("%Y-%m-%d"))
    earn_df = fetch_earnings(token, start_date.strftime("%Y-%m-%d"), end_date.strftime("%Y-%m-%d"), earn_symbols or "")

    # Apply simple filters
    if econ_impact and "impact" in econ_df.columns:
        econ_df = econ_df[econ_df["impact"].astype(str).str.lower().isin([x.lower() for x in econ_impact])]

    # Render tables
    with left:
        st.markdown(f"*Results:* <span class='metric-pill'>{len(econ_df)}</span>", unsafe_allow_html=True)
        cols = [c for c in ["date","country","event","impact","actual","estimate","previous","unit","source"] if c in econ_df.columns]
        st.dataframe(econ_df[cols], use_container_width=True, hide_index=True)
        st.download_button("⬇ Download Economic Events (CSV)", econ_df.to_csv(index=False).encode("utf-8"),
                           file_name=f"economic_{start_date}_{end_date}.csv", mime="text/csv")

    with right:
        st.markdown(f"*Results:* <span class='metric-pill'>{len(earn_df)}</span>", unsafe_allow_html=True)
        for c in ("epsEstimated","epsActual","revenueEstimated","revenueActual"):
            if c in earn_df.columns: earn_df[c] = pd.to_numeric(earn_df[c], errors="coerce")
        cols = [c for c in ["reportDate","time","symbol","exchange","name","epsEstimated","epsActual","revenueEstimated","revenueActual","currency"] if c in earn_df.columns]
        st.dataframe(earn_df[cols], use_container_width=True, hide_index=True)
        st.download_button("⬇ Download Earnings (CSV)", earn_df.to_csv(index=False).encode("utf-8"),
                           file_name=f"earnings_{start_date}_{end_date}.csv", mime="text/csv") 

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
        st.info("No reports/usa_morning.md file yet — it will appear once your Morning Digest cron runs.")

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
            src = n.get("source", "")
            ts = n.get("ts", "")
            url = n.get("url", "")
            with st.container(border=True):
                st.markdown(f"{title}")
                meta = " • ".join([x for x in [src, ts] if x])
                if meta:
                    st.caption(meta)
                if url:
                    st.link_button("Open", url, use_container_width=True)
    else:
        st.info("data/news.json is empty. Your vega-home-feeds cron will populate this automatically.")

st.markdown("---")
render_queue()
