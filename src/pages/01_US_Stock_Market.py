# US_Stock_Market.py
# USA Text Dashboard — Scanner (EMA-based) + Econ/Earnings split + Morning Report + Queue
# Data feed: EODHD (set EODHD_API_TOKEN in env or st.secrets)

import os, json, math, time, requests, pandas as pd, numpy as np, streamlit as st
from datetime import date, timedelta, datetime
from typing import Optional, Dict, List

# ──────────────────────────────────────────────────────────────────────────────
# Optional project integrations (graceful fallbacks if missing)
# ──────────────────────────────────────────────────────────────────────────────
try:
    from src.components.tradingview_widgets import advanced_chart, economic_calendar
    HAS_TV_WIDGETS = True
except Exception:
    HAS_TV_WIDGETS = False

try:
    from src.engine.smart_money import make_light_badge, passes_rules as sm_passes
    HAS_SMART_MONEY = True
except Exception:
    HAS_SMART_MONEY = False
    def make_light_badge(x):  # simple fallback
        return f"USA Dashboard Ready"

try:
    from src.components.today_queue import add as add_to_queue, render as render_queue
    HAS_QUEUE = True
except Exception:
    HAS_QUEUE = False
    _STORE = os.getenv("VEGA_TODAY_TRADES_PATH", "data/vega/today_trades.json")
    def add_to_queue(symbol: str, region: str = "USA"):
        os.makedirs(os.path.dirname(_STORE), exist_ok=True)
        data = {"tickers": []}
        if os.path.exists(_STORE):
            try:
                with open(_STORE, "r", encoding="utf-8") as f:
                    data = json.load(f)
            except Exception:
                pass
        rec = {"symbol": symbol, "region": region}
        if rec not in data["tickers"]:
            data["tickers"].append(rec)
            with open(_STORE, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
    def render_queue():
        st.subheader("📌 Today's Trades Queue")
        if os.path.exists(_STORE):
            try:
                with open(_STORE, "r", encoding="utf-8") as f:
                    d = json.load(f)
            except Exception:
                d = {"tickers": []}
        else:
            d = {"tickers": []}
        if not d.get("tickers"):
            st.caption("No tickers yet. Add from the scanner.")
            return
        for rec in d["tickers"]:
            st.write(f"- **{rec.get('symbol','?')}** ({rec.get('region','?')})")

try:
    from src.engine.vector_metrics import compute_from_df
    HAS_VECTOR = True
except Exception:
    HAS_VECTOR = False

# ──────────────────────────────────────────────────────────────────────────────
# Page setup
# ──────────────────────────────────────────────────────────────────────────────
st.set_page_config(page_title="USA Text Dashboard", page_icon="🗺️", layout="wide")
st.title("USA Text Dashboard")
st.success(make_light_badge("USA"))

# ──────────────────────────────────────────────────────────────────────────────
# EODHD token
# ──────────────────────────────────────────────────────────────────────────────
def _token() -> Optional[str]:
    tok = os.getenv("EODHD_API_TOKEN")
    if tok:
        return tok
    try:
        return st.secrets.get("EODHD_API_TOKEN")  # type: ignore[attr-defined]
    except Exception:
        return None

TOKEN = _token()
if not TOKEN:
    st.warning("Set **EODHD_API_TOKEN** in your environment or `st.secrets` to enable the scanner and earnings fallback.")

# ──────────────────────────────────────────────────────────────────────────────
# Utilities (EODHD, indicators, wedges, strategy tags)
# ──────────────────────────────────────────────────────────────────────────────
@st.cache_data(ttl=300, show_spinner=False)
def fetch_ohlcv(symbol_eod: str, start: str, end: str, token: str) -> pd.DataFrame:
    """EODHD daily candles for USA: SYMBOL.US"""
    url = f"https://eodhd.com/api/eod/{symbol_eod}"
    params = {"from": start, "to": end, "api_token": token, "fmt": "json", "period": "d"}
    try:
        r = requests.get(url, params=params, timeout=20)
        if r.status_code != 200:
            return pd.DataFrame()
        data = r.json()
        df = pd.DataFrame(data)
        if df.empty:
            return df
        df["date"] = pd.to_datetime(df["date"])
        df = df.rename(columns={"open": "Open", "high": "High", "low": "Low", "close": "Close", "volume": "Volume"})
        return df.sort_values("date").reset_index(drop=True)
    except Exception:
        return pd.DataFrame()

def _eod_us(sym: str) -> str:
    if "." in sym:
        return sym  # allow AAPL.US
    return f"{sym.upper()}.US"

def ema(series: pd.Series, length: int) -> pd.Series:
    return series.ewm(span=length, adjust=False).mean()

def rsi(series: pd.Series, length: int = 14) -> pd.Series:
    delta = series.diff()
    up = np.where(delta > 0, delta, 0.0)
    down = np.where(delta < 0, -delta, 0.0)
    roll_up = pd.Series(up).rolling(length).mean()
    roll_down = pd.Series(down).rolling(length).mean()
    rs = roll_up / (roll_down.replace(0, np.nan))
    return pd.Series(100 - (100 / (1 + rs)), index=series.index)

def atr(df: pd.DataFrame, length: int = 14) -> pd.Series:
    hl = (df["High"] - df["Low"]).abs()
    hc = (df["High"] - df["Close"].shift()).abs()
    lc = (df["Low"] - df["Close"].shift()).abs()
    tr = pd.concat([hl, hc, lc], axis=1).max(axis=1)
    return tr.rolling(length).mean()

def compute_indicators(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out["EMA20"] = ema(out["Close"], 20)
    out["EMA50"] = ema(out["Close"], 50)
    out["EMA200"] = ema(out["Close"], 200)
    out["RSI14"] = rsi(out["Close"], 14)
    out["ATR14"] = atr(out, 14)
    out["AvgVol20"] = out["Volume"].rolling(20).mean()
    out["High20"] = out["High"].rolling(20).max()
    out["Low20"] = out["Low"].rolling(20).min()
    return out

def _linreg(x, y):
    x = np.asarray(x, dtype=float); y = np.asarray(y, dtype=float)
    n = len(x)
    if n < 2: return (0.0, 0.0)
    A = np.vstack([x, np.ones(n)]).T
    m, b = np.linalg.lstsq(A, y, rcond=None)[0]
    return (m, b)

def _channel_slope_quality(highs, lows):
    idx = np.arange(len(highs))
    m_hi, b_hi = _linreg(idx, highs)
    m_lo, b_lo = _linreg(idx, lows)
    fit_hi = -np.mean(np.abs((m_hi * idx + b_hi) - highs))
    fit_lo = -np.mean(np.abs((m_lo * idx + b_lo) - lows))
    fit = (fit_hi + fit_lo) / 2.0
    return (m_hi, b_hi, m_lo, b_lo, fit)

def is_rising_wedge(df: pd.DataFrame):
    highs = df["High"].values; lows = df["Low"].values
    m_hi, _, m_lo, _, fit = _channel_slope_quality(highs, lows)
    cond = (m_hi > 0) and (m_lo > 0) and (m_hi < m_lo)   # rising & narrowing
    score = float(fit + (m_lo - m_hi))
    return cond, score

def is_falling_wedge(df: pd.DataFrame):
    highs = df["High"].values; lows = df["Low"].values
    m_hi, _, m_lo, _, fit = _channel_slope_quality(highs, lows)
    cond = (m_hi < 0) and (m_lo < 0) and (m_lo > m_hi)   # falling & narrowing
    score = float(fit + (m_lo - m_hi))
    return cond, score

def tag_long(row: pd.Series) -> bool:
    return bool(row["EMA20"] > row["EMA50"] > row["EMA200"] and row["Close"] > row["EMA20"] and row["RSI14"] >= 50)

def tag_short(row: pd.Series) -> bool:
    return bool(row["EMA20"] < row["EMA50"] < row["EMA200"] and row["Close"] < row["EMA20"] and row["RSI14"] <= 50)

def tag_momentum(row: pd.Series) -> bool:
    return bool(row["EMA20"] > row["EMA50"] > row["EMA200"]
                and row["RSI14"] >= 60
                and row["Close"] >= 0.98 * (row["High20"] or row["Close"])
                and row["Volume"] >= 1.2 * (row["AvgVol20"] or 1))

# ──────────────────────────────────────────────────────────────────────────────
# Scanner & Chart (USA only)
# ──────────────────────────────────────────────────────────────────────────────
st.markdown("### 🔎 Scanner & Chart")
left, right = st.columns([3, 2], gap="large")

with left:
    scan_kind = st.radio(
        "Scan type",
        ["Rising Wedge", "Falling Wedge", "Long Stock", "Short Stock", "High Momentum Stock"],
        horizontal=True,
    )

    default_symbol = st.text_input("Symbol (TradingView format)", value="NASDAQ:QQQ")
    st.link_button("🔗 Open in TradingView",
                   f"https://www.tradingview.com/chart/?symbol={default_symbol}",
                   use_container_width=True)

    if HAS_TV_WIDGETS:
        advanced_chart(default_symbol, height=720)
    else:
        st.info("`advanced_chart()` not found. Chart embed skipped.")

    # Vector metrics (optional from local CSV)
    csv_path = os.path.join("data/eod/us",
                            (default_symbol.split(":")[-1] if ":" in default_symbol else default_symbol) + ".csv")
    if HAS_VECTOR and os.path.exists(csv_path):
        try:
            df_csv = pd.read_csv(csv_path)
            m = compute_from_df(df_csv)
            c1, c2, c3, c4, c5 = st.columns(5)
            c1.metric("RT", m["RT"])
            c2.metric("RV", m["RV"])
            c3.metric("RS", m["RS"])
            c4.metric("CI", m["CI"])
            c5.metric("VST", m["VST"])
        except Exception as e:
            st.caption(f"Vector metrics unavailable (CSV issue): {e}")
    else:
        st.caption("Vector metrics appear when a local CSV exists for the selected symbol (data/eod/us/).")

with right:
    st.subheader("Local Scans (USA)")
    symbols_txt = st.text_area(
        "Symbols (comma or newline separated)",
        "AAPL, MSFT, NVDA, AMZN, META, TSLA, QQQ, SPY",
        height=80
    )
    lookback = st.number_input("Lookback bars", min_value=150, max_value=3000, value=420, step=10)
    apply_sm = st.checkbox("Apply Smart Money pre-filter (if available)", value=True)

    if "us_scan_df" not in st.session_state:
        st.session_state["us_scan_df"] = pd.DataFrame()

    def parse_symbols(s: str) -> List[str]:
        if not s:
            return []
        raw = [x.strip().upper() for x in s.replace("\n", ",").split(",")]
        return [x for x in raw if x]

    def run_scan(symbols: List[str], kind: str) -> pd.DataFrame:
        if not TOKEN:
            st.error("EODHD token missing — set EODHD_API_TOKEN.")
            return pd.DataFrame()

        start = (date.today() - timedelta(days=int(max(lookback * 1.2, 200)))).strftime("%Y-%m-%d")
        end = date.today().strftime("%Y-%m-%d")
        rows = []
        for sym in symbols:
            df = fetch_ohlcv(_eod_us(sym), start, end, TOKEN)
            if df.empty or len(df) < 120:
                continue
            df = compute_indicators(df).tail(lookback)
            row = df.iloc[-1].copy()

            # Pattern/strategy decision
            if kind == "Rising Wedge" or kind == "Falling Wedge":
                W = min(120, len(df))
                window = df.tail(W)
                ok, score = (is_rising_wedge(window) if kind == "Rising Wedge" else is_falling_wedge(window))
            elif kind == "Long Stock":
                ok, score = tag_long(row), float(row.get("RSI14", 0))
            elif kind == "Short Stock":
                ok, score = tag_short(row), float(100 - row.get("RSI14", 0))
            else:  # High Momentum
                ok, score = tag_momentum(row), float(row.get("RSI14", 0))

            if not ok:
                continue

            # Smart Money pre-filter (if available)
            sm_ok = True
            if apply_sm and HAS_SMART_MONEY:
                try:
                    sm_ok = bool(sm_passes(df))  # your engine decides using full history
                except Exception:
                    sm_ok = True  # don't block on engine errors

            if not sm_ok:
                continue

            rows.append({
                "Symbol": sym.upper(),
                "Close": round(float(row["Close"]), 4),
                "EMA20": round(float(row["EMA20"]), 4),
                "EMA50": round(float(row["EMA50"]), 4),
                "EMA200": round(float(row["EMA200"]), 4),
                "RSI14": round(float(row["RSI14"]), 2),
                "ATR14": round(float(row["ATR14"]), 4),
                "Vol": int(row["Volume"]),
                "AvgVol20": int(row["AvgVol20"]),
                "High20": round(float(row["High20"]), 4),
                "Low20": round(float(row["Low20"]), 4),
                "Score": round(float(score), 4),
                "Tag": kind
            })
        return pd.DataFrame(rows)

    run_col, clear_col = st.columns([2, 1])
    if run_col.button("🔍 Run Scanner", use_container_width=True):
        syms = parse_symbols(symbols_txt)
        if not syms:
            st.warning("Please provide at least one symbol.")
        else:
            with st.spinner("Scanning USA symbols…"):
                res = run_scan(syms, scan_kind)
            st.session_state["us_scan_df"] = res
            st.success("Scanner finished.")

    if clear_col.button("🗑️ Clear", use_container_width=True):
        st.session_state["us_scan_df"] = pd.DataFrame()

    res = st.session_state["us_scan_df"]
    if not res.empty:
        res = res.sort_values(["Score", "RSI14"], ascending=[False, False]).reset_index(drop=True)
        st.dataframe(
            res[["Symbol", "Tag", "Score", "Close", "EMA20", "EMA50", "EMA200", "RSI14", "ATR14", "Vol", "AvgVol20", "High20", "Low20"]],
            use_container_width=True, hide_index=True
        )

        pick = st.selectbox("Preview / Queue", res["Symbol"].tolist())
        c1, c2, c3 = st.columns([1, 1, 1])
        with c1:
            st.download_button("⬇️ CSV", res.to_csv(index=False).encode("utf-8"),
                               file_name=f"usa_scan_{scan_kind.replace(' ','_')}.csv", mime="text/csv")
        with c2:
            if st.button("➕ Add Selected to Today's Queue", use_container_width=True):
                add_to_queue(pick, "USA")
                st.toast(f"Added {pick}")
        with c3:
            if st.button("➕ Add ALL to Today's Queue", use_container_width=True):
                for s in res["Symbol"].tolist():
                    add_to_queue(s, "USA")
                st.success("Queued all results.")

        # TV preview
        import streamlit.components.v1 as components
        tv_symbol = pick if ":" in pick else pick
        st.markdown("#### 📈 Preview (TradingView)")
        components.html(f"""
        <div class="tradingview-widget-container">
          <div id="tv_scanner"></div>
          <script type="text/javascript" src="https://s3.tradingview.com/tv.js"></script>
          <script type="text/javascript">
            new TradingView.widget({{
              "container_id": "tv_scanner",
              "symbol": "{tv_symbol}",
              "interval": "D",
              "timezone": "Etc/UTC",
              "theme": "dark",
              "style": "1",
              "locale": "en",
              "studies": ["EMA@tv-basicstudies","EMA@tv-basicstudies","EMA@tv-basicstudies","RSI@tv-basicstudies"],
              "withdateranges": true,
              "details": true,
              "calendar": true,
              "autosize": true,
              "height": 560
            }});
          </script>
        </div>
        """, height=560, scrolling=False)
    else:
        st.info("Click **Run Scanner** to generate results.")

st.markdown("---")

# ──────────────────────────────────────────────────────────────────────────────
# Economic Calendar + Earnings (Split View) — TradingView embeds + fallback
# ──────────────────────────────────────────────────────────────────────────────
st.header("🗓️ Economic Calendar & 💼 Earnings (Split View)")

# Styling: black divider
st.markdown("""
<style>
.inline-black-divider{
  width:100%;
  height:600px;
  min-height:600px;
  background:#000;
  border-radius:8px;
}
</style>
""", unsafe_allow_html=True)

col_left, col_mid, col_right = st.columns([0.475, 0.05, 0.475], gap="small")

import streamlit.components.v1 as components

with col_left:
    st.subheader("📆 Economic Calendar (TradingView • USA/CAD/MXN)")
    components.html("""
    <div class="tradingview-widget-container">
      <div class="tradingview-widget-container__widget"></div>
      <script type="text/javascript" src="https://s3.tradingview.com/external-embedding/embed-widget-events.js" async>
      {
        "colorTheme": "dark",
        "isTransparent": true,
        "width": "100%",
        "height": "600",
        "locale": "en",
        "importanceFilter": "-1,0,1",
        "currencyFilter": "USD,CAD,MXN"
      }
      </script>
    </div>
    """, height=620, scrolling=False)

with col_mid:
    st.markdown('<div class="inline-black-divider"></div>', unsafe_allow_html=True)

with col_right:
    st.subheader("💼 Upcoming Earnings (TradingView • US)")
    components.html("""
    <div class="tradingview-widget-container">
      <div class="tradingview-widget-container__widget"></div>
      <script type="text/javascript"
              src="https://s3.tradingview.com/external-embedding/embed-widget-earnings.js" async>
      {
        "colorTheme": "dark",
        "isTransparent": true,
        "width": "100%",
        "height": "600",
        "locale": "en",
        "exchange": "US"
      }
      </script>
    </div>
    """, height=620, scrolling=False)

# Fallback earnings table (EODHD) — expands only if needed
def _safe_request(url, params):
    try:
        r = requests.get(url, params=params, timeout=20)
        if r.status_code == 200:
            return r.json()
    except Exception:
        pass
    return []

def _earnings_df(tok, start, end):
    base = "https://eodhd.com/api/calendar/earnings"
    params = {"from": start, "to": end, "api_token": tok, "fmt": "json", "limit": "2000"}
    data = _safe_request(base, params)
    if not data:
        return pd.DataFrame()
    df = pd.DataFrame(data).rename(columns={"code": "symbol", "epsEstimate": "epsEstimated"})
    if "reportDate" in df.columns:
        df["reportDate"] = pd.to_datetime(df["reportDate"], errors="coerce")
    keep = [c for c in ["reportDate","time","symbol","exchange","name","epsEstimated","epsActual","revenueEstimated","revenueActual","currency"] if c in df.columns]
    return df[keep].sort_values(["reportDate","symbol"] if "symbol" in df.columns else ["reportDate"]).reset_index(drop=True)

with st.expander("🧰 Fallback: Earnings table (EODHD)", expanded=False):
    if TOKEN:
        today = date.today()
        start = (today - timedelta(days=1)).strftime("%Y-%m-%d")
        end = (today + timedelta(days=14)).strftime("%Y-%m-%d")
        df_e = _earnings_df(TOKEN, start, end)
        if not df_e.empty:
            st.dataframe(df_e, use_container_width=True, hide_index=True)
            st.download_button("⬇️ Download Earnings (CSV)",
                               df_e.to_csv(index=False).encode("utf-8"),
                               file_name=f"earnings_{start}_{end}.csv", mime="text/csv")
        else:
            st.info("No earnings returned by EODHD for this window or API is rate-limited.")
    else:
        st.caption("Set EODHD_API_TOKEN to enable the fallback table.")

st.markdown("---")

# ──────────────────────────────────────────────────────────────────────────────
# Morning Report & News
# ──────────────────────────────────────────────────────────────────────────────
st.header("📰 USA Morning Report & News")
c1, c2 = st.columns(2)

with c1:
    st.subheader("🇺🇸 Morning Report (Latest)")
    report_path = "reports/usa_morning.md"
    if os.path.exists(report_path):
        with open(report_path, "r", encoding="utf-8") as f:
            st.markdown(f.read())
    else:
        st.info("No `reports/usa_morning.md` file yet — it will appear once your Morning Digest cron runs.")

with c2:
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
                st.markdown(f"**{title}**")
                meta = " • ".join([x for x in [src, ts] if x])
                if meta:
                    st.caption(meta)
                if url:
                    st.link_button("Open", url, use_container_width=True)
    else:
        st.info("`data/news.json` is empty. Your feed job will populate this automatically.")

st.markdown("---")

# ──────────────────────────────────────────────────────────────────────────────
# Today's Trades Queue (UI)
# ──────────────────────────────────────────────────────────────────────────────
render_queue()
