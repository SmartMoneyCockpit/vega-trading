# tools/scanners/pattern_scanners.py
from __future__ import annotations
import os, glob
import pandas as pd
import numpy as np

def _read_csv_any(path: str) -> pd.DataFrame:
    df = pd.read_csv(path)
    cols = {c.lower(): c for c in df.columns}
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
    x = np.arange(len(y)); x = x - x.mean(); y = y - y.mean()
    d = (x**2).sum()
    return float((x*y).sum()/d) if d else 0.0

def _range_narrowing(high: np.ndarray, low: np.ndarray) -> float:
    return _rolling_slope(high - low)

def _strength_proxy(close: np.ndarray) -> float:
    return float((close[-1] - close[-20]) / (abs(close[-20]) + 1e-9))

def _scan(df: pd.DataFrame, kind: str):
    w = min(40, len(df))
    if w < 20: return None
    h = df["high"].values[-w:]; l = df["low"].values[-w:]
    sH = _rolling_slope(h); sL = _rolling_slope(l); nar = _range_narrowing(h,l)
    if kind == "rising_wedge":
        ok = sH > 0 and sL > 0 and nar < 0
        score = (sH + sL)/2 - abs(nar)
    elif kind == "falling_wedge":
        ok = sH < 0 and sL < 0 and nar < 0
        score = (-sH - sL)/2 - abs(nar)
    else:  # vega_smart_today proxy
        if len(df) < 25: return None
        close = df["close"].values
        roc20 = _strength_proxy(close)
        pullback = float(close[-1]/(df["high"].values[-5:-1].max()+1e-9)-1.0)
        atr = (df["high"][-14:] - df["low"][-14:]).mean()
        atr_prev = (df["high"][-28:-14] - df["low"][-28:-14]).mean() if len(df)>=28 else atr
        compression = float((atr_prev - atr)/(atr_prev+1e-9))
        score = max(0.0, (roc20>0)*roc20) + max(0.0, -pullback) + max(0.0, compression)
        ok = score > 0.02
    return (ok, float(score))

def run_scan(data_dir: str, kind: str = "rising_wedge", limit: int = 50) -> pd.DataFrame:
    files = sorted(glob.glob(os.path.join(data_dir, "*.csv")))
    rec = []
    for p in files:
        sym = os.path.splitext(os.path.basename(p))[0]
        try:
            df = _read_csv_any(p); res = _scan(df, kind)
            if res and res[0]:
                last = df.iloc[-1]
                rec.append({"symbol": sym, "close": float(last["close"]), "score": round(res[1],4)})
        except Exception:
            pass
    out = pd.DataFrame(rec).sort_values("score", ascending=False).head(limit)
    return out.reset_index(drop=True)
