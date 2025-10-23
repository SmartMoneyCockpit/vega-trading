
# 20_USA_Scanner.py
# USA-only Scanner (EMAs + Wedges + Momentum) with TradingView preview and Today Queue
# Data: EODHD (https://eodhd.com) with EODHD_API_TOKEN
# Integrations: src.engine.smart_money (optional), src.components.today_queue (optional), src.components.tradingview_widgets.advanced_chart

import os, json, math, time, requests, pandas as pd, numpy as np, streamlit as st
from datetime import date, timedelta
from typing import Optional, Dict, List

# ---------- Page ----------
st.set_page_config(page_title="USA Scanner", page_icon="🛰️", layout="wide")
st.title("🛰️ USA Scanner (EMAs + Wedges + Momentum)")

# ---------- Optional integrations ----------
try:
    from src.engine.smart_money import passes_rules as sm_passes, make_light_badge
    HAS_SM = True
except Exception:
    HAS_SM = False
    def make_light_badge(x): return "🟢 PASS" if x else "🔴 FAIL"

try:
    from src.components.today_queue import add as add_to_queue
    HAS_QUEUE = True
except Exception:
    HAS_QUEUE = False
    _STORE = os.getenv("VEGA_TODAY_TRADES_PATH", "data/vega/today_trades.json")
    def add_to_queue(symbol, region="USA"):
        os.makedirs(os.path.dirname(_STORE), exist_ok=True)
        data = {"tickers": []}
        if os.path.exists(_STORE):
            try:
                with open(_STORE,"r",encoding="utf-8") as f: data = json.load(f)
            except Exception: pass
        rec = {"symbol": symbol, "region": region}
        if rec not in data["tickers"]:
            data["tickers"].append(rec)
            with open(_STORE,"w",encoding="utf-8") as f: json.dump(data,f,indent=2)

try:
    from src.components.tradingview_widgets import advanced_chart
    HAS_TV = True
except Exception:
    HAS_TV = False

# ---------- Token ----------
def _token()->Optional[str]:
    tok = os.getenv("EODHD_API_TOKEN")
    if tok: return tok
    try: return st.secrets.get("EODHD_API_TOKEN")  # type: ignore[attr-defined]
    except Exception: return None

TOKEN = _token()
if not TOKEN:
    st.error("Missing **EODHD_API_TOKEN**. Set it in env or st.secrets and rerun.")
    st.stop()

# ---------- Helpers ----------
def _eod_symbol(sym: str)->str:
    # Force USA format for EODHD
    if "." in sym:  # allow explicit overrides like AAPL.US
        return sym
    return f"{sym.upper()}.US"

def _tv_symbol(sym: str)->str:
    # For TradingView preview
    if ":" in sym: return sym
    return sym.upper()

def parse_symbols(s: str)->List[str]:
    if not s.strip(): return []
    raw = [x.strip().upper() for x in s.replace("\\n", ",").split(",")]
    return [x for x in raw if x]

@st.cache_data(ttl=300, show_spinner=False)
def fetch_ohlcv(symbol_eod: str, start: str, end: str, token: str) -> pd.DataFrame:
    url = f"https://eodhd.com/api/eod/{symbol_eod}"
    params = {"from": start, "to": end, "api_token": token, "fmt": "json", "period":"d"}
    try:
        r = requests.get(url, params=params, timeout=20)
        if r.status_code != 200: return pd.DataFrame()
        data = r.json()
        df = pd.DataFrame(data)
        if df.empty: return df
        df["date"] = pd.to_datetime(df["date"])
        df = df.rename(columns={"open":"Open","high":"High","low":"Low","close":"Close","volume":"Volume"})
        return df.sort_values("date").reset_index(drop=True)
    except Exception:
        return pd.DataFrame()

def ema(series: pd.Series, length:int) -> pd.Series:
    return series.ewm(span=length, adjust=False).mean()

