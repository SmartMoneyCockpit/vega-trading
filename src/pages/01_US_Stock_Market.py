# US_Stock_Market.py
# USA Text Dashboard — A/B Smart Money Scanner + TV Chart + Earnings + News (compact)
# Needs: EODHD_API_TOKEN

import os, json, requests, pandas as pd, numpy as np, streamlit as st
from datetime import date, timedelta
from typing import Optional, Dict, List, Tuple
from collections import Counter
import streamlit.components.v1 as components

# ───────────────────── Optional deps (graceful fallbacks)
try:
    import yfinance as yf; HAS_YF = True
except Exception: HAS_YF = False
try:
    from src.components.tradingview_widgets import advanced_chart; HAS_TV = True
except Exception: HAS_TV = False
try:
    from src.engine.smart_money import make_light_badge, passes_rules as sm_passes; HAS_SM = True
except Exception:
    HAS_SM = False
    def make_light_badge(_: str)->str: return "USA Dashboard Ready"
try:
    from src.components.today_queue import add as add_to_queue, render as render_queue; HAS_QUEUE = True
except Exception:
    HAS_QUEUE = False; _STORE = os.getenv("VEGA_TODAY_TRADES_PATH", "data/vega/today_trades.json")
    def add_to_queue(symbol: str, region: str="USA"):
        os.makedirs(os.path.dirname(_STORE), exist_ok=True)
        d={"tickers":[]}; 
        if os.path.exists(_STORE):
            try: d=json.load(open(_STORE,"r",encoding="utf-8"))
            except Exception: pass
        rec={"symbol":symbol,"region":region}
        if rec not in d["tickers"]:
            d["tickers"].append(rec); json.dump(d, open(_STORE,"w",encoding="utf-8"), indent=2)
    def render_queue():
        st.subheader("📌 Today's Trades Queue")
        d={"tickers":[]}
        if os.path.exists(_STORE):
            try: d=json.load(open(_STORE,"r",encoding="utf-8"))
            except Exception: pass
        if not d.get("tickers"): st.caption("No tickers yet. Add from the scanner."); return
        for r in d["tickers"]: st.write(f"- **{r.get('symbol','?')}** ({r.get('region','?')})")

# ───────────────────── Page
st.set_page_config(page_title="USA Text Dashboard", page_icon="🗺️", layout="wide")
st.title("USA Text Dashboard — A/B Smart Money"); st.success(make_light_badge("USA"))

# ───────────────────── Token + HTTP
def _token()->Optional[str]:
    t=os.getenv("EODHD_API_TOKEN")
    if t: return t
    try: return st.secrets.get("EODHD_API_TOKEN")  # type: ignore[attr-defined]
    except Exception: return None
TOKEN=_token()
if not TOKEN: st.warning("Set **EODHD_API_TOKEN** to enable scanner, earnings, and news.")

def _safe_get(url: str, params: Dict, timeout: int=25):
    try:
        r=requests.get(url, params=params, timeout=timeout); 
        if r.status_code==200: return r.json()
    except Exception: pass
    return None

# ───────────────────── EODHD helpers
@st.cache_data(ttl=600, show_spinner=False)
def eod_exchange_symbols_us(token: str)->pd.DataFrame:
    d=_safe_get("https://eodhd.com/api/exchange-symbol-list/US", {"api_token":token,"fmt":"json"}) or []
    return pd.DataFrame(d)

@st.cache_data(ttl=300, show_spinner=False)
def fetch_ohlcv(sym_eod: str, start: str, end: str, token: str)->pd.DataFrame:
    d=_safe_get(f"https://eodhd.com/api/eod/{sym_eod}", {"from":start,"to":end,"api_token":token,"fmt":"json","period":"d"}) or []
    df=pd.DataFrame(d)
    if df.empty: return df
    df["date"]=pd.to_datetime(df["date"], errors="coerce")
    return df.rename(columns={"open":"Open","high":"High","low":"Low","close":"Close","volume":"Volume"})\
             .sort_values("date").reset_index(drop=True)

def _eod_us(sym:str)->str: sym=sym.strip().upper(); return sym if "." in sym else f"{sym}.US"

