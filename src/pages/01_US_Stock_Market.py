# US_Stock_Market.py
# USA Text Dashboard — EODHD-backed Scanner + Always-on Earnings + TV Calendar + News
# Env: EODHD_API_TOKEN in env or st.secrets

import os, json, math, time, requests, pandas as pd, numpy as np, streamlit as st
from datetime import date, timedelta, datetime
from typing import Optional, Dict, List
import urllib.parse

# ──────────────────────────────────────────────────────────────────────────────
# Optional integrations
# ──────────────────────────────────────────────────────────────────────────────
try:
    from src.components.tradingview_widgets import advanced_chart
    HAS_TV_WIDGETS = True
except Exception:
    HAS_TV_WIDGETS = False

try:
    from src.engine.smart_money import make_light_badge, passes_rules as sm_passes
    HAS_SM = True
except Exception:
    HAS_SM = False
    def make_light_badge(x): return "USA Dashboard Ready"

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
                with open(_STORE, "r", encoding="utf-8") as f: data = json.load(f)
            except Exception: pass
        rec = {"symbol": symbol, "region": region}
        if rec not in data["tickers"]:
            data["tickers"].append(rec)
            with open(_STORE, "w", encoding="utf-8") as f: json.dump(data, f, indent=2)
    def render_queue():
        st.subheader("📌 Today's Trades Queue")
        if os.path.exists(_STORE):
            try:
                with open(_STORE, "r", encoding="utf-8") as f: d = json.load(f)
            except Exception: d = {"tickers":[]}
        else:
            d = {"tickers":[]}
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
# EODHD token & helpers
# ──────────────────────────────────────────────────────────────────────────────
def _token()->Optional[str]:
    tok = os.getenv("EODHD_API_TOKEN")
    if tok: return tok
    try: return st.secrets.get("EODHD_API_TOKEN")  # type: ignore[attr-defined]
    except Exception: return None

TOKEN = _token()
if not TOKEN:
    st.warning("Set **EODHD_API_TOKEN** in your env or st.secrets to enable scanner, earnings, and news.")

def _safe_get(url: str, params: Dict, timeout: int = 25):
    try:
        r = requests.get(url, params=params, timeout=timeout)
        if r.status_code == 200:
            return r.json()
        return None
    except Exception:
        return None

# ──────────────────────────────────────────────────────────────────────────────
# EODHD APIs: Search, Screener (best-effort), OHLCV, Earnings, News
# ──────────────────────────────────────────────────────────────────────────────
@st.cache_data(ttl=300, show_spinner=False)
def eod_search_us(query: str, token: str) -> pd.DataFrame:
    if not query.strip(): return pd.DataFrame(columns=["Code","Exchange","Name"])
    url = f"https://eodhd.com/api/search/{urllib.parse.quote(query.strip())}"
    params = {"api_token": token, "limit": "50"}
    data = _safe_get(url, params) or []
    df = pd.DataFrame(data)
    if df.empty: return df
    us_ex = {"NYSE","NASDAQ","AMEX","BATS","ARCX","OTC","NYSE MKT"}
    if "Exchange" in df.columns:
        df = df[df["Exchange"].astype(str).str.upper().isin(us_ex)]
    keep = [c for c in ["Code","Exchange","Name"] if c in df.columns]
    return df[keep].drop_duplicates().reset_index(drop=True)

@st.cache_data(ttl=300, show_spinner=False)
def eod_screener_us(kind: str, token: str) -> List[str]:
    base = "https://eodhd.com/api/screener"
    params: Dict[str,str] = {"api_token": token, "country": "US", "limit": "200"}
    if kind == "Long Stock":
        params.update({"trend": "bullish"})
    elif kind == "Short Stock":
        params.update({"trend": "bearish"})
    elif kind == "High Momentum Stock":
        params.update({"momentum": "high"})
    elif kind in ("Rising Wedge","Falling Wedge"):
        params.update({"pattern": "wedge"})
    data = _safe_get(base, params)
    if not data: return []
    df = pd.DataFrame(data)
    if df.empty: return []
    cand = []
    for col in ["code","symbol","Code","Symbol"]:
        if col in df.columns:
            cand = df[col].astype(str).str.upper().tolist()
            break
    out, seen = [], set()
    for s in cand:
        s = s.split(".")[0] if "." in s else s
        if s and s not in seen:
            out.append(s); seen.add(s)
    return out[:200]

