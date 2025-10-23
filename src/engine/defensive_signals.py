import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime, timedelta
import json, os

def _load_series_csv(fp: str, date_col='date', value_col='close'):
    if not fp or not Path(fp).exists():
        return pd.Series(dtype=float)
    df = pd.read_csv(fp)
    if date_col in df.columns:
        df[date_col] = pd.to_datetime(df[date_col], errors='coerce')
        df = df.sort_values(date_col).set_index(date_col)
    else:
        df.iloc[:,0] = pd.to_datetime(df.iloc[:,0], errors='coerce')
        df = df.rename(columns={df.columns[0]: date_col}).sort_values(date_col).set_index(date_col)
    val = value_col if value_col in df.columns else df.columns[-1]
    s = pd.to_numeric(df[val], errors='coerce')
    return s.dropna()

def _load_sector_tiles_csv(fp: str):
    if not fp or not Path(fp).exists():
        return pd.DataFrame(columns=['sector','score'])
    df = pd.read_csv(fp)
    cols = [c.lower() for c in df.columns]
    df.columns = cols
    if 'sector' not in cols or 'score' not in cols:
        return pd.DataFrame(columns=['sector','score'])
    return df[['sector','score']]

def _read_recent_flips(alerts_dir='data/alerts', hours=24):
    path = Path(alerts_dir)
    if not path.exists():
        return []
    cutoff = datetime.now() - timedelta(hours=hours)
    flips = []
    for p in path.glob('*_flips_*.json'):
        try:
            ts = p.stem.split('_flips_')[-1]
            ts_dt = datetime.strptime(ts, '%Y%m%d_%H%M%S')
            if ts_dt >= cutoff:
                flips.extend(json.loads(p.read_text(encoding='utf-8')))
        except Exception:
            pass
    return flips

def vix_score(vix: pd.Series):
    if vix.empty:
        return np.nan, None
    latest = float(vix.iloc[-1])
    if latest < 15: s = 10
    elif latest < 20: s = 35
    elif latest < 30: s = 70
    else: s = 95
    return s, latest

def ratio_score(ratio: pd.Series):
    if ratio.empty or ratio.shape[0] < 30:
        return np.nan, None
    roll = ratio.rolling(60)
    mean = roll.mean().iloc[-1]
    std = roll.std(ddof=1).iloc[-1]
    if std == 0 or not np.isfinite(std):
        return np.nan, float(ratio.iloc[-1])
    z = (ratio.iloc[-1] - mean) / std
    score = float(np.clip(50 + 20*z, 0, 100))
    return score, float(ratio.iloc[-1])

def yield_curve_score(spread: pd.Series):
    if spread.empty:
        return np.nan, None
    latest = float(spread.iloc[-1])
    if latest >= 1.0: s = 10
    elif latest >= 0.2: s = 30
    elif latest >= 0.0: s = 45
    elif latest >= -0.5: s = 75
    else: s = 90
    return s, latest

def breadth_score(tiles_df: pd.DataFrame, strong_cutoff=0.00):
    if tiles_df.empty:
        return np.nan, None
    valid = tiles_df.dropna(subset=['score'])
    if valid.empty:
        return np.nan, None
    pct_strong = (valid['score'] >= strong_cutoff).mean()
    risk = float(np.clip(100 * (1 - pct_strong), 0, 100))
    return risk, float(pct_strong*100.0)

def flips_score(flips: list):
    if not flips:
        return 0.0, 0
    count = 0
    for f in flips:
        if f.get('from') == 'Strong' and f.get('to') == 'Weak':
            count += 1
    mapping = [0, 30, 50, 70, 90]
    idx = min(count, 4)
    return float(mapping[idx]), count

DEFAULT_WEIGHTS = {
    'vix': 0.30,
    'ratio': 0.20,
    'yield_curve': 0.15,
    'breadth': 0.25,
    'flips': 0.10,
}

def composite_risk(scores: dict, weights: dict = None) -> float:
    w = weights or DEFAULT_WEIGHTS
    total = 0.0
    wsum = 0.0
    for k, v in scores.items():
        if np.isfinite(v) and k in w:
            total += v * w[k]
            wsum += w[k]
    if wsum == 0:
        return np.nan
    return float(total / wsum)

def status_from_index(idx: float) -> str:
    if not np.isfinite(idx):
        return 'NA'
    if idx >= 70: return '🔴 Defensive'
    if idx >= 45: return '🟡 Caution'
    return '🟢 Normal'

def save_snapshot(record: dict, path='data/defensive/history.csv'):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    df = pd.DataFrame([record])
    if Path(path).exists():
        df.to_csv(path, mode='a', header=False, index=False)
    else:
        df.to_csv(path, index=False)
    return path

def compute_overlay(
    vix_path='data/vix.csv',
    tlt_path='data/tlt.csv',
    spy_path='data/spy.csv',
    spread_path='data/yield_curve.csv',
    tiles_path='data/exports/USA_sector_tiles_latest.csv',
    alerts_dir='data/alerts',
    weights: dict = None
):
    vix = _load_series_csv(vix_path)
    tlt = _load_series_csv(tlt_path)
    spy = _load_series_csv(spy_path)
    ratio = (tlt / spy).dropna() if not tlt.empty and not spy.empty else pd.Series(dtype=float)
    spread = _load_series_csv(spread_path, value_col='spread')
    tiles = _load_sector_tiles_csv(tiles_path)
    flips = _read_recent_flips(alerts_dir=alerts_dir, hours=24)

    vix_s, vix_val = vix_score(vix)
    ratio_s, ratio_val = ratio_score(ratio)
    yc_s, yc_val = yield_curve_score(spread)
    br_s, br_pct = breadth_score(tiles)
    fl_s, fl_cnt = flips_score(flips)

    scores = {'vix': vix_s, 'ratio': ratio_s, 'yield_curve': yc_s, 'breadth': br_s, 'flips': fl_s}
    idx = composite_risk(scores, weights=weights)
    status = status_from_index(idx)

    record = {
        'ts': datetime.now().isoformat(timespec='seconds'),
        'risk_index': round(idx, 2) if np.isfinite(idx) else None,
        'status': status,
        'vix': vix_val,
        'ratio': ratio_val,
        'yield_curve': yc_val,
        'breadth_pct_strong': br_pct,
        'flips_strong_to_weak': fl_cnt
    }

    return {
        'scores': scores,
        'record': record,
        'status': status,
        'series': {'vix': vix, 'ratio': ratio, 'yield_curve': spread},
        'tiles': tiles,
        'flips_recent': flips
    }
