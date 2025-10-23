
# US_Stock_Market.py
# USA Text Dashboard — Start-from-zero Pattern Scanner + EODHD Earnings + TV Calendar + EODHD News
# Requires: EODHD_API_TOKEN in env or st.secrets

import os, json, requests, pandas as pd, numpy as np, streamlit as st
from datetime import date, timedelta
from typing import Optional, Dict, List
import urllib.parse

# ──────────────────────────────────────────────────────────────────────────────
# Optional integrations (graceful fallbacks)
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
    def make_light_badge(_: str)->str: return "USA Dashboard Ready"

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
            st.caption("No tickers yet. Add from the scanner."); return
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
    st.warning("Set **EODHD_API_TOKEN** in your environment or `st.secrets` to enable scanner, earnings, and news.")

def _safe_get(url: str, params: Dict, timeout: int = 25):
    try:
        r = requests.get(url, params=params, timeout=timeout)
        if r.status_code == 200:
            return r.json()
    except Exception:
        pass
    return None

# ──────────────────────────────────────────────────────────────────────────────
# EODHD APIs: US symbol list, OHLCV, Earnings, News
# ──────────────────────────────────────────────────────────────────────────────
@st.cache_data(ttl=600, show_spinner=False)
def eod_exchange_symbols_us(token: str) -> pd.DataFrame:
    url = "https://eodhd.com/api/exchange-symbol-list/US"
    params = {"api_token": token, "fmt": "json"}
    data = _safe_get(url, params) or []
    return pd.DataFrame(data)

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
    return sym if "." in sym else f"{sym}.US"

# ──────────────────────────────────────────────────────────────────────────────
# Indicators & pattern logic
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
    if len(x) < 2: return (0.0, 0.0)
    A = np.vstack([x, np.ones(len(x))]).T
    m, b = np.linalg.lstsq(A, y, rcond=None)[0]
    return m, b

def _channel(df: pd.DataFrame):
    idx = np.arange(len(df))
    m_hi, _ = _linreg(idx, df["High"].values)
    m_lo, _ = _linreg(idx, df["Low"].values)
    fit_hi = -np.mean(np.abs((m_hi*idx + df["High"].mean()) - df["High"].values))
    fit_lo = -np.mean(np.abs((m_lo*idx + df["Low"].mean())  - df["Low"].values))
    return m_hi, m_lo, (fit_hi + fit_lo) / 2.0

def is_rising_wedge(df: pd.DataFrame):
    m_hi, m_lo, fit = _channel(df)
    ok = (m_hi > 0) and (m_lo > 0) and (m_hi < m_lo)
    score = float(fit + (m_lo - m_hi))
    return ok, score

def is_falling_wedge(df: pd.DataFrame):
    m_hi, m_lo, fit = _channel(df)
    ok = (m_hi < 0) and (m_lo < 0) and (m_lo > m_hi)
    score = float(fit + (m_lo - m_hi))
    return ok, score

def tag_long(row: pd.Series) -> bool:
    return bool(row["EMA20"] > row["EMA50"] > row["EMA200"] and row["Close"] > row["EMA20"] and row["RSI14"] >= 50)

def tag_short(row: pd.Series) -> bool:
    return bool(row["EMA20"] < row["EMA50"] < row["EMA200"] and row["Close"] < row["EMA20"] and row["RSI14"] <= 50)

def tag_momentum(row: pd.Series) -> bool:
    return bool(row["EMA20"] > row["EMA50"] > row["EMA200"] and row["RSI14"] >= 60 and row["Close"] >= 0.98*(row["High20"] or row["Close"]) and row["Volume"] >= 1.2*(row["AvgVol20"] or 1))

# ──────────────────────────────────────────────────────────────────────────────
# Scanner & Chart
# ──────────────────────────────────────────────────────────────────────────────
st.markdown("### 🔎 Scanner & Chart")
left, right = st.columns([3, 2], gap="large")

with left:
    scan_kind = st.radio("Scan type", ["Rising Wedge","Falling Wedge","Long Stock","Short Stock","High Momentum Stock"], horizontal=True)
    default_symbol = st.text_input("Symbol (TradingView format)", value="AAPL")
    st.link_button("🔗 Open in TradingView", f"https://www.tradingview.com/chart/?symbol={default_symbol}", use_container_width=True)
    if HAS_TV_WIDGETS:
        advanced_chart(default_symbol, height=720)
    else:
        st.info("`advanced_chart()` not found. Chart embed skipped.")