@st.cache_data(ttl=300, show_spinner=False)
def fetch_ohlcv(symbol_eod: str, start: str, end: str, token: str) -> pd.DataFrame:
    url = f"https://eodhd.com/api/eod/{symbol_eod}"
    params = {"from": start, "to": end, "api_token": token, "fmt": "json", "period": "d"}
    data = _safe_get(url, params)
    if not data: return pd.DataFrame()
    df = pd.DataFrame(data)
    if df.empty: return df
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df = df.rename(columns={"open":"Open","high":"High","low":"Low","close":"Close","volume":"Volume"})
    return df.sort_values("date").reset_index(drop=True)

def _eod_us(sym: str) -> str:
    sym = sym.strip().upper()
    if "." in sym: return sym
    return f"{sym}.US"

@st.cache_data(ttl=300, show_spinner=False)
def eod_earnings(from_date: str, to_date: str, token: str) -> pd.DataFrame:
    base = "https://eodhd.com/api/calendar/earnings"
    params = {"from": from_date, "to": to_date, "api_token": token, "fmt": "json", "limit": "5000"}
    data = _safe_get(base, params) or []
    if not data: return pd.DataFrame()
    df = pd.DataFrame(data).rename(columns={"code":"symbol","epsEstimate":"epsEstimated"})
    if "reportDate" in df.columns:
        df["reportDate"] = pd.to_datetime(df["reportDate"], errors="coerce")
    keep = [c for c in ["reportDate","time","symbol","exchange","name","epsEstimated","epsActual","revenueEstimated","revenueActual","currency"] if c in df.columns]
    return df[keep].sort_values(["reportDate","symbol"] if "symbol" in df.columns else ["reportDate"]).reset_index(drop=True)

@st.cache_data(ttl=300, show_spinner=False)
def eod_news(from_date: str, to_date: str, token: str) -> pd.DataFrame:
    base = "https://eodhd.com/api/news"
    params = {"from": from_date, "to": to_date, "api_token": token, "fmt": "json", "limit": "100"}
    data = _safe_get(base, params) or []
    df = pd.DataFrame(data)
    if df.empty: return df
    for c in ["date","publishedDate","time"]:
        if c in df.columns:
            df["ts"] = pd.to_datetime(df[c], errors="coerce")
            break
    keep = [c for c in ["ts","title","content","link","symbols","source","author"] if c in df.columns]
    if not keep: return pd.DataFrame()
    return df[keep].sort_values("ts", ascending=False).reset_index(drop=True)

# ──────────────────────────────────────────────────────────────────────────────
# Indicators & patterns
# ──────────────────────────────────────────────────────────────────────────────
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
    out["EMA20"]  = ema(out["Close"], 20)
    out["EMA50"]  = ema(out["Close"], 50)
    out["EMA200"] = ema(out["Close"], 200)
    out["RSI14"]  = rsi(out["Close"], 14)
    out["ATR14"]  = atr(out, 14)
    out["AvgVol20"]= out["Volume"].rolling(20).mean()
    out["High20"]  = out["High"].rolling(20).max()
    out["Low20"]   = out["Low"].rolling(20).min()
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
    fit_hi = -np.mean(np.abs((m_hi*idx + b_hi) - highs))
    fit_lo = -np.mean(np.abs((m_lo*idx + b_lo) - lows))
    fit = (fit_hi + fit_lo) / 2.0
    return (m_hi, b_hi, m_lo, b_lo, fit)

def is_rising_wedge(df: pd.DataFrame):
    highs = df["High"].values; lows = df["Low"].values
    m_hi, _, m_lo, _, fit = _channel_slope_quality(highs, lows)
    cond = (m_hi > 0) and (m_lo > 0) and (m_hi < m_lo)
    score = float(fit + (m_lo - m_hi))
    return cond, score