def rsi(series: pd.Series, length:int=14) -> pd.Series:
    delta = series.diff()
    up = np.where(delta>0, delta, 0.0)
    down = np.where(delta<0, -delta, 0.0)
    roll_up = pd.Series(up).rolling(length).mean()
    roll_down = pd.Series(down).rolling(length).mean()
    rs = roll_up / (roll_down.replace(0, np.nan))
    return pd.Series(100 - (100/(1+rs)), index=series.index)

def atr(df: pd.DataFrame, length:int=14) -> pd.Series:
    hl = (df["High"] - df["Low"]).abs()
    hc = (df["High"] - df["Close"].shift()).abs()
    lc = (df["Low"] - df["Close"].shift()).abs()
    tr = pd.concat([hl, hc, lc], axis=1).max(axis=1)
    return tr.rolling(length).mean()

def indicators(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out["EMA20"]  = ema(out["Close"], 20)
    out["EMA50"]  = ema(out["Close"], 50)
    out["EMA200"] = ema(out["Close"], 200)
    out["RSI14"]  = rsi(out["Close"], 14)
    out["ATR14"]  = atr(out, 14)
    out["AvgVol20"]= out["Volume"].rolling(20).mean()
    out["High20"] = out["High"].rolling(20).max()
    out["Low20"]  = out["Low"].rolling(20).min()
    return out

# Linear regression helpers for wedge detection
def _linreg(x, y):
    x = np.asarray(x, dtype=float); y = np.asarray(y, dtype=float)
    n = len(x); 
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
    m_hi, b_hi, m_lo, b_lo, fit = _channel_slope_quality(highs, lows)
    cond = (m_hi > 0) and (m_lo > 0) and (m_hi < m_lo)   # both rising, narrowing
    score = float(fit + (m_lo - m_hi))
    return cond, score

def is_falling_wedge(df: pd.DataFrame):
    highs = df["High"].values; lows = df["Low"].values
    m_hi, b_hi, m_lo, b_lo, fit = _channel_slope_quality(highs, lows)
    cond = (m_hi < 0) and (m_lo < 0) and (m_lo > m_hi)   # both falling, narrowing
    score = float(fit + (m_lo - m_hi))
    return cond, score

# Strategy taggers (USA only)
def tag_long(row):
    return bool(row["EMA20"] > row["EMA50"] > row["EMA200"] and row["Close"] > row["EMA20"] and row["RSI14"] >= 50)

def tag_short(row):
    return bool(row["EMA20"] < row["EMA50"] < row["EMA200"] and row["Close"] < row["EMA20"] and row["RSI14"] <= 50)

def tag_momentum(row):
    return bool(row["EMA20"] > row["EMA50"] > row["EMA200"]
                and row["RSI14"] >= 60
                and row["Close"] >= 0.98*(row["High20"] or row["Close"])
                and row["Volume"] >= 1.2*(row["AvgVol20"] or 1))

# ---------- UI: Controls (inline, no sidebar) ----------
left, right = st.columns([3,2], gap="large")

with left:
    st.subheader("Scanner & Chart (USA only)")
    scan_type = st.radio(
        "Scan type",
        ["Rising Wedge","Falling Wedge","Long Stock","Short Stock","High Momentum Stock"],
        horizontal=True,
    )
    default_symbol = st.text_input("Chart symbol (TradingView format)", value="NASDAQ:QQQ")
    st.link_button("🔗 Open in TradingView", f"https://www.tradingview.com/chart/?symbol={default_symbol}", use_container_width=True)

    if HAS_TV:
        advanced_chart(default_symbol, height=620)
    else:
        st.info("advanced_chart() not found — skipping embedded chart.")

with right:
    st.subheader("Universe & Run")
    symbols_txt = st.text_area(
        "USA Symbols (comma or newline)",
        "AAPL, MSFT, NVDA, AMZN, META, TSLA, QQQ, SPY",
        height=90
    )
    lookback = st.slider("Lookback bars", min_value=150, max_value=1500, value=420, step=10)
    apply_sm = st.checkbox("Apply Smart Money pre-filter (if available)", value=True)

    run_col, clear_col = st.columns([2,1])
    if run_col.button("🚀 Run USA Scanner", use_container_width=True):
        st.session_state["scan_go"] = True
    if clear_col.button("🧹 Clear"):
        st.session_state["scan_go"] = False
        st.session_state["scan_df"] = pd.DataFrame()

# ---------- Scan ----------
go = st.session_state.get("scan_go", False)
start = (date.today() - timedelta(days=int(max(lookback*1.2, 200)))).strftime("%Y-%m-%d")
end   = date.today().strftime("%Y-%m-%d")

def run_scan(symbols: List[str], kind: str) -> pd.DataFrame:
    rows = []
    for sym in symbols:
        df = fetch_ohlcv(_eod_symbol(sym), start, end, TOKEN)
        if df.empty or len(df) < 120: 
            continue
        df = indicators(df).tail(lookback)
        row = df.iloc[-1].copy()
        # Wedges evaluated on last N bars window
        if kind == "Rising Wedge" or kind == "Falling Wedge":
            W = min(120, len(df))
            dwindow = df.tail(W)
            ok, sc = (is_rising_wedge(dwindow) if kind=="Rising Wedge" else is_falling_wedge(dwindow))
            flag = ok
        elif kind == "Long Stock":
            flag, sc = tag_long(row), float(row.get("RSI14", 0))
        elif kind == "Short Stock":
            flag, sc = tag_short(row), float(100 - row.get("RSI14", 0))
        else:  # High Momentum
            flag, sc = tag_momentum(row), float(row.get("RSI14", 0))

        if not flag:
            continue

        sm_ok = True
        if apply_sm and HAS_SM:
            try:
                sm_ok = bool(sm_passes(df))  # pass full df to your engine
            except Exception:
                sm_ok = True  # don't block if engine errors

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
            "Score": round(float(sc), 4),
            "Tag": kind,
        })
    return pd.DataFrame(rows)

