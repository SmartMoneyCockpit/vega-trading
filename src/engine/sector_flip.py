
import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime
import json, os

# ---------- Helpers ----------

def _load_intraday_csv(fp: str, price_col="close", vol_col="volume", time_col="datetime"):
    """
    Load intraday CSV with columns: datetime, close, volume (names configurable).
    Returns a DataFrame indexed by datetime (UTC/local agnostic).
    """
    df = pd.read_csv(fp)
    if time_col in df.columns:
        df[time_col] = pd.to_datetime(df[time_col], errors="coerce")
        df = df.sort_values(time_col).set_index(time_col)
    else:
        df.iloc[:,0] = pd.to_datetime(df.iloc[:,0], errors="coerce")
        df = df.rename(columns={df.columns[0]: time_col}).sort_values(time_col).set_index(time_col)
    # normalize columns
    if price_col not in df.columns:
        # guess last numeric column
        for c in reversed(df.columns):
            if pd.api.types.is_numeric_dtype(df[c]): price_col = c; break
    if vol_col not in df.columns:
        vol_col = None
    cols = {"close": df[price_col]}
    if vol_col: cols["volume"] = df[vol_col]
    out = pd.DataFrame(cols).dropna()
    return out

def _ema(s: pd.Series, span: int):
    return s.ewm(span=span, adjust=False).mean()

# ---------- Rule 1: Relative return sign flip with threshold ----------

def rel_flip_alerts(sector_df: pd.DataFrame, index_df: pd.DataFrame, window_min=15, threshold=0.006):
    """
    Detect flips where sector's relative return vs index changes sign and exceeds threshold
    over the last `window_min` minutes.
    Returns list of events with ts, direction ('up'/'down'), value.
    """
    if sector_df.empty or index_df.empty:
        return []

    # Align to common timeline (minute index)
    df = pd.concat([sector_df["close"], index_df["close"]], axis=1, keys=["sector","index"]).dropna()
    if df.shape[0] < 3: return []
    # Compute rolling window relative performance over window_min
    # rel_ret = (sector_t/sector_t-w) / (index_t/index_t-w) - 1
    w = f"{window_min}T"
    sec_ret = df["sector"] / df["sector"].shift(window_min) - 1.0
    idx_ret = df["index"] / df["index"].shift(window_min) - 1.0
    rel = (1 + sec_ret) / (1 + idx_ret) - 1.0
    rel = rel.dropna()

    events = []
    # Detect sign flip: sign(current) != sign(prev) and |current| >= threshold
    sgn = np.sign(rel)
    for i in range(1, len(rel)):
        if np.sign(rel.iloc[i]) != np.sign(rel.iloc[i-1]) and abs(rel.iloc[i]) >= threshold:
            direction = "up" if rel.iloc[i] > 0 else "down"
            events.append({
                "ts": rel.index[i].strftime("%Y-%m-%d %H:%M"),
                "rule": "rel_flip",
                "window_min": window_min,
                "threshold": threshold,
                "direction": direction,
                "rel_ret": float(rel.iloc[i])
            })
    return events

# ---------- Rule 2: EMA(10) - EMA(30) cross with volume filter ----------

def ema_cross_volume_alerts(sector_df: pd.DataFrame, vol_mult=1.2, fast=10, slow=30):
    """
    Detect when momentum proxy (EMA10-EMA30) crosses zero and volume >= vol_mult * 20-day avg (intraday bars).
    Returns list of events with ts, direction, and vol ratio.
    """
    if sector_df.empty or "volume" not in sector_df.columns:
        return []
    p = sector_df["close"]
    v = sector_df["volume"]
    if len(p) < slow + 2: return []

    ema_f = _ema(p, fast)
    ema_s = _ema(p, slow)
    mom = ema_f - ema_s
    vol_avg = v.rolling(20).mean()
    events = []
    for i in range(1, len(mom)):
        crossed_up = mom.iloc[i-1] <= 0 and mom.iloc[i] > 0
        crossed_dn = mom.iloc[i-1] >= 0 and mom.iloc[i] < 0
        vol_ok = v.iloc[i] >= vol_mult * (vol_avg.iloc[i] if pd.notnull(vol_avg.iloc[i]) else 0)
        if vol_ok and (crossed_up or crossed_dn):
            events.append({
                "ts": mom.index[i].strftime("%Y-%m-%d %H:%M"),
                "rule": "ema_cross_vol",
                "fast": fast, "slow": slow, "vol_mult": vol_mult,
                "direction": "up" if crossed_up else "down",
                "mom": float(mom.iloc[i]),
                "vol_ratio": float(v.iloc[i] / (vol_avg.iloc[i] if pd.notnull(vol_avg.iloc[i]) and vol_avg.iloc[i] != 0 else np.nan))
            })
    return events

# ---------- End-to-end for batch of sectors ----------

def evaluate_flips(
    sector_files: dict,
    index_file: str,
    price_col="close",
    vol_col="volume",
    time_col="datetime",
    window_min=15,
    threshold=0.006,
    vol_mult=1.2,
    fast=10, slow=30
):
    """
    sector_files: dict like {'XLK.csv': '/path/to/xlk.csv', ...}
    Returns DataFrame of alerts with columns: ts, sector, rule, direction, rel_ret/mom/vol_ratio.
    """
    idx_df = _load_intraday_csv(index_file, price_col=price_col, vol_col=vol_col, time_col=time_col) if index_file else pd.DataFrame()
    rows = []
    for name, fp in sector_files.items():
        s_df = _load_intraday_csv(fp, price_col=price_col, vol_col=vol_col, time_col=time_col)
        # Rule 1
        r1 = rel_flip_alerts(s_df, idx_df, window_min=window_min, threshold=threshold) if not idx_df.empty else []
        for ev in r1:
            ev["sector"] = Path(name).stem.upper()
            rows.append(ev)
        # Rule 2
        r2 = ema_cross_volume_alerts(s_df, vol_mult=vol_mult, fast=fast, slow=slow)
        for ev in r2:
            ev["sector"] = Path(name).stem.upper()
            rows.append(ev)
    if not rows:
        return pd.DataFrame(columns=["ts","sector","rule","direction","rel_ret","mom","vol_ratio","window_min","threshold","fast","slow","vol_mult"])
    df = pd.DataFrame(rows)
    df = df.sort_values("ts")
    return df

# ---------- Logging ----------

def write_alerts(df: pd.DataFrame, alerts_dir="data/alerts", tag="sector_flip_intraday"):
    Path(alerts_dir).mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = Path(alerts_dir) / f"{tag}_{ts}.csv"
    df.to_csv(path, index=False)
    return str(path)