def is_falling_wedge(df: pd.DataFrame):
    highs = df["High"].values; lows = df["Low"].values
    m_hi, _, m_lo, _, fit = _channel_slope_quality(highs, lows)
    cond = (m_hi < 0) and (m_lo < 0) and (m_lo > m_hi)
    score = float(fit + (m_lo - m_hi))
    return cond, score

def tag_long(row: pd.Series) -> bool:
    return bool(row["EMA20"] > row["EMA50"] > row["EMA200"] and row["Close"] > row["EMA20"] and row["RSI14"] >= 50)

def tag_short(row: pd.Series) -> bool:
    return bool(row["EMA20"] < row["EMA50"] < row["EMA200"] and row["Close"] < row["EMA20"] and row["RSI14"] <= 50)

def tag_momentum(row: pd.Series) -> bool:
    return bool(row["EMA20"] > row["EMA50"] > row["EMA200"]
                and row["RSI14"] >= 60
                and row["Close"] >= 0.98*(row["High20"] or row["Close"])
                and row["Volume"] >= 1.2*(row["AvgVol20"] or 1))

# ──────────────────────────────────────────────────────────────────────────────
# Scanner & Chart
# ──────────────────────────────────────────────────────────────────────────────
st.markdown("### 🔎 Scanner & Chart")
left, right = st.columns([3,2], gap="large")

with left:
    scan_kind = st.radio(
        "Scan type",
        ["Rising Wedge","Falling Wedge","Long Stock","Short Stock","High Momentum Stock"],
        horizontal=True,
    )

    default_symbol = st.text_input("Symbol (TradingView format)", value="AAPL")
    st.link_button("🔗 Open in TradingView",
                   f"https://www.tradingview.com/chart/?symbol={default_symbol}",
                   use_container_width=True)
    if HAS_TV_WIDGETS:
        advanced_chart(default_symbol, height=720)
    else:
        st.info("`advanced_chart()` not found. Chart embed skipped.")

    # Optional vector metrics
    csv_path = os.path.join("data/eod/us",
                            (default_symbol.split(":")[-1] if ":" in default_symbol else default_symbol) + ".csv")
    if HAS_VECTOR and os.path.exists(csv_path):
        try:
            df_csv = pd.read_csv(csv_path)
            m = compute_from_df(df_csv)
            c1, c2, c3, c4, c5 = st.columns(5)
            c1.metric("RT", m["RT"]); c2.metric("RV", m["RV"]); c3.metric("RS", m["RS"]); c4.metric("CI", m["CI"]); c5.metric("VST", m["VST"])
        except Exception as e:
            st.caption(f"Vector metrics unavailable (CSV issue): {e}")
    else:
        st.caption("Vector metrics appear when a local CSV exists for the selected symbol (data/eod/us/).")

