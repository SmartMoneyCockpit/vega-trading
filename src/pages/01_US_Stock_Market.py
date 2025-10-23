# US_Stock_Market.py
# USA Text Dashboard — A/B Smart Money Scanner (Minimal Filters) + Earnings + TV Calendar + News
# Requires: EODHD_API_TOKEN in env or st.secrets
# Also uses: yfinance (pip install yfinance)

import os, json, requests, pandas as pd, numpy as np, streamlit as st
from datetime import date, timedelta
from typing import Optional, Dict, List, Tuple
from collections import Counter

# ──────────────────────────────────────────────────────────────────────────────
# Optional libs
# ──────────────────────────────────────────────────────────────────────────────
try:
    import yfinance as yf
    HAS_YF = True
except Exception:
    HAS_YF = False

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
# Page
# ──────────────────────────────────────────────────────────────────────────────
st.set_page_config(page_title="USA Text Dashboard", page_icon="🗺️", layout="wide")
st.title("USA Text Dashboard — A/B Smart Money")
st.success(make_light_badge("USA"))

# ──────────────────────────────────────────────────────────────────────────────
# Token / HTTP helpers
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
# EODHD APIs
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
# Indicators (minimal)
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
    out["EMA20"]   = ema(out["Close"], 20)
    out["EMA50"]   = ema(out["Close"], 50)
    out["EMA200"]  = ema(out["Close"], 200)
    out["RSI14"]   = rsi(out["Close"], 14)
    out["ATR14"]   = atr(out, 14)
    out["AvgVol30"]= out["Volume"].rolling(30).mean()
    out["High20"]  = out["High"].rolling(20).max()
    out["Low20"]   = out["Low"].rolling(20).min()
    return out

# ──────────────────────────────────────────────────────────────────────────────
# Minimal Vector-style metrics
# ──────────────────────────────────────────────────────────────────────────────
def score_rt(df: pd.DataFrame) -> float:
    if len(df) < 60: return 0.0
    c = df["Close"]
    r4 = (c.iloc[-1] / c.iloc[-20] - 1.0) if len(c) >= 20 else 0.0
    r12 = (c.iloc[-1] / c.iloc[-60] - 1.0) if len(c) >= 60 else 0.0
    val = 1.0 + 0.6*r4 + 0.4*r12
    return round(float(max(0.0, val)), 3)

def score_rs(df: pd.DataFrame) -> float:
    if len(df) < 60: return 0.0
    ret = df["Close"].pct_change().dropna()
    vol = ret.rolling(20).std().iloc[-1] if len(ret) >= 20 else ret.std()
    if vol is None or vol == 0 or np.isnan(vol): return 1.0
    rs = 1.0 / float(vol * 15)
    return round(float(min(max(rs, 0.1), 2.0)), 3)

def score_rv(price: float, eps: Optional[float], grt: Optional[float]) -> float:
    if eps is None or eps <= 0 or grt is None or np.isnan(grt): 
        return 1.0
    pe = price / eps if eps else np.nan
    if not pe or pe <= 0: return 1.0
    peg = pe / max(grt, 0.01)
    rv = 1.5 / peg
    return round(float(min(max(rv, 0.1), 2.0)), 3)

def score_vst(rt: float, rv: float, rs: float) -> float:
    return round(float(0.4*rt + 0.3*rv + 0.3*rs), 3)

def score_ci(df: pd.DataFrame) -> float:
    if len(df) < 60: return 0.8
    ok_trend = (df["EMA20"].iloc[-1] > df["EMA50"].iloc[-1] > df["EMA200"].iloc[-1])
    dd = (df["High20"].iloc[-1] - df["Low20"].iloc[-1]) / max(df["High20"].iloc[-1], 1e-9)
    ci = 1.2 if ok_trend else 0.8
    ci -= 0.5*dd
    return round(float(min(max(ci, 0.1), 1.5)), 3)

def compute_stop(row: pd.Series) -> float:
    return round(float(row["EMA50"] - 2.0*row["ATR14"]), 4)

# ──────────────────────────────────────────────────────────────────────────────
# Minimal A/B setup gates (lowest safe thresholds)
# ──────────────────────────────────────────────────────────────────────────────
def gate_long_minimal(row: pd.Series) -> bool:
    # Lowest safe: basic up-bias + not weak momentum
    up_bias = (row["EMA20"] >= row["EMA50"]) or (row["Close"] >= row["EMA20"])
    rsi_ok  = row["RSI14"] >= 45
    return bool(up_bias and rsi_ok)

