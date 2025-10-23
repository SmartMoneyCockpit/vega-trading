# src/engine/smart_money.py
from __future__ import annotations
import os
import pandas as pd
from pathlib import Path

DEBUG = os.getenv("VEGA_DEBUG", "0") == "1"

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

def get_market_inputs(region: str) -> dict:
    presets = {
        "USA":    {"breadth": 0.55, "rs": 0.53, "vol": 1.9},
        "Canada": {"breadth": 0.52, "rs": 0.51, "vol": 1.8},
        "Mexico": {"breadth": 0.50, "rs": 0.49, "vol": 2.0},
        "LATAM":  {"breadth": 0.48, "rs": 0.47, "vol": 2.2},
    }
    return presets.get(region, {"breadth": 0.50, "rs": 0.50, "vol": 2.00})

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
                # Ensure timezone-naive
                try:
                    df["date"] = df["date"].dt.tz_localize(None)
                except Exception:
                    pass
                return df.dropna(subset=["date"])
        except Exception:
            pass
    return pd.DataFrame(columns=["symbol", "date"])

def _debug_write(symbol: str, cal: pd.DataFrame, now: pd.Timestamp, future: pd.Timestamp, subset: pd.DataFrame, note: str = ""):
    try:
        root = Path("data/vega/debug"); root.mkdir(parents=True, exist_ok=True)
        p = root / f"earnings_debug_{symbol}.txt"
        lines = []
        lines.append(f"NOTE: {note}")
        lines.append(f"now={now!r} (tzinfo={getattr(now, 'tzinfo', None)})  dtype={type(now)}")
        lines.append(f"future={future!r}")
        lines.append(f"cal.dtypes=\n{cal.dtypes}")
        lines.append(f"cal.head(5)=\n{cal.head(5)}")
        lines.append(f"subset({symbol}).dtypes=\n{subset.dtypes}")
        lines.append(f"subset.head(5)=\n{subset.head(5)}")
        p.write_text("\n\n".join(lines), encoding="utf-8")
        print(f"[VEGA DEBUG] wrote {p}")
    except Exception as e:
        print(f"[VEGA DEBUG] failed to write diagnostics: {e}")

def within_earnings_window(symbol: str, days: int, cal: pd.DataFrame) -> bool:
    if cal.empty:
        return False
    rows = cal[cal["symbol"].str.upper() == symbol.upper()]
    if rows.empty:
        return False
    now = pd.Timestamp.utcnow().normalize()  # naive UTC
    future = now + pd.Timedelta(days=days)
    try:
        mask = (rows["date"] >= now) & (rows["date"] <= future)
    except Exception as e:
        if DEBUG:
            _debug_write(symbol, cal, now, future, rows, note=f"comparison error: {e}")
        raise
    if DEBUG:
        _debug_write(symbol, cal, now, future, rows.loc[mask], note="ok")
    return bool(mask.any())

def passes_rules(symbol: str, region: str, rr_ratio: float = 3.0, pop: float = 0.60) -> dict:
    cfg = load_config()
    reasons = []

    cal = load_earnings_calendar()
    try:
        if within_earnings_window(symbol, cfg["earnings_lookahead_days"], cal):
            return {"pass": False, "reasons": ["Within 30 days of earnings"]}
    except Exception as e:
        # bubble up a short message so UI shows reason
        return {"pass": False, "reasons": [f"earnings-window error: {e}"]}

    if rr_ratio < cfg["min_rr_ratio"]:
        return {"pass": False, "reasons": [f"R/R too low ({rr_ratio}:1)"]}

    if pop < cfg["pop_target"]:
        reasons.append(f"POP below target ({int(pop*100)}%)")

    status = compute_status(region)
    if status["light"].startswith("🔴"):
        reasons.append("Market regime red")

    return {"pass": len(reasons) == 0, "reasons": reasons, "status": status}
