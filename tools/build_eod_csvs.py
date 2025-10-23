#!/usr/bin/env python3
"""
Build (or refresh) EOD CSVs used by compute_from_df() for VectorVest metrics.

Writes one file per symbol to data/eod/us/<SYMBOL>.csv with columns:
Date, Open, High, Low, Close, Volume
"""

import os, argparse, sys
import pandas as pd

# Soft dep so script doesn't crash if yfinance isn't installed yet
try:
    import yfinance as yf
except Exception:
    yf = None

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
OUT_DIR = os.path.join(ROOT, "data", "eod", "us")
os.makedirs(OUT_DIR, exist_ok=True)

DEFAULT_SYMBOLS = ["SPY","QQQ","AAPL","MSFT","NVDA","AMZN","META","TSLA"]

def fetch(symbol: str, years: int = 5) -> pd.DataFrame:
    if yf is None:
        raise RuntimeError("yfinance not installed. Run: pip install yfinance pandas numpy")
    period = f"{years}y"
    df = yf.download(symbol, period=period, interval="1d", auto_adjust=False, progress=False)
    if df is None or df.empty:
        raise RuntimeError(f"No data for {symbol}")
    df = df.reset_index()
    # Normalize columns
    if "Adj Close" in df.columns:
        df = df.rename(columns={
            "Date":"Date",
            "Open":"Open","High":"High","Low":"Low",
            "Close":"Close","Adj Close":"Adj Close","Volume":"Volume"
        })
    else:
        df = df.rename(columns=str.title)
    keep = [c for c in ["Date","Open","High","Low","Close","Volume"] if c in df.columns]
    df = df[keep].copy()
    # Ensure Date isoformat
    df["Date"] = pd.to_datetime(df["Date"]).dt.tz_localize(None)
    return df

def save_csv(symbol: str, df: pd.DataFrame):
    out = os.path.join(OUT_DIR, f"{symbol}.csv")
    df.to_csv(out, index=False)
    return out

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--symbols", type=str, default=",".join(DEFAULT_SYMBOLS),
                    help="Comma-separated list (e.g. SPY,QQQ,AAPL)")
    ap.add_argument("--years", type=int, default=5, help="Years of history to fetch")
    args = ap.parse_args()

    symbols = [s.strip().upper() for s in args.symbols.split(",") if s.strip()]
    print(f"Writing CSVs to: {OUT_DIR}")
    ok, bad = 0, []
    for sym in symbols:
        try:
            df = fetch(sym, years=args.years)
            path = save_csv(sym, df)
            ok += 1
            print(f"✓ {sym} -> {path} ({len(df)} rows)")
        except Exception as e:
            bad.append((sym, str(e)))
            print(f"✗ {sym}: {e}")
    print(f"\nDone. OK: {ok}, Failed: {len(bad)}")
    if bad:
        for sym, err in bad:
            print(f"- {sym}: {err}")

if __name__ == "__main__":
    main()