def gate_short_minimal(row: pd.Series) -> bool:
    # Lowest safe: basic down-bias + not overbought
    down_bias = (row["EMA20"] <= row["EMA50"]) or (row["Close"] <= row["EMA20"])
    rsi_ok    = row["RSI14"] <= 55
    return bool(down_bias and rsi_ok)

def decide_buy_today(row: pd.Series, is_long: bool, rt: float, vst: float) -> Tuple[str, float, float]:
    # Gentle "A+1" logic — prefer trend alignment, allow mild pullbacks
    if is_long:
        ok_now = (row["EMA20"] >= row["EMA50"]) and (row["RSI14"] >= 50) and (row["Close"] >= 0.97*(row["High20"] or row["Close"]))
        almost = (row["EMA20"] >= row["EMA50"]) and (row["RSI14"] >= 45)
    else:
        ok_now = (row["EMA20"] <= row["EMA50"]) and (row["RSI14"] <= 50) and (row["Close"] <= 1.03*(row["Low20"] or row["Close"]))
        almost = (row["EMA20"] <= row["EMA50"]) and (row["RSI14"] <= 55)

    entry = float(row["Close"])
    stop  = compute_stop(row)

    if ok_now and rt >= 1.0 and vst >= 0.9:
        return ("Buy Today", entry, stop)
    if almost and rt >= 0.9 and vst >= 0.85:
        return ("Buy in 2–3 days", entry, stop)
    return ("Wait", entry, stop)

# ──────────────────────────────────────────────────────────────────────────────
# Smart Money tracer
# ──────────────────────────────────────────────────────────────────────────────
def _sm_eval(symbol: str, price=None, ctx=None):
    if not HAS_SM:
        return False, ["smart_money_not_loaded"]
    try:
        ok, details = sm_passes(symbol=symbol, price=price, context=ctx, return_details=True)
        reasons = details.get("fail_reasons", []) if not ok else []
        return ok, reasons
    except TypeError:
        try:
            ok = sm_passes(symbol)
            return (ok, [] if ok else ["failed_unknown"])
        except Exception as e:
            return False, [f"error:{type(e).__name__}"]

def _render_sm_summary(total_checked: int, reasons_counter: Counter, fail_examples_df: pd.DataFrame):
    st.markdown(f"**Smart Money filter summary:** checked `{total_checked}` symbols")
    if reasons_counter:
        st.markdown("**Top filter reasons**")
        for r, n in reasons_counter.most_common(12):
            st.write(f"- {r} → {n}")
    if isinstance(fail_examples_df, pd.DataFrame) and not fail_examples_df.empty:
        st.markdown("**Examples (failed):**")
        st.dataframe(fail_examples_df.head(25), use_container_width=True, height=360)

# ──────────────────────────────────────────────────────────────────────────────
# UI — Two-option Scanner (A=Long, B=Short)
# ──────────────────────────────────────────────────────────────────────────────
st.markdown("### 🔎 A/B Smart Money Scanner (Minimal Filters)")
left, right = st.columns([3, 2], gap="large")

if "preview_symbol" not in st.session_state:
    st.session_state["preview_symbol"] = "AAPL"

with left:
    mode = st.radio("Mode", ["A — Long (Smart Money)","B — Short (Smart Money)"], horizontal=True)
    default_symbol = st.text_input("Symbol (TradingView format)", value=st.session_state["preview_symbol"])
    st.session_state["preview_symbol"] = default_symbol
    st.link_button("🔗 Open in TradingView", f"https://www.tradingview.com/chart/?symbol={default_symbol}", use_container_width=True)
    if HAS_TV_WIDGETS:
        advanced_chart(st.session_state["preview_symbol"], height=720)
    else:
        st.info("`advanced_chart()` not found. Chart embed skipped.")