# ───────────────────── Indicators (light)
ema = lambda s,n: s.ewm(span=n, adjust=False).mean()
def rsi(s:pd.Series, n:int=14)->pd.Series:
    d=s.diff(); up=np.where(d>0,d,0.0); dn=np.where(d<0,-d,0.0)
    rs = pd.Series(up).rolling(n).mean() / pd.Series(dn).rolling(n).mean().replace(0,np.nan)
    return pd.Series(100 - (100/(1+rs)), index=s.index)
def atr(df:pd.DataFrame, n:int=14)->pd.Series:
    tr=pd.concat([(df["High"]-df["Low"]).abs(),
                  (df["High"]-df["Close"].shift()).abs(),
                  (df["Low"]-df["Close"].shift()).abs()], axis=1).max(axis=1); 
    return tr.rolling(n).mean()
def compute_indicators(df:pd.DataFrame)->pd.DataFrame:
    o=df.copy()
    o["EMA20"],o["EMA50"],o["EMA200"]=ema(o["Close"],20),ema(o["Close"],50),ema(o["Close"],200)
    o["RSI14"],o["ATR14"]=rsi(o["Close"],14),atr(o,14)
    o["AvgVol30"]=o["Volume"].rolling(30).mean()
    o["High20"],o["Low20"]=o["High"].rolling(20).max(),o["Low"].rolling(20).min()
    return o

# ───────────────────── Vector-style scores
def score_rt(df:pd.DataFrame)->float:
    if len(df)<60: return 0.0
    c=df["Close"]; r4=(c.iloc[-1]/c.iloc[-20]-1.0) if len(c)>=20 else 0.0
    r12=(c.iloc[-1]/c.iloc[-60]-1.0) if len(c)>=60 else 0.0
    return round(float(max(0.0, 1.0+0.6*r4+0.4*r12)),3)

def score_rs(df:pd.DataFrame)->float:
    if len(df)<60: return 0.0
    ret=df["Close"].pct_change().dropna()
    vol = (ret.rolling(20).std().iloc[-1] if len(ret)>=20 else ret.std()) or 1e-9
    return round(float(min(max(1.0/(vol*15),0.1),2.0)),3)

def score_rv(price:float, eps:Optional[float], grt:Optional[float])->float:
    if not eps or eps<=0 or grt is None or np.isnan(grt): return 1.0
    pe = price/eps if eps else np.nan
    if not pe or pe<=0: return 1.0
    return round(float(min(max(1.5/(pe/max(grt,0.01)),0.1),2.0)),3)

score_vst = lambda rt,rv,rs: round(float(0.4*rt+0.3*rv+0.3*rs),3)

# CI (Option 2): 13-week trend-recovery stability (higher is steadier)
def score_ci(df:pd.DataFrame)->float:
    if len(df)<65: return 0.9
    w=df.set_index("date")[["Close"]].resample("W-FRI").last().dropna()
    if len(w)<13: return 0.9
    up_weeks=(w["Close"].diff()>0).tail(13).sum()
    peak=np.maximum.accumulate(w["Close"].tail(13))
    dd=((peak - w["Close"].tail(13))/peak).max()  # worst drawdown over 13w
    up_ratio=float(up_weeks)/13.0
    ci = 0.6*up_ratio + 0.4*(1.0 - float(dd))
    return round(float(min(max(ci*1.5,0.1),1.5)),3)

compute_stop = lambda row: round(float(row["EMA50"] - 2.0*row["ATR14"]),4)

# ───────────────────── A/B setup gates (minimal but safe)
def gate_long_minimal(r:pd.Series)->bool: return bool(((r["EMA20"]>=r["EMA50"]) or (r["Close"]>=r["EMA20"])) and r["RSI14"]>=40)
def gate_short_minimal(r:pd.Series)->bool: return bool(((r["EMA20"]<=r["EMA50"]) or (r["Close"]<=r["EMA20"])) and r["RSI14"]<=60)