with right:
    st.subheader("Universe & Scan (EODHD-first)")

    # EODHD Screener call (server-side)
    eod_candidates = []
    if TOKEN:
        if st.button("🔎 Find Candidates via EODHD Screener"):
            with st.spinner("Querying EODHD screener…"):
                eod_candidates = eod_screener_us(scan_kind, TOKEN)
            if eod_candidates:
                st.session_state["usa_universe"] = sorted(set(eod_candidates))
                st.success(f"Got {len(eod_candidates)} candidates from EODHD.")
            else:
                st.info("Screener returned nothing (or plan doesn't support it). You can still scan via client fallback below.")

    # Search helper and manual add
    if "usa_universe" not in st.session_state:
        st.session_state["usa_universe"] = []
    search_q = st.text_input("Search EODHD (ticker or company)")
    s1, s2 = st.columns([1,1])
    if s1.button("Search"):
        if not TOKEN: st.error("EODHD token missing.")
        else:
            df_s = eod_search_us(search_q, TOKEN)
            st.session_state["last_search_df"] = df_s
    df_s = st.session_state.get("last_search_df", pd.DataFrame())
    if not df_s.empty:
        st.caption("Search results (US):")
        picks = st.multiselect(
            "Select symbols to add",
            options=[f"{r.Code} — {r.Name} ({r.Exchange})" for r in df_s.itertuples()],
            default=[],
        )
        if s2.button("➕ Add selected"):
            for p in picks:
                sym = p.split(" — ")[0].strip().upper()
                if sym not in st.session_state["usa_universe"]:
                    st.session_state["usa_universe"].append(sym)
            st.success("Added to universe.")

    manual = st.text_area("Or paste symbols (comma/newline)", "", height=80)
    if st.button("➕ Add pasted"):
        raw = [x.strip().upper() for x in manual.replace("\n", ",").split(",") if x.strip()]
        for sym in raw:
            if sym not in st.session_state["usa_universe"]:
                st.session_state["usa_universe"].append(sym)
        st.success("Added pasted symbols.")

    universe = sorted(set(st.session_state["usa_universe"]))
    st.caption(f"Universe size: **{len(universe)}**")
    if universe: st.code(", ".join(universe), language="text")

    lookback = st.number_input("Lookback bars", min_value=150, max_value=3000, value=420, step=10)
    apply_sm = st.checkbox("Apply Smart Money pre-filter (if available)", value=True)

    if "us_scan_df" not in st.session_state:
        st.session_state["us_scan_df"] = pd.DataFrame()

    @st.cache_data(ttl=300, show_spinner=False)
    def run_scan(symbols: List[str], kind: str, lookback: int, token: str) -> pd.DataFrame:
        start = (date.today() - timedelta(days=int(max(lookback * 1.2, 200)))).strftime("%Y-%m-%d")
        end   = date.today().strftime("%Y-%m-%d")
        rows = []
        for sym in symbols:
            df = fetch_ohlcv(_eod_us(sym), start, end, token)
            if df.empty or len(df) < 120: 
                continue
            df = compute_indicators(df).tail(lookback)
            row = df.iloc[-1].copy()
            if kind in ("Rising Wedge","Falling Wedge"):
                W = min(120, len(df)); window = df.tail(W)
                ok, score = (is_rising_wedge(window) if kind=="Rising Wedge" else is_falling_wedge(window))
            elif kind == "Long Stock":
                ok, score = tag_long(row), float(row.get("RSI14", 0))
            elif kind == "Short Stock":
                ok, score = tag_short(row), float(100 - row.get("RSI14", 0))
            else:
                ok, score = tag_momentum(row), float(row.get("RSI14", 0))
            if not ok: 
                continue
            sm_ok = True
            if apply_sm and HAS_SM:
                try: sm_ok = bool(sm_passes(df))
                except Exception: sm_ok = True
            if not sm_ok: 
                continue
            rows.append({
                "Symbol": sym.upper(), "Tag": kind, "Score": round(float(score), 4),
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
            })
        return pd.DataFrame(rows)

    r1, r2 = st.columns([2,1])
    if r1.button("🚀 Run Scanner", use_container_width=True):
        if not TOKEN:
            st.error("EODHD token missing — set EODHD_API_TOKEN.")
        elif not universe:
            st.warning("Universe is empty. Use EODHD Screener or Search above, or paste tickers, then run again.")
        else:
            with st.spinner("Scanning USA symbols…"):
                res = run_scan(universe, scan_kind, lookback, TOKEN)
            st.session_state["us_scan_df"] = res
            st.success("Scanner finished.")

    if r2.button("🗑️ Clear Results", use_container_width=True):
        st.session_state["us_scan_df"] = pd.DataFrame()

    res = st.session_state["us_scan_df"]
    if not res.empty:
        res = res.sort_values(["Score","RSI14"], ascending=[False, False]).reset_index(drop=True)
        st.dataframe(
            res[["Symbol","Tag","Score","Close","EMA20","EMA50","EMA200","RSI14","ATR14","Vol","AvgVol20","High20","Low20"]],
            use_container_width=True, hide_index=True
        )
        pick = st.selectbox("Preview / Queue", res["Symbol"].tolist())
        c1, c2, c3 = st.columns([1,1,1])
        with c1:
            st.download_button("⬇️ CSV", res.to_csv(index=False).encode("utf-8"),
                               file_name=f"usa_scan_{scan_kind.replace(' ','_')}.csv", mime="text/csv")
        with c2:
            if st.button("➕ Add Selected to Today's Queue", use_container_width=True):
                add_to_queue(pick, "USA"); st.toast(f"Added {pick}")
        with c3:
            if st.button("➕ Add ALL to Today's Queue", use_container_width=True):
                for s in res["Symbol"].tolist(): add_to_queue(s, "USA")
                st.success("Queued all results.")

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
        st.info("Use **EODHD Screener** or **Search** to build a universe, then click **Run Scanner**.")

