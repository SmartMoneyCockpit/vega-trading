# src/engine/smart_money.py
# Force-replace marker (do not remove): VEGA_SMART_MONEY_VERSION=20251023001134
from __future__ import annotations
import os
import pandas as pd

# ---- Defaults for Smart Money thresholds ----
DEFAULTS = {
    "min_rr_ratio": 3.0,
    "earnings_lookahead_days": 30,
    "pop_target": 0.60,
    "vol_ceiling": 2.2,
    "breadth_floor": 0.45,
    "rs_floor": 0.50,
}

def load_config(path: str = "src/config/smart_money.yaml") -> dict:
    try:
        import yaml
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                cfg = yaml.safe_load(f) or {}
            d = DEFAULTS.copy(); d.update(cfg); return d
    except Exception:
        pass
    return DEFAULTS.copy()

# ---- Market inputs (stub; wire to live feeds later) ----
def get_market_inputs(region: str) -> dict:
    presets = {
        "USA":    {"breadth": 0.55, "rs": 0.53, "vol": 1.9},
        "Canada": {"breadth": 0.52, "rs": 0.51, "vol": 1.8},
        "Mexico": {"breadth": 0.50, "rs": 0.49, "vol": 2.0},
        "LATAM":  {"breadth": 0.48, "rs": 0.47, "vol": 2.2},
    }
    return presets.get(region, {"breadth": 0.50, "rs": 0.50, "vol": 2.00})

# ---- Core status ----
def compute_status(region: str) -> dict:
    cfg = load_config()
    m = get_market_inputs(region)
    score = 0.0
    score += max(0.0, m["breadth"] - cfg["breadth_floor"]) * 1.2
    score += max(0.0, m["rs"] - cfg["rs_floor"]) * 1.0
    score += max(0.0, (cfg["vol_ceiling"] - m["vol"])) * 0.2
    score = max(0.0, min(1.0, score))
    light = "🟢 Trade Today" if score >= 0.65 else "🟡 Wait / Selective" if score >= 0.45 else "🔴 Avoid / Hedge"
    return {"region": region, "score": round(score, 3), "light": light, **m}

def make_light_badge(region: str) -> str:
    s = compute_status(region)
    return f"{s['light']}  •  Score {s['score']}  •  Breadth {s['breadth']:.0%}  •  RS {s['rs']:.0%}  •  Vol {s['vol']:.2f}"

# ---- Earnings helpers (TZ-safe) ----
def load_earnings_calendar(path: str = "data/earnings/calendar.csv") -> pd.DataFrame:
    if os.path.exists(path):
        try:
            df = pd.read_csv(path)
            if "symbol" in df.columns and "date" in df.columns:
                df["date"] = pd.to_datetime(df["date"], errors="coerce")
                # Ensure timezone-naive to avoid 'datetime64[ns] vs Timestamp' errors
                try:
                    df["date"] = df["date"].dt.tz_localize(None)
                except Exception:
                    pass
                return df.dropna(subset=["date"])
        except Exception:
            pass
    return pd.DataFrame(columns=["symbol", "date"])

def within_earnings_window(symbol: str, days: int, cal: pd.DataFrame) -> bool:
    if cal.empty:
        return False
    rows = cal[cal["symbol"].str.upper() == symbol.upper()]
    if rows.empty:
        return False
    # Use naive UTC timestamps (dtype=datetime64[ns])
    now = pd.Timestamp.utcnow().normalize()
    future = now + pd.Timedelta(days=days)
    upcoming = rows[(rows["date"] >= now) & (rows["date"] <= future)]
    return not upcoming.empty

# ---- Rule gate used by dashboards ----
def passes_rules(symbol: str, region: str, rr_ratio: float = 3.0, pop: float = 0.60) -> dict:
    """Return dict with 'pass' flag and optional 'reasons' list."""
    cfg = load_config()
    reasons = []

    # Earnings window
    cal = load_earnings_calendar()
    if within_earnings_window(symbol, cfg["earnings_lookahead_days"], cal):
        return {"pass": False, "reasons": ["Within 30 days of earnings"]}

    # Risk/Reward
    if rr_ratio < cfg["min_rr_ratio"]:
        return {"pass": False, "reasons": [f"R/R too low ({rr_ratio}:1)"]}

    # Probability of Profit
    if pop < cfg["pop_target"]:
        reasons.append(f"POP below target ({int(pop*100)}%)")

    # Market regime
    status = compute_status(region)
    if status["light"].startswith("🔴"):
        reasons.append("Market regime red")

    return {"pass": len(reasons) == 0, "reasons": reasons, "status": status}