def decide_buy_today(row:pd.Series, is_long:bool, rt:float, vst:float)->Tuple[str,float,float]:
    if is_long:
        ok_now=(row["EMA20"]>=row["EMA50"]) and (row["RSI14"]>=50) and (row["Close"]>=0.97*(row["High20"] or row["Close"]))
        almost=(row["EMA20"]>=row["EMA50"]) and (row["RSI14"]>=45)
    else:
        ok_now=(row["EMA20"]<=row["EMA50"]) and (row["RSI14"]<=50) and (row["Close"]<=1.03*(row["Low20"] or row["Close"]))
        almost=(row["EMA20"]<=row["EMA50"]) and (row["RSI14"]<=55)
    entry=float(row["Close"]); stop=compute_stop(row)
    if ok_now and rt>=1.0 and vst>=0.9: return ("Buy Today", entry, stop)
    if almost and rt>=0.9 and vst>=0.85: return ("Buy in 2–3 days", entry, stop)
    return ("Wait", entry, stop)

# ───────────────────── Smart Money (resilient wrapper)
def _sm_eval(symbol:str, price=None, ctx=None):
    if not HAS_SM: return True,["smart_money_not_loaded_but_allowed"]
    try:
        ok,details=sm_passes(symbol=symbol, price=price, context=ctx, return_details=True)
        return bool(ok), (details.get("fail_reasons",[]) if not ok else [])
    except Exception: return True,["smart_money_error_bypassed"]

def _render_sm_summary(total_checked:int, reasons_counter:Counter, fail_examples_df:pd.DataFrame):
    st.markdown(f"**Smart Money filter summary:** checked `{total_checked}` symbols")
    if reasons_counter:
        st.markdown("**Top filter reasons**")
        for r,n in reasons_counter.most_common(12): st.write(f"- {r} → {n}")
    if isinstance(fail_examples_df,pd.DataFrame) and not fail_examples_df.empty:
        st.markdown("**Examples (failed):**"); st.dataframe(fail_examples_df.head(25), use_container_width=True, height=360)

# ───────────────────── UI — Chart (left) + Scanner controls/table (right)
st.markdown("### 🔎 A/B Smart Money Scanner")
L,R = st.columns([3,2], gap="large")
if "preview_symbol" not in st.session_state: st.session_state["preview_symbol"]="AAPL"

with L:
    mode = st.radio("Mode", ["A — Long (Smart Money)","B — Short (Smart Money)"], horizontal=True)
    sym_in = st.text_input("Symbol (TradingView format)", value=st.session_state["preview_symbol"])
    st.session_state["preview_symbol"]=sym_in
    st.link_button("🔗 Open in TradingView", f"https://www.tradingview.com/chart/?symbol={sym_in}", use_container_width=True)
    if HAS_TV: advanced_chart(st.session_state["preview_symbol"], height=680)
    else: st.info("`advanced_chart()` not found. Chart embed skipped.")

