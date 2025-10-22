# src/engine/smart_money.py
"""
Vega Smart Money Engine (lightweight wiring)
- Computes 🟢/🟡/🔴 status from inputs: breadth, RS, volatility, earnings window, R/R rule
- Provides filter function for scanned tickers
- Adapters are stubs you can replace with your live sources (Sheets, EODHD, TV, etc.)
"""
from __future__ import annotations
import os, json, math, datetime as dt
from dataclasses import dataclass
from typing import Optional, Dict, Any, List
import pandas as pd

# --- Config ------------------------------------------------------------------
DEFAULTS = {
    "min_rr_ratio": 3.0,     # risk reward must be >= 1:3 (risking 1 to make 3)
    "earnings_lookahead_days": 30,
    "pop_target": 0.60,
    "vol_ceiling": 2.2,      # VIX-like ceiling for green (scaled proxy 0..4)
    "breadth_floor": 0.45,   # % advancers floor for green
    "rs_floor": 0.50,        # relative strength floor
}

def load_config(path: str = "src/config/smart_money.yaml") -> Dict[str, Any]:
    try:
        import yaml
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                cfg = yaml.safe_load(f) or {}
            d = DEFAULTS.copy(); d.update(cfg); return d
    except Exception:
        pass
    return DEFAULTS.copy()

# --- Adapters (replace these with your real sources) --------------------------
def get_market_inputs(region: str) -> Dict[str, float]:
    """
    Return dict with keys: breadth(0-1), rs(0-1), vol(0-4)
    Replace with real data sources. This stub uses simple static numbers.
    """
    # TODO: wire to your Breadth Panel + RS Momentum + VIX proxy
    presets = {
        "USA":    {"breadth": 0.55, "rs": 0.53, "vol": 1.9},
        "Canada": {"breadth": 0.52, "rs": 0.51, "vol": 1.8},
        "Mexico": {"breadth": 0.50, "rs": 0.49, "vol": 2.0},
        "LATAM":  {"breadth": 0.48, "rs": 0.47, "vol": 2.2},
    }
    return presets.get(region, {"breadth":0.5, "rs":0.5, "vol":2.0})

def load_earnings_calendar(path: str = "data/earnings/calendar.csv") -> pd.DataFrame:
    if os.path.exists(path):
        try:
            df = pd.read_csv(path)
            if "symbol" in df.columns and "date" in df.columns:
                df["date"] = pd.to_datetime(df["date"])
                return df
        except Exception:
            pass
    # empty frame
    return pd.DataFrame(columns=["symbol","date"])

# --- Core logic ---------------------------------------------------------------
def compute_status(region: str) -> Dict[str, Any]:
    cfg = load_config()
    mkt = get_market_inputs(region)
    # score 0..1
    score = 0.0
    # Positive breadth & RS help, high vol hurts
    score += max(0.0, mkt["breadth"] - cfg["breadth_floor"]) * 1.2
    score += max(0.0, mkt["rs"] - cfg["rs_floor"]) * 1.0
    score += max(0.0, (cfg["vol_ceiling"] - mkt["vol"])) * 0.2
    # clamp 0..1
    score = max(0.0, min(1.0, score))
    if score >= 0.65:
        light = "🟢 Trade Today"
    elif score >= 0.45:
        light = "🟡 Wait / Selective"
    else:
        light = "🔴 Avoid / Hedge"
    return {"region": region, "score": round(score,3), "light": light, **mkt}

def within_earnings_window(symbol: str, days: int, cal: pd.DataFrame) -> bool:
    if cal.empty: return False
    rows = cal[cal["symbol"].str.upper()==symbol.upper()]
    if rows.empty: return False
    now = pd.Timestamp.now(tz="UTC").normalize()
    future = now + pd.Timedelta(days=days)
    upcoming = rows[rows["date"].between(now, future)]
    return not upcoming.empty

def passes_rules(symbol: str, region: str, rr_ratio: float = 3.0, pop: float = 0.60) -> Dict[str, Any]:
    """
    Return dict with pass flag + reasons. Uses config + earnings window.
    R/R, POP are inputs from your strategy calculator; here we treat them as satisfied
    by default (replace this with your actual numbers).
    """
    cfg = load_config()
    cal = load_earnings_calendar()
    reasons: List[str] = []

    # Rule: no buys within 30 days of earnings
    if within_earnings_window(symbol, cfg["earnings_lookahead_days"], cal):
        return {"pass": False, "reasons": ["Within 30 days of earnings"]}

    # Rule: risk reward must be >= 1:3
    if rr_ratio < cfg["min_rr_ratio"]:
        return {"pass": False, "reasons": [f"R/R too low ({rr_ratio}:1)"]}

    # Rule: POP around 60%
    if pop < cfg["pop_target"]:
        reasons.append(f"POP below target ({pop:.0%})")

    # Market regime: avoid red days
    status = compute_status(region)
    if status["light"].startswith("🔴"):
        reasons.append("Market regime red")

    return {"pass": len(reasons)==0, "reasons": reasons, "status": status}

# Convenience function used by pages
def make_light_badge(region: str) -> str:
    s = compute_status(region)
    return f"{s['light']}  •  Score {s['score']}  •  Breadth {s['breadth']:.0%}  •  RS {s['rs']:.0%}  •  Vol {s['vol']:.2f}"