st.markdown("---")

# ──────────────────────────────────────────────────────────────────────────────
# Economic Calendar + Earnings
# ──────────────────────────────────────────────────────────────────────────────
st.header("🗓️ Economic Calendar & 💼 Earnings (Split View)")

st.markdown("""
<style>
.inline-black-divider{width:100%;height:600px;min-height:600px;background:#000;border-radius:8px;}
.section-card{padding:.6rem .8rem;border:1px solid rgba(255,255,255,.08);border-radius:12px;background:rgba(255,255,255,.02);}
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
    st.subheader("💼 Earnings (EODHD • Always On)")
    today = date.today()
    d1, d2 = st.columns(2)
    with d1:
        earn_start = st.date_input("From", value=today - timedelta(days=1), key="earn_from")
    with d2:
        earn_end   = st.date_input("To",   value=today + timedelta(days=14), key="earn_to")
    if TOKEN:
        with st.spinner("Loading earnings…"):
            df_e = eod_earnings(earn_start.strftime("%Y-%m-%d"), earn_end.strftime("%Y-%m-%d"), TOKEN)
        if not df_e.empty:
            if "exchange" in df_e.columns:
                df_e = df_e[df_e["exchange"].astype(str).str.contains("US|NYSE|NASDAQ|AMEX|BATS|ARCX|OTC", case=False, na=True)]
            st.dataframe(df_e, use_container_width=True, hide_index=True)
            st.download_button("⬇️ Download Earnings (CSV)",
                               df_e.to_csv(index=False).encode("utf-8"),
                               file_name=f"earnings_{earn_start}_{earn_end}.csv",
                               mime="text/csv")
        else:
            st.info("No earnings returned for this window or API rate-limited.")
    else:
        st.caption("Set EODHD_API_TOKEN to show earnings here.")

st.markdown("---")

# ──────────────────────────────────────────────────────────────────────────────
# Morning Report & News (EODHD News feed)
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
        st.caption("No `reports/usa_morning.md` yet. Using EODHD News on the right.")

with c2:
    st.subheader("Market News (EODHD)")
    if TOKEN:
        to_dt = date.today()
        from_dt = to_dt - timedelta(days=3)
        with st.spinner("Fetching EODHD News…"):
            news_df = eod_news(from_dt.strftime("%Y-%m-%d"), to_dt.strftime("%Y-%m-%d"), TOKEN)
        if not news_df.empty:
            for r in news_df.head(12).itertuples():
                with st.container(border=True):
                    st.markdown(f"**{getattr(r,'title','(no title)')}**")
                    meta_parts = []
                    if getattr(r,'source',None): meta_parts.append(str(r.source))
                    if getattr(r,'ts',None): meta_parts.append(str(getattr(r,'ts')))
                    if meta_parts: st.caption(" • ".join(meta_parts))
                    link = getattr(r,'link',None)
                    if link: st.link_button("Open", link, use_container_width=True)
        else:
            st.info("No news returned by EODHD for the selected window.")
    else:
        st.caption("Set EODHD_API_TOKEN to enable EODHD news.")

st.markdown("---")

# ──────────────────────────────────────────────────────────────────────────────
# Today's Trades Queue
# ──────────────────────────────────────────────────────────────────────────────
render_queue()