with R:
    st.subheader("Universe Scan (USA)")
    lookback = st.number_input("Lookback bars", 150, 3000, 420, 10)
    apply_sm = st.checkbox("Apply Smart Money pre-filter", value=True)
    max_checks = st.number_input("HARD CAP: symbols to process", 50, 2000, 200, 50)
    max_results = st.number_input("Max matches to return", 5, 2000, 200, 5)
    start_offset = st.number_input("Start offset in symbol list", 0, 50000, 0, 100)

    if "us_symbol_pool" not in st.session_state: st.session_state["us_symbol_pool"]=[]
    if st.button("📥 Load US symbol list", use_container_width=True):
        if not TOKEN: st.error("EODHD token missing — set EODHD_API_TOKEN.")
        else:
            df_all=eod_exchange_symbols_us(TOKEN)
            if df_all.empty: st.warning("Could not retrieve US symbol list.")
            else:
                ex_ok={"NYSE","NASDAQ","AMEX","NYSE MKT","BATS","ARCX"}
                if "Exchange" in df_all.columns:
                    df_all=df_all[df_all["Exchange"].astype(str).str.upper().isin(ex_ok)]
                if "Type" in df_all.columns:
                    df_all=df_all[~df_all["Type"].astype(str).str.contains("ETF|ETN|FUND|PREF|ADR|RIGHT|WARRANT", case=True, na=False)]
                st.session_state["us_symbol_pool"]=df_all["Code"].astype(str).str.upper().dropna().drop_duplicates().tolist() if "Code" in df_all.columns else []
                st.success(f"Loaded {len(st.session_state['us_symbol_pool'])} US symbols.")

    pool=st.session_state.get("us_symbol_pool", [])
    if "us_scan_df" not in st.session_state: st.session_state["us_scan_df"]=pd.DataFrame()
    if "us_sm_counts" not in st.session_state: st.session_state["us_sm_counts"]=Counter()
    if "us_sm_fail_examples" not in st.session_state: st.session_state["us_sm_fail_examples"]=pd.DataFrame()
    MIN_AVG30_VOLUME=100_000

    @st.cache_data(ttl=300, show_spinner=False)
    def _scan(is_long:bool, lookback:int, token:str, pool:List[str], start_offset:int, max_checks:int, max_results:int, apply_sm_flag:bool):
        start=(date.today()-timedelta(days=int(max(lookback*1.2,200)))).strftime("%Y-%m-%d"); end=date.today().strftime("%Y-%m-%d")
        out=[]; processed=0; reasons_counter=Counter(); fail_rows=[]
        for sym in pool[start_offset:]:
            if processed>=int(max_checks): break
            df=fetch_ohlcv(_eod_us(sym), start, end, token); processed+=1
            if df.empty or len(df)<60: reasons_counter["data_insufficient"]+=1; fail_rows.append({"Symbol":sym,"Reason":"data_insufficient"}); continue
            df=df.tail(max(lookback,60)); df=compute_indicators(df); row=df.iloc[-1]
            avg30=float(row.get("AvgVol30") or 0.0)
            if avg30<MIN_AVG30_VOLUME: reasons_counter["liquidity_avg30_floor"]+=1; fail_rows.append({"Symbol":sym,"Reason":"liquidity_avg30_floor"}); continue
            if not (gate_long_minimal(row) if is_long else gate_short_minimal(row)):
                reasons_counter["long_setup_min_fail" if is_long else "short_setup_min_fail"]+=1; 
                fail_rows.append({"Symbol":sym,"Reason":"setup_min_fail"}); continue
            sm_ok, sm_reasons = (True, [])
            if apply_sm_flag and HAS_SM:
                sm_ok, sm_reasons=_sm_eval(sym, price=float(row["Close"]), ctx={"benchmark":"SPY"})
            if not sm_ok:
                for rr in (sm_reasons or ["smart_money_fail"]): reasons_counter[rr]+=1
                fail_rows.append({"Symbol":sym,"Reason":", ".join(sm_reasons)[:240]}); continue
            rt=score_rt(df); rs=score_rs(df); eps=grt=sector=sales=None
            if HAS_YF:
                try:
                    info=yf.Ticker(sym).info; eps=info.get("trailingEps"); grt=info.get("earningsGrowth"); sector=info.get("sector"); sales=info.get("revenueGrowth")
                except Exception: pass
            rv=score_rv(float(row["Close"]), eps, (grt if grt is not None else (sales if sales is not None else 0.1)))
            vst=score_vst(rt,rv,rs); ci=score_ci(df)
            label,entry,stop=decide_buy_today(row,is_long,rt,vst)
            if label=="Wait": reasons_counter["buy_logic_wait"]+=1; fail_rows.append({"Symbol":sym,"Reason":"buy_logic_wait"}); continue
            pct_prc=(row["Close"]/df["Close"].iloc[-2]-1.0)*100.0 if len(df)>=2 else 0.0
            chg=row["Close"]-df["Close"].iloc[-2] if len(df)>=2 else 0.0
            out.append({
                "Symbol": sym.upper(),
                "TV": f"https://www.tradingview.com/chart/?symbol={sym.upper()}",
                "Side": "LONG" if is_long else "SHORT",
                "Sector": sector or "",
                "% PRC": round(float(pct_prc),2),
                "RS": round(float(rs),3), "RT": round(float(rt),3),
                "VST": round(float(vst),3), "CI": round(float(ci),3),
                "AvgVol30": int(avg30), "Buy Today": label,
                "$ Change (D)": round(float(chg),4), "Stop": round(float(stop),4)
            })
            if len(out)>=int(max_results): break
        df_out=pd.DataFrame(out); fail_df=pd.DataFrame(fail_rows)
        if not df_out.empty:
            by=[c for c in ["VST","RS","RT","Symbol"] if c in df_out.columns]; asc=[False,False,False,True][:len(by)]
            df_out=df_out.sort_values(by=by, ascending=asc).reset_index(drop=True)
        return df_out, reasons_counter, fail_df, processed

    if st.button("🚀 Scan (A/B)", use_container_width=True):
        if not TOKEN: st.error("EODHD token missing — set EODHD_API_TOKEN.")
        elif not pool: st.warning("Load the US symbol list first.")
        else:
            with st.spinner("Scanning…"):
                is_long = mode.startswith("A")
                res,counts,fail_df,checked=_scan(is_long,lookback,TOKEN,pool,int(start_offset),int(max_checks),int(max_results),apply_sm)
            st.session_state["us_scan_df"]=res; st.session_state["us_sm_counts"]=counts
            st.session_state["us_sm_fail_examples"]=fail_df; st.success(f"Done. Checked: {checked} • Matches: {len(res)}")

    res=st.session_state.get("us_scan_df", pd.DataFrame())
    _render_sm_summary(total_checked=(sum(st.session_state.get("us_sm_counts",Counter()).values())+len(res)),
                       reasons_counter=st.session_state.get("us_sm_counts",Counter()),
                       fail_examples_df=st.session_state.get("us_sm_fail_examples",pd.DataFrame()))

    if not res.empty:
        st.markdown("### Smart Money — Passed")
        # Link column → TradingView, click sets preview symbol (no dropdowns)
        try:
            st.dataframe(
                res[[c for c in ["Symbol","Side","Sector","% PRC","RS","RT","VST","CI","AvgVol30","Buy Today","TV"]]],
                use_container_width=True, hide_index=True,
                column_config={
                    "TV": st.column_config.LinkColumn("TradingView", help="Open chart", validate="^https?://")
                },
            )
        except Exception:
            # Fallback (no LinkColumn support)
            df_show=res.copy(); df_show["TradingView"]=df_show["TV"]; df_show=df_show.drop(columns=["TV"])
            st.dataframe(df_show, use_container_width=True, hide_index=True)

        # Quick picker keeps chart pinned on the left—no scroll back & forth
        pick = st.selectbox("Quick Preview (updates left chart)", res["Symbol"].tolist(), key="quick_pick")
        if st.button("🔍 Preview Selected", use_container_width=True, key="btn_prev"):
            st.session_state["preview_symbol"]=pick; st.rerun()
        c1,c2=st.columns(2)
        with c1:
            st.download_button("⬇️ CSV", res.to_csv(index=False).encode("utf-8"), file_name="usa_scan_AB.csv", mime="text/csv")
        with c2:
            if st.button("➕ Add ALL to Today's Queue", use_container_width=True):
                for s in res["Symbol"].tolist(): add_to_queue(s,"USA"); st.success("Queued all results.")
    else:
        st.info("No final matches. See **Top filter reasons** above to adjust thresholds.")