with right:
    st.subheader("Start from Zero — Find Matches")
    lookback     = st.number_input("Lookback bars", 150, 3000, 420, 10)
    apply_sm     = st.checkbox("Apply Smart Money pre-filter (if available)", value=True)
    max_checks   = st.number_input("Max symbols to check (budget)", 50, 5000, 800, 50)
    max_results  = st.number_input("Max matches to return", 5, 1000, 150, 5)
    start_offset = st.number_input("Start offset in symbol list", 0, 50000, 0, 100)

    if "us_symbol_pool" not in st.session_state:
        st.session_state["us_symbol_pool"] = []

    if st.button("📥 Load US symbol list", use_container_width=True):
        if not TOKEN:
            st.error("EODHD token missing — set EODHD_API_TOKEN.")
        else:
            df_all = eod_exchange_symbols_us(TOKEN)
            if df_all.empty:
                st.warning("Could not retrieve US symbol list.")
            else:
                ex_ok = {"NYSE","NASDAQ","AMEX","NYSE MKT","BATS","ARCX","OTC"}
                if "Exchange" in df_all.columns:
                    df_all = df_all[df_all["Exchange"].astype(str).str.upper().isin(ex_ok)]
                if "Code" in df_all.columns:
                    pool = df_all["Code"].astype(str).str.upper().dropna().drop_duplicates().tolist()
                else:
                    pool = []
                st.session_state["us_symbol_pool"] = pool
                st.success(f"Loaded {len(pool)} US symbols.")

    pool = st.session_state.get("us_symbol_pool", [])

    if "us_scan_df" not in st.session_state:
        st.session_state["us_scan_df"] = pd.DataFrame()

    @st.cache_data(ttl=300, show_spinner=False)
    def _find_matches(kind: str, lookback: int, token: str, pool: List[str], start_offset: int, max_checks: int, max_results: int, apply_sm_flag: bool) -> pd.DataFrame:
        from datetime import date, timedelta
        start = (date.today() - timedelta(days=int(max(lookback * 1.2, 200)))).strftime("%Y-%m-%d")
        end   = date.today().strftime("%Y-%m-%d")
        out = []
        checked = 0
        for sym in pool[start_offset: start_offset + max_checks]:
            df = fetch_ohlcv(_eod_us(sym), start, end, token)
            if df.empty or len(df) < 120:
                checked += 1
                continue
            df = df.tail(max(lookback, 120))
            df = compute_indicators(df)
            row = df.iloc[-1]

            if kind in ("Rising Wedge","Falling Wedge"):
                sub = df.tail(min(120, len(df)))
                ok, score = (is_rising_wedge(sub) if kind=="Rising Wedge" else is_falling_wedge(sub))
            elif kind == "Long Stock":
                ok, score = tag_long(row), float(row.get("RSI14", 0))
            elif kind == "Short Stock":
                ok, score = tag_short(row), float(100 - row.get("RSI14", 0))
            else:
                ok, score = tag_momentum(row), float(row.get("RSI14", 0))

            if not ok:
                checked += 1
                continue

            sm_ok = True
            if apply_sm_flag and HAS_SM:
                try: sm_ok = bool(sm_passes(df))
                except Exception: sm_ok = True
            if not sm_ok:
                checked += 1
                continue

            out.append({
                "Symbol": sym.upper(),
                "Tag": kind,
                "Score": round(float(score), 4),
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
            if len(out) >= max_results:
                break
            checked += 1
        return pd.DataFrame(out)

    if st.button("🚀 Find Matches (Start from Zero)", use_container_width=True):
        if not TOKEN:
            st.error("EODHD token missing — set EODHD_API_TOKEN.")
        elif not pool:
            st.warning("Load the US symbol list first (click 'Load US symbol list').")
        else:
            with st.spinner("Scanning for pattern matches…"):
                res = _find_matches(scan_kind, lookback, TOKEN, pool, int(start_offset), int(max_checks), int(max_results), apply_sm)
            st.session_state["us_scan_df"] = res
            st.success(f"Done. Matches: {len(res)}")

    res = st.session_state.get("us_scan_df", pd.DataFrame())
    if not res.empty:
        res = res.sort_values(["Score","RSI14"], ascending=[False, False]).reset_index(drop=True)
        st.dataframe(res, use_container_width=True, hide_index=True)
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
        st.info("Click **Load US symbol list** → **Find Matches** to start from zero.")

st.markdown("---")

# Economic Calendar & Earnings
st.header("🗓️ Economic Calendar & 💼 Earnings (Split View)")
st.markdown("<style>.inline-black-divider{width:100%;height:600px;min-height:600px;background:#000;border-radius:8px;}</style>", unsafe_allow_html=True)
col_left, col_mid, col_right = st.columns([0.475, 0.05, 0.475], gap="small")
import streamlit.components.v1 as components
with col_left:
    st.subheader("📆 Economic Calendar (TradingView • USA/CAD/MXN)")
    components.html("""
    <div class="tradingview-widget-container">
      <div class="tradingview-widget-container__widget"></div>
      <script type="text/javascript" src="https://s3.tradingview.com/external-embedding/embed-widget-events.js" async>
      {"colorTheme":"dark","isTransparent":true,"width":"100%","height":"600","locale":"en","importanceFilter":"-1,0,1","currencyFilter":"USD,CAD,MXN"}
      </script>
    </div>""", height=620, scrolling=False)
with col_mid:
    st.markdown('<div class="inline-black-divider"></div>', unsafe_allow_html=True)
with col_right:
    st.subheader("💼 Earnings (EODHD • Always On)")
    today = date.today()
    d1, d2 = st.columns(2)
    with d1: earn_start = st.date_input("From", value=today - timedelta(days=1), key="earn_from")
    with d2: earn_end   = st.date_input("To",   value=today + timedelta(days=14), key="earn_to")
    if TOKEN:
        from_date = earn_start.strftime("%Y-%m-%d"); to_date = earn_end.strftime("%Y-%m-%d")
        with st.spinner("Loading earnings…"):
            raw = _safe_get("https://eodhd.com/api/calendar/earnings", {"from": from_date,"to": to_date,"api_token": TOKEN,"fmt":"json","limit":"5000"}) or []
            df_e = pd.DataFrame(raw)
        if not df_e.empty:
            if "code" in df_e.columns and "symbol" not in df_e.columns:
                df_e = df_e.rename(columns={"code":"symbol"})
            if "epsEstimate" in df_e.columns and "epsEstimated" not in df_e.columns:
                df_e = df_e.rename(columns={"epsEstimate":"epsEstimated"})
            if "reportDate" in df_e.columns:
                df_e["reportDate"] = pd.to_datetime(df_e["reportDate"], errors="coerce")
            if "exchange" in df_e.columns:
                df_e = df_e[df_e["exchange"].astype(str).str.contains("US|NYSE|NASDAQ|AMEX|BATS|ARCX|OTC", case=False, na=True)]
            keep = [c for c in ["reportDate","time","symbol","exchange","name","epsEstimated","epsActual","revenueEstimated","revenueActual","currency"] if c in df_e.columns]
            if keep: df_e = df_e[keep]
            st.dataframe(df_e.sort_values(["reportDate","symbol"] if "symbol" in df_e.columns else ["reportDate"]), use_container_width=True, hide_index=True)
            st.download_button("⬇️ Download Earnings (CSV)", df_e.to_csv(index=False).encode("utf-8"), file_name=f"earnings_{from_date}_{to_date}.csv", mime="text/csv")
        else:
            st.info("No earnings returned for this window or API rate-limited.")
    else:
        st.caption("Set EODHD_API_TOKEN to show earnings here.")

st.markdown("---")
st.header("📰 USA Morning Report & News")
c1, c2 = st.columns(2)
with c1:
    st.subheader("🇺🇸 Morning Report (Latest)")
    report_path = "reports/usa_morning.md"
    if os.path.exists(report_path):
        with open(report_path, "r", encoding="utf-8") as f: st.markdown(f.read())
    else:
        st.caption("No `reports/usa_morning.md` yet. Using EODHD News on the right.")
with c2:
    st.subheader("Market News (EODHD)")
    if TOKEN:
        to_dt = date.today(); from_dt = to_dt - timedelta(days=3)
        with st.spinner("Fetching EODHD News…"):
            raw_news = _safe_get("https://eodhd.com/api/news", {"from": from_dt.strftime("%Y-%m-%d"), "to": to_dt.strftime("%Y-%m-%d"), "api_token": TOKEN, "fmt":"json", "limit":"100"}) or []
            df_news = pd.DataFrame(raw_news)
        if not df_news.empty:
            ts_col = None
            for c in ["date","publishedDate","time"]:
                if c in df_news.columns: ts_col = c; break
            if ts_col: df_news["ts"] = pd.to_datetime(df_news[ts_col], errors="coerce")
            for r in df_news.sort_values("ts", ascending=False).head(12).itertuples():
                with st.container(border=True):
                    st.markdown(f"**{getattr(r,'title','(no title)')}**")
                    meta = " • ".join([x for x in [getattr(r,'source',None), getattr(r,'ts',None)] if x])
                    if meta: st.caption(meta)
                    link = getattr(r,'link',None)
                    if link: st.link_button("Open", link, use_container_width=True)
        else:
            st.info("No news returned by EODHD for the selected window.")
    else:
        st.caption("Set EODHD_API_TOKEN to enable EODHD news.")

st.markdown("---")
render_queue()