with right:
    st.subheader("Universe Scan (USA)")
    lookback     = st.number_input("Lookback bars", 150, 3000, 420, 10)
    apply_sm     = st.checkbox("Apply Smart Money pre-filter", value=True)
    max_checks   = st.number_input("HARD CAP: symbols to process", 50, 2000, 200, 50)
    max_results  = st.number_input("Max matches to return", 5, 2000, 200, 5)
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
                if "Type" in df_all.columns:
                    df_all = df_all[~df_all["Type"].astype(str).str.contains("ETF|ETN|FUND|PREF|ADR|RIGHT|WARRANT", case=True, na=False)]
                pool = df_all["Code"].astype(str).str.upper().dropna().drop_duplicates().tolist() if "Code" in df_all.columns else []
                st.session_state["us_symbol_pool"] = pool
                st.success(f"Loaded {len(pool)} US symbols.")

    pool = st.session_state.get("us_symbol_pool", [])

    if "us_scan_df" not in st.session_state:
        st.session_state["us_scan_df"] = pd.DataFrame()
    if "us_sm_counts" not in st.session_state:
        st.session_state["us_sm_counts"] = Counter()
    if "us_sm_fail_examples" not in st.session_state:
        st.session_state["us_sm_fail_examples"] = pd.DataFrame()

    # Minimal floors (liquidity only)
    MIN_ABS_VOLUME = 100_000   # keep liquidity sane; RVOL requirement removed

    @st.cache_data(ttl=300, show_spinner=False)
    def _find_matches(is_long: bool, lookback: int, token: str, pool: List[str],
                      start_offset: int, max_checks: int, max_results: int,
                      apply_sm_flag: bool):
        start = (date.today() - timedelta(days=int(max(lookback * 1.2, 200)))).strftime("%Y-%m-%d")
        end   = date.today().strftime("%Y-%m-%d")
        out = []
        processed = 0

        reasons_counter = Counter()
        fail_rows: List[Dict] = []

        for sym in pool[start_offset:]:
            if processed >= int(max_checks):
                break
            df = fetch_ohlcv(_eod_us(sym), start, end, token)
            processed += 1
            if df.empty or len(df) < 120:
                reasons_counter["data_insufficient"] += 1
                fail_rows.append({"Symbol": sym, "Reason": "data_insufficient"})
                continue

            df = df.tail(max(lookback, 120))
            df = compute_indicators(df)
            row = df.iloc[-1]

            # Liquidity only (no RVOL gate)
            vol_today = float(row.get("Volume") or 0.0)
            if vol_today < MIN_ABS_VOLUME:
                reasons_counter["liquidity_abs_floor"] += 1
                fail_rows.append({"Symbol": sym, "Reason": "liquidity_abs_floor"})
                continue

            # Minimal setup gates
            ok_setup = gate_long_minimal(row) if is_long else gate_short_minimal(row)
            if not ok_setup:
                reasons = "long_setup_min_fail" if is_long else "short_setup_min_fail"
                reasons_counter[reasons] += 1
                fail_rows.append({"Symbol": sym, "Reason": reasons})
                continue

            # Smart Money prefilter (kept)
            sm_ok = True
            sm_reasons: List[str] = []
            if apply_sm_flag and HAS_SM:
                ok, r = _sm_eval(sym, price=float(row["Close"]), ctx={"benchmark":"SPY"})
                sm_ok = bool(ok); sm_reasons = r
            if not sm_ok:
                if not sm_reasons:
                    sm_reasons = ["smart_money_fail"]
                for rr in sm_reasons:
                    reasons_counter[rr] += 1
                fail_rows.append({"Symbol": sym, "Reason": ", ".join(sm_reasons)[:240]})
                continue

            # Scores (light)
            rt = score_rt(df)
            rs = score_rs(df)
            eps = None; grt = None; sector = None; sales_growth = None
            if HAS_YF:
                try:
                    info = yf.Ticker(sym).info
                    eps = info.get("trailingEps", None)
                    grt = info.get("earningsGrowth", None)
                    sector = info.get("sector", None)
                    sales_growth = info.get("revenueGrowth", None)
                except Exception:
                    pass
            rv  = score_rv(float(row["Close"]), eps, grt if grt is not None else (sales_growth if sales_growth is not None else 0.1))
            vst = score_vst(rt, rv, rs)
            ci  = score_ci(df)

            label, entry, stop = decide_buy_today(row, is_long, rt, vst)
            if label == "Wait":
                reasons_counter["buy_logic_wait"] += 1
                fail_rows.append({"Symbol": sym, "Reason": "buy_logic_wait"})
                continue

            pct_prc = (row["Close"] / df["Close"].iloc[-2] - 1.0)*100.0 if len(df) >= 2 else 0.0
            chg = row["Close"] - df["Close"].iloc[-2] if len(df) >= 2 else 0.0

            out.append({
                "Symbol": sym.upper(),
                "Side": "LONG" if is_long else "SHORT",
                "Sector": sector or "",
                "$ Change (From Yesterday)": round(float(chg), 4),
                "% PRC": round(float(pct_prc), 2),
                "RS": round(float(rs), 3),
                "RT": round(float(rt), 3),
                "VST": round(float(vst), 3),
                "CI": round(float(ci), 3),
                "Stop": round(float(stop), 4),
                "EPS": round(float(eps), 3) if eps not in (None, np.nan) else None,
                "Volume": int(vol_today),
                "Buy Today": label,
            })
            if len(out) >= int(max_results):
                break

        df_out = pd.DataFrame(out)
        fail_df = pd.DataFrame(fail_rows)
        total_checked = processed

        if not df_out.empty:
            by = [c for c in ["VST","RS","RT","Symbol"] if c in df_out.columns]
            asc = [False, False, False, True][:len(by)]
            df_out = df_out.sort_values(by=by, ascending=asc).reset_index(drop=True)

        return df_out, reasons_counter, fail_df, total_checked

    if st.button("🚀 Scan (A/B)", use_container_width=True):
        if not TOKEN:
            st.error("EODHD token missing — set EODHD_API_TOKEN.")
        elif not pool:
            st.warning("Load the US symbol list first (click 'Load US symbol list').")
        else:
            with st.spinner("Scanning…"):
                is_long = (mode.startswith("A"))
                res, sm_counts, sm_fail_df, total_checked = _find_matches(
                    is_long, lookback, TOKEN, pool, int(start_offset), int(max_checks), int(max_results), apply_sm
                )
            st.session_state["us_scan_df"] = res
            st.session_state["us_sm_counts"] = sm_counts
            st.session_state["us_sm_fail_examples"] = sm_fail_df
            st.success(f"Done. Checked: {total_checked} • Matches: {len(res)}")

    # Results + Smart Money drop-off explanation
    res = st.session_state.get("us_scan_df", pd.DataFrame())
    sm_counts = st.session_state.get("us_sm_counts", Counter())
    sm_fail_df = st.session_state.get("us_sm_fail_examples", pd.DataFrame())

    _render_sm_summary(
        total_checked = (0 if sm_counts is None else (sum(sm_counts.values()) + len(res))),
        reasons_counter = sm_counts if isinstance(sm_counts, Counter) else Counter(),
        fail_examples_df = sm_fail_df if isinstance(sm_fail_df, pd.DataFrame) else pd.DataFrame()
    )

    if not res.empty:
        st.markdown("### Smart Money — Passed")
        show_cols = [c for c in ["Symbol","Side","Sector","% PRC","RS","RT","VST","Volume","Buy Today"] if c in res.columns]
        st.dataframe(res[show_cols], use_container_width=True, hide_index=True)

        st.caption("Click a row below to expand, preview in TradingView, and add to Today’s Queue.")
        for r in res.itertuples(index=False):
            header = f"{getattr(r,'Symbol')} [{getattr(r,'Side')}] — {getattr(r,'Sector','')}"
            with st.expander(header):
                cA, cB = st.columns([1,1])
                with cA:
                    if st.button(f"🔍 Preview {getattr(r,'Symbol')}", key=f"preview_{getattr(r,'Symbol')}"):
                        st.session_state["preview_symbol"] = getattr(r,'Symbol')
                        st.rerun()
                    try:
                        st.write(pd.Series(r._asdict(), name="Details"))
                    except Exception:
                        st.write(res.loc[res["Symbol"]==getattr(r,'Symbol')].T)
                with cB:
                    if st.button(f"➕ Add {getattr(r,'Symbol')} to Today's Queue", key=f"queue_{getattr(r,'Symbol')}"):
                        add_to_queue(getattr(r,'Symbol'), "USA"); st.toast(f"Added {getattr(r,'Symbol')}")

        pick = st.selectbox("Quick Preview / Queue", res["Symbol"].tolist())
        c1, c2, c3 = st.columns([1,1,1])
        with c1:
            st.download_button("⬇️ CSV", res.to_csv(index=False).encode("utf-8"),
                               file_name=f"usa_scan_AB.csv", mime="text/csv")
        with c2:
            if st.button("➕ Add Selected to Today's Queue", use_container_width=True):
                add_to_queue(pick, "USA"); st.toast(f"Added {pick}")
        with c3:
            if st.button("➕ Add ALL to Today's Queue", use_container_width=True):
                for s in res["Symbol"].tolist(): add_to_queue(s, "USA")
                st.success("Queued all results.")
    else:
        st.info("No final matches. See **Top filter reasons** above to adjust thresholds (e.g., earnings window via Smart Money, liquidity floors).")

# ──────────────────────────────────────────────────────────────────────────────
# Economic Calendar & Earnings
# ──────────────────────────────────────────────────────────────────────────────
st.markdown("---")
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

# ──────────────────────────────────────────────────────────────────────────────
# Morning Report & News
# ──────────────────────────────────────────────────────────────────────────────
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