# ───────────────────── Economic Calendar & Earnings
st.markdown("---"); st.header("🗓️ Economic Calendar & 💼 Earnings (Split View)")
st.markdown("<style>.inline-black-divider{width:100%;height:600px;min-height:600px;background:#000;border-radius:8px;}</style>", unsafe_allow_html=True)
cL,cM,cR = st.columns([0.475,0.05,0.475], gap="small")

with cL:
    st.subheader("📆 Economic Calendar (TradingView • USA/CAD/MXN)")
    components.html("""
    <div class="tradingview-widget-container"><div class="tradingview-widget-container__widget"></div>
    <script type="text/javascript" src="https://s3.tradingview.com/external-embedding/embed-widget-events.js" async>
    {"colorTheme":"dark","isTransparent":true,"width":"100%","height":"600","locale":"en","importanceFilter":"-1,0,1","currencyFilter":"USD,CAD,MXN"}
    </script></div>""", height=620, scrolling=False)

with cM: st.markdown('<div class="inline-black-divider"></div>', unsafe_allow_html=True)

with cR:
    st.subheader("💼 Earnings (EODHD • Always On)")
    today=date.today(); d1,d2=st.columns(2)
    with d1: earn_start=st.date_input("From", value=today-timedelta(days=1), key="earn_from")
    with d2: earn_end  =st.date_input("To",   value=today+timedelta(days=14), key="earn_to")
    if TOKEN:
        from_date, to_date = earn_start.strftime("%Y-%m-%d"), earn_end.strftime("%Y-%m-%d")
        with st.spinner("Loading earnings…"):
            raw=_safe_get("https://eodhd.com/api/calendar/earnings",
                          {"from":from_date,"to":to_date,"api_token":TOKEN,"fmt":"json","limit":"5000"}) or []
            df_e=pd.DataFrame(raw)
        if not df_e.empty:
            df_e=df_e.rename(columns={"code":"symbol","epsEstimate":"epsEstimated"}) if "code" in df_e.columns else df_e
            if "reportDate" in df_e.columns: df_e["reportDate"]=pd.to_datetime(df_e["reportDate"], errors="coerce")
            if "exchange" in df_e.columns:
                df_e=df_e[df_e["exchange"].astype(str).str.contains("US|NYSE|NASDAQ|AMEX|BATS|ARCX|OTC", case=False, na=True)]
            keep=[c for c in ["reportDate","time","symbol","exchange","name","epsEstimated","epsActual","revenueEstimated","revenueActual","currency"] if c in df_e.columns]
            if keep: df_e=df_e[keep]
            st.dataframe(df_e.sort_values(["reportDate","symbol"] if "symbol" in df_e.columns else ["reportDate"]),
                         use_container_width=True, hide_index=True)
            st.download_button("⬇️ Download Earnings (CSV)", df_e.to_csv(index=False).encode("utf-8"),
                               file_name=f"earnings_{from_date}_{to_date}.csv", mime="text/csv")
        else:
            st.info("No earnings returned for this window (or API rate-limited).")
    else: st.caption("Set EODHD_API_TOKEN to show earnings.")