if go:
    with st.spinner("Scanning USA symbols…"):
        symbols = parse_symbols(symbols_txt)
        df_out = run_scan(symbols, scan_type)
        st.session_state["scan_df"] = df_out
        st.success(f"Done. Matches: {len(df_out)}")

# ---------- Display ----------
df_out = st.session_state.get("scan_df", pd.DataFrame())
if not df_out.empty:
    st.markdown("#### 📋 Results")
    df_out = df_out.sort_values(["Score","RSI14"], ascending=[False, False]).reset_index(drop=True)
    st.dataframe(df_out, use_container_width=True, hide_index=True)

    c1, c2, c3 = st.columns([1,1,1])
    with c1:
        st.download_button("⬇️ Download CSV", df_out.to_csv(index=False).encode("utf-8"),
                           file_name=f"usa_scanner_{scan_type.replace(' ','_')}.csv", mime="text/csv")
    with c2:
        if st.button("➕ Add ALL to Today's Queue", use_container_width=True):
            for sym in df_out["Symbol"].tolist():
                add_to_queue(sym, "USA")
            st.success("Queued all results to Today's Trades.")
    with c3:
        picked = st.selectbox("Preview / queue single", options=df_out["Symbol"].tolist())
        if st.button("Add selected to Today's Queue", use_container_width=True):
            add_to_queue(picked, "USA")
            st.toast(f"Queued {picked}")

    # TradingView preview
    st.markdown("#### 📈 Preview (TradingView)")
    import streamlit.components.v1 as components
    tv_sym = _tv_symbol(picked if 'picked' in locals() else df_out['Symbol'].iloc[0])
    components.html(f"""
    <div class="tradingview-widget-container">
      <div id="tv_scanner"></div>
      <script type="text/javascript" src="https://s3.tradingview.com/tv.js"></script>
      <script type="text/javascript">
        new TradingView.widget({{
          "container_id": "tv_scanner",
          "symbol": "{tv_sym}",
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
    st.info("Run the scanner to see results.")
