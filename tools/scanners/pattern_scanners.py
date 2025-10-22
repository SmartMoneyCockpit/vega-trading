# tools/scanners/pattern_scanners.py
"""
Local scanners for Canada (and reusable elsewhere).
Drop CSVs in data/eod/ca/ with columns: date, open, high, low, close, volume
(or OHLCV typical headers). We infer if needed.
Scans implemented:
- Rising Wedge
- Falling Wedge
- Vega Smart Money (Today) placeholder: filters for RS/RT-like proxies.

These are intentionally lightweight; replace heuristics later with your
production detectors.
"""
from __future__ import annotations
import os, glob, math
from dataclasses import dataclass
from typing import List, Dict, Tuple
import pandas as pd
import numpy as np

DATA_DIR = os.getenv("VEGA_CA_EOD_DIR", "data/eod/ca")

def _read_csv_any(path: str) -> pd.DataFrame:
    df = pd.read_csv(path)
    cols = {c.lower(): c for c in df.columns}
    # normalize
    m = {
        "date": cols.get("date", list(df.columns)[0]),
        "open": cols.get("open", list(df.columns)[1]),
        "high": cols.get("high", list(df.columns)[2]),
        "low":  cols.get("low",  list(df.columns)[3]),
        "close":cols.get("close",list(df.columns)[4]),
        "volume": cols.get("volume", cols.get("vol", None))
    }
    out = pd.DataFrame({
        "date": pd.to_datetime(df[m["date"]]),
        "open": pd.to_numeric(df[m["open"]], errors="coerce"),
        "high": pd.to_numeric(df[m["high"]], errors="coerce"),
        "low":  pd.to_numeric(df[m["low"]],  errors="coerce"),
        "close":pd.to_numeric(df[m["close"]],errors="coerce"),
        "volume": pd.to_numeric(df[m["volume"]], errors="coerce") if m["volume"] else np.nan,
    }).dropna(subset=["close"])
    out.sort_values("date", inplace=True)
    out.reset_index(drop=True, inplace=True)
    return out

def _rolling_slope(y: np.ndarray) -> float:
    x = np.arange(len(y))
    x = x - x.mean()
    y = y - y.mean()
    denom = (x**2).sum()
    if denom == 0: return 0.0
    return float((x*y).sum()/denom)

def _range_narrowing(high: np.ndarray, low: np.ndarray) -> float:
    rng = high - low
    return _rolling_slope(rng)

def _strength_proxy(close: np.ndarray) -> float:
    # simple ROC-based strength proxy
    return float((close[-1] - close[-20]) / (1e-9 + abs(close[-20])))

def scan_rising_wedge(df: pd.DataFrame) -> Dict[str, float]:
    # last 40 bars window
    w = min(40, len(df))
    if w < 20: return {}
    s_high = _rolling_slope(df["high"].values[-w:])
    s_low  = _rolling_slope(df["low"].values[-w:])
    nar = _range_narrowing(df["high"].values[-w:], df["low"].values[-w:])
    if s_high > 0 and s_low > 0 and nar < 0:
        return {"score": float((s_high + s_low) / 2.0 - abs(nar))}
    return {}

def scan_falling_wedge(df: pd.DataFrame) -> Dict[str, float]:
    w = min(40, len(df))
    if w < 20: return {}
    s_high = _rolling_slope(df["high"].values[-w:])
    s_low  = _rolling_slope(df["low"].values[-w:])
    nar = _range_narrowing(df["high"].values[-w:], df["low"].values[-w:])
    if s_high < 0 and s_low < 0 and nar < 0:
        return {"score": float((-s_high - s_low) / 2.0 - abs(nar))}
    return {}

def scan_vega_smart_today(df: pd.DataFrame) -> Dict[str, float]:
    # proxy: positive 20d ROC, pullback within 3d, ATR compression
    w = min(40, len(df))
    if w < 25: return {}
    roc20 = _strength_proxy(df["close"].values)
    pullback = float(df["close"].values[-1] / (df["high"].values[-5:-1].max()+1e-9) - 1.0)
    atr = (df["high"][-14:] - df["low"][-14:]).mean()
    atr_prev = (df["high"][-28:-14] - df["low"][-28:-14]).mean() if len(df) >= 28 else atr
    compression = float((atr_prev - atr) / (atr_prev + 1e-9))
    score = 0.0
    if roc20 > 0: score += roc20
    if pullback < 0: score += min(0.05, -pullback)
    if compression > 0: score += min(0.05, compression)
    if score > 0.02:
        return {"score": float(score), "roc20": float(roc20), "compress": float(compression)}
    return {}

def run_scan(kind: str = "rising_wedge", limit: int = 50) -> pd.DataFrame:
    files = sorted(glob.glob(os.path.join(DATA_DIR, "*.csv")))
    records = []
    for path in files:
        sym = os.path.splitext(os.path.basename(path))[0]
        try:
            df = _read_csv_any(path)
            if kind == "rising_wedge":
                res = scan_rising_wedge(df)
            elif kind == "falling_wedge":
                res = scan_falling_wedge(df)
            else:
                res = scan_vega_smart_today(df)
            if res:
                last = df.iloc[-1]
                records.append({
                    "symbol": sym,
                    "close": float(last["close"]),
                    "score": round(res.get("score", 0.0), 4),
                } | {k:v for k,v in res.items() if k!="score"})
        except Exception:
            continue
    out = pd.DataFrame(records).sort_values("score", ascending=False).head(limit)
    return out.reset_index(drop=True)