# ───────────────────── Morning Report & News (fix for Timestamp join)
st.markdown("---"); st.header("📰 USA Morning Report & News")
c1,c2=st.columns(2)
with c1:
    st.subheader("🇺🇸 Morning Report (Latest)")
    p="reports/usa_morning.md"
    if os.path.exists(p): st.markdown(open(p,"r",encoding="utf-8").read())
    else: st.caption("No `reports/usa_morning.md` yet. Using EODHD News on the right.")
with c2:
    st.subheader("Market News (EODHD)")
    if TOKEN:
        to_dt=date.today(); from_dt=to_dt - timedelta(days=3)
        with st.spinner("Fetching EODHD News…"):
            raw=_safe_get("https://eodhd.com/api/news",
                          {"from":from_dt.strftime("%Y-%m-%d"),"to":to_dt.strftime("%Y-%m-%d"),
                           "api_token":TOKEN,"fmt":"json","limit":"100"}) or []
            df_news=pd.DataFrame(raw)
        if not df_news.empty:
            ts_col=next((c for c in ["date","publishedDate","time"] if c in df_news.columns), None)
            if ts_col: df_news["ts"]=pd.to_datetime(df_news[ts_col], errors="coerce")
            for r in df_news.sort_values("ts", ascending=False).head(12).itertuples():
                with st.container(border=True):
                    st.markdown(f"**{getattr(r,'title','(no title)')}**")
                    parts=[]
                    src=getattr(r,'source',None); ts=getattr(r,'ts',None)
                    if src: parts.append(str(src))
                    if ts is not None: parts.append(str(ts))
                    if parts: st.caption(" • ".join(parts))
                    link=getattr(r,'link',None)
                    if link: st.link_button("Open", str(link), use_container_width=True)
        else: st.info("No news returned by EODHD for the selected window.")
    else: st.caption("Set EODHD_API_TOKEN to enable EODHD news.")

st.markdown("---"); render_queue()
