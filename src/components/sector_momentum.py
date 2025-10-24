import os, pandas as pd
from pathlib import Path

DATA_ROOT = os.getenv("VEGA_SECTOR_DATA_ROOT", "data/vega/sectors")

SAMPLE_US = [
    ("XLK","Technology", 0.8, 2.4, 5.9, 78),
    ("XLI","Industrials", 0.3, 1.1, 2.0, 61),
    ("XLB","Materials", -0.2, 0.9, 1.6, 55),
    ("XLF","Financials", 0.1, -0.6, 0.7, 48),
    ("XLY","Consumer Discretionary", -0.5, 0.2, 1.9, 57),
    ("XLP","Consumer Staples", 0.2, 0.5, 0.9, 52),
    ("XLV","Health Care", 0.4, 0.8, 1.2, 58),
    ("XLU","Utilities", -0.1, -0.4, 0.5, 44),
    ("XLE","Energy", -0.9, -1.5, -3.2, 33),
    ("XLRE","Real Estate", -0.3, -0.1, 0.6, 46),
    ("XLC","Communication Services", 0.6, 1.9, 4.0, 70),
]

SAMPLE_CA = [
    ("TTF","Tech (TSX proxy)", 0.5, 1.2, 3.4, 64),
    ("ZIN","Industrials", 0.1, -0.2, 0.7, 49),
    ("XMA","Materials", -0.4, 0.3, 0.9, 50),
    ("ZEB","Financials", 0.2, 0.6, 1.1, 55),
    ("XRE","Real Estate", -0.2, -0.4, 0.1, 42),
    ("XIU","Large Cap (proxy)", 0.3, 0.8, 1.5, 59),
]

SAMPLE_MX = [
    ("ME_TEC","Technology (proxy)", 0.6, 1.4, 3.0, 62),
    ("ME_FIN","Financials (proxy)", 0.2, 0.5, 1.2, 54),
    ("ME_BAS","Materials (proxy)", -0.3, 0.2, 0.7, 47),
    ("ME_COM","Communication (proxy)", 0.4, 0.9, 1.8, 58),
]

def _load_csv(path: str) -> pd.DataFrame:
    try:
        if os.path.exists(path):
            return pd.read_csv(path)
    except Exception:
        pass
    return pd.DataFrame()

def load_region(region: str) -> pd.DataFrame:
    region = (region or "USA").upper()
    if region == "USA":
        df = _load_csv(os.path.join(DATA_ROOT, "us_sectors.csv"))
        if df.empty:
            df = pd.DataFrame(SAMPLE_US, columns=["symbol","name","change_1d","change_5d","change_20d","rs_score"])
        return df
    if region == "CANADA":
        df = _load_csv(os.path.join(DATA_ROOT, "ca_sectors.csv"))
        if df.empty:
            df = pd.DataFrame(SAMPLE_CA, columns=["symbol","name","change_1d","change_5d","change_20d","rs_score"])
        return df
    if region == "MEXICO":
        df = _load_csv(os.path.join(DATA_ROOT, "mx_sectors.csv"))
        if df.empty:
            df = pd.DataFrame(SAMPLE_MX, columns=["symbol","name","change_1d","change_5d","change_20d","rs_score"])
        return df
    return load_region("USA")

def score_from_df(df, window: str) -> pd.DataFrame:
    col = {"1D":"change_1d","5D":"change_5d","1M":"change_20d"}.get(window, "change_1d")
    df = df.copy()
    df["momentum"] = df[col].astype(float)
    lo, hi = df["momentum"].min(), df["momentum"].max()
    rng = (hi - lo) if hi != lo else 1.0
    df["mom_norm"] = ((df["momentum"] - lo) / rng * 100.0).round(1)
    return df

def grade_band(x: float) -> str:
    if x >= 66: return "🟢"
    if x >= 45: return "🟡"
    return "🔴"

def trend_emoji(x: float) -> str:
    if x >= 0.6: return "⬆️"
    if x <= -0.6: return "⬇️"
    return "↔️"
