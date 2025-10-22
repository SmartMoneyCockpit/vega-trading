
import pandas as pd, numpy as np, streamlit as st
from datetime import datetime, timedelta
from src.eodhd_client import get_eod_history, get_price_quote

ARROW_UP = "▲"
ARROW_DOWN = "▼"
ARROW_FLAT = "▬"

def _safe_hist(symbol: str, exch: str, start="2023-01-01"):
    data = get_eod_history(symbol, exch, period="d", from_=start)
    if isinstance(data, dict) and "error" in data:
        return None, data["error"]
    df = pd.DataFrame(data)
    if df.empty or "close" not in df.columns or "date" not in df.columns:
        return None, "no data"
    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values("date").reset_index(drop=True)
    return df, None

def _pct_change(df, days):
    if len(df) < days+1: return np.nan
    return (df["close"].iloc[-1] / df["close"].iloc[-1-days] - 1.0) * 100.0

def _normalize(value, lo, hi):
    if np.isnan(value): return np.nan
    return max(0.0, min(2.0, 1.0 + (value - lo) / (hi - lo + 1e-9)))  # maps into ~0..2 band

def compute_row_metrics(ticker: str, exch: str):
    # Real-time quote (for Price/Bid/Ask/% and arrows)
    q = get_price_quote(ticker, exch)
    if isinstance(q, dict) and "error" in q:
        return {"ticker": ticker, "error": q["error"]}
    price = q.get("close") or q.get("previousClose") or q.get("lastTradePrice")
    bid = q.get("bid")
    ask = q.get("ask")
    chg_p = q.get("change_p")
    # Arrow
    if chg_p is None:
        arrow = ARROW_FLAT
    else:
        arrow = ARROW_UP if chg_p > 0 else (ARROW_DOWN if chg_p < 0 else ARROW_FLAT)

    # History for VV-style proxies
    df, err = _safe_hist(ticker, exch, start=(datetime.today()-timedelta(days=400)).strftime("%Y-%m-%d"))
    if df is None:
        return {"ticker": ticker, "price": price, "bid": bid, "ask": ask, "%": chg_p, "arrow": arrow, "error": err}

    # Proxies (not official VV): scaled to ~0..2 where 1.0 ~ neutral
    # RS: 26-week return (band -30%..+30%)
    rs26w_pct = _pct_change(df, 130)
    RS = _normalize(rs26w_pct/100.0, -0.30, 0.30)

    # RT: 5-day momentum (band -5%..+5%)
    mom5d_pct = _pct_change(df, 5)
    RT = _normalize(mom5d_pct/100.0, -0.05, 0.05)

    # RV: value proxy via lower volatility & positive slope
    vol = float(df["close"].pct_change().std() or 0.0)
    slope = float((df["close"].iloc[-1] - df["close"].iloc[max(0, len(df)-21)]) / (df["close"].iloc[max(0, len(df)-21)] + 1e-9))
    # lower vol is "better": invert and scale; slope positive adds
    RV = _normalize((0.05 - vol) + slope, -0.10, 0.10)

    # CI: consistency proxy via SMA trend agreement (20 vs 50) and drawdown
    sma20 = df["close"].rolling(20).mean().iloc[-1]
    sma50 = df["close"].rolling(50).mean().iloc[-1]
    trend_up = 1.0 if (sma20 >= sma50) else -1.0
    peak = df["close"].cummax()
    dd = (df["close"] / peak - 1.0).min()  # most negative drawdown
    CI = _normalize(trend_up*0.05 - abs(dd), -0.30, 0.10)

    # VST: composite
    VST = np.nanmean([RT, RV, RS, CI])

    return {
        "ticker": ticker,
        "price": price,
        "bid": bid,
        "ask": ask,
        "%": None if chg_p is None else round(float(chg_p), 2),
        "arrow": arrow,
        "RT": None if np.isnan(RT) else round(float(RT), 2),
        "RV": None if np.isnan(RV) else round(float(RV), 2),
        "RS": None if np.isnan(RS) else round(float(RS), 2),
        "CI": None if np.isnan(CI) else round(float(CI), 2),
        "VST": None if np.isnan(VST) else round(float(VST), 2),
    }

def render_scanner(default_list, exch, benchmark, title="VectorVest-Style Scanner"):
    st.subheader(f"📊 {title}")
    tickers = st.text_area("Tickers to scan", "\\n".join(default_list), key=f"scan_{exch}").splitlines()
    go = st.button("Run Scanner", key=f"go_{exch}")
    if not go:
        st.info("Enter tickers and press **Run Scanner**.")
        return

    rows = []
    for t in tickers:
        t = t.strip()
        if not t: continue
        rows.append(compute_row_metrics(t, exch))

    df = pd.DataFrame(rows)
    if "error" in df.columns:
        # surface errors inline
        st.dataframe(df, use_container_width=True)
    else:
        # Arrange and display in the requested format
        cols = ["ticker","price","bid","ask","%","RT","RV","RS","CI","VST","arrow"]
        present = [c for c in cols if c in df.columns]
        st.dataframe(df[present], use_container_width=True)
        st.caption("Notes: RT/RV/RS/CI/VST are **proxies** derived from EOD prices (not official VectorVest). Arrows reflect intraday % change.")
