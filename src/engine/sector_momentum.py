
import numpy as np
import pandas as pd
import os

def _to_returns(df: pd.DataFrame, price_col="close"):
    s = pd.to_numeric(df[price_col], errors="coerce").ffill()
    return s.pct_change().dropna()

def _norm_equity(df: pd.DataFrame, price_col="close"):
    s = pd.to_numeric(df[price_col], errors="coerce").ffill().dropna()
    if s.empty: return s
    return s / s.iloc[0]

def _rs(asset: pd.Series, bench: pd.Series):
    df = pd.concat([asset, bench], axis=1).dropna()
    if df.shape[0] < 2: return np.nan
    a = df.iloc[:,0]
    b = df.iloc[:,1]
    ratio = (1 + a).cumprod() / (1 + b).cumprod()
    return float(ratio.iloc[-1] / ratio.median() - 1.0)

def _horizon_ret(series: pd.Series, periods: int):
    if series.shape[0] <= periods: return np.nan
    return float(series.iloc[-1] / series.iloc[-periods] - 1.0)

def compute_momentum(asset_df: pd.DataFrame, bench_df: pd.DataFrame, price_col="close"):
    r_a = _to_returns(asset_df, price_col)
    r_b = _to_returns(bench_df, price_col) if bench_df is not None else None
    eq_a = (1 + r_a).cumprod()

    horizons = {"1w":5, "1m":21, "3m":63, "6m":126}
    hvals = {k: _horizon_ret(eq_a, p) for k,p in horizons.items()}

    rs_val = _rs(r_a, r_b) if r_b is not None else np.nan

    w = {"1w":0.2,"1m":0.3,"3m":0.3,"6m":0.2}
    base = sum([(hvals[k] if np.isfinite(hvals[k]) else 0)*w[k] for k in w])
    boost = (rs_val if np.isfinite(rs_val) else 0) * 0.25
    comp = base + boost

    return {
        "h_1w": hvals["1w"],
        "h_1m": hvals["1m"],
        "h_3m": hvals["3m"],
        "h_6m": hvals["6m"],
        "rs": rs_val,
        "score": comp
    }

def tiles_from_files(files: list, bench_df: pd.DataFrame = None, price_col="close"):
    rows = []
    for f in files:
        try:
            df = pd.read_csv(f)
            if "date" in df.columns:
                df["date"] = pd.to_datetime(df["date"], errors="coerce")
                df = df.sort_values("date").set_index("date")
            else:
                df.iloc[:,0] = pd.to_datetime(df.iloc[:,0], errors="coerce")
                df = df.rename(columns={df.columns[0]:"date"}).sort_values("date").set_index("date")
            name = getattr(f, "name", "SECTOR")
            sym = os.path.splitext(os.path.basename(name))[0].upper()
            metrics = compute_momentum(df, bench_df, price_col=price_col)
            row = {"sector": sym}
            row.update(metrics)
            rows.append(row)
        except Exception:
            rows.append({"sector": getattr(f, "name", "SECTOR"), "h_1w": np.nan, "h_1m": np.nan, "h_3m": np.nan, "h_6m": np.nan, "rs": np.nan, "score": np.nan})
    return pd.DataFrame(rows)

def grade(score: float):
    if not np.isfinite(score): return "NA"
    if score >= 0.06: return "🟢 Strong"
    if score >= 0.0:  return "🟡 Neutral"
    return "🔴 Weak"
