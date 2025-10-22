# src/engine/smart_money.py
from __future__ import annotations
import os, pandas as pd

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
            with open(path,"r",encoding="utf-8") as f: cfg = yaml.safe_load(f) or {}
            d = DEFAULTS.copy(); d.update(cfg); return d
    except Exception: pass
    return DEFAULTS.copy()

def get_market_inputs(region: str) -> dict:
    presets = {
        "USA":    {"breadth": 0.55, "rs": 0.53, "vol": 1.9},
        "Canada": {"breadth": 0.52, "rs": 0.51, "vol": 1.8},
        "Mexico": {"breadth": 0.50, "rs": 0.49, "vol": 2.0},
        "LATAM":  {"breadth": 0.48, "rs": 0.47, "vol": 2.2},
    }
    return presets.get(region, {"breadth":0.5,"rs":0.5,"vol":2.0})

def compute_status(region: str) -> dict:
    cfg = load_config(); m = get_market_inputs(region)
    score = 0.0
    score += max(0.0, m["breadth"] - cfg["breadth_floor"]) * 1.2
    score += max(0.0, m["rs"] - cfg["rs_floor"]) * 1.0
    score += max(0.0, (cfg["vol_ceiling"] - m["vol"])) * 0.2
    score = max(0.0, min(1.0, score))
    light = "🟢 Trade Today" if score>=0.65 else "🟡 Wait / Selective" if score>=0.45 else "🔴 Avoid / Hedge"
    return {"region":region,"score":round(score,3),"light":light,**m}

def make_light_badge(region: str) -> str:
    s = compute_status(region)
    return f"{s['light']}  •  Score {s['score']}  •  Breadth {s['breadth']:.0%}  •  RS {s['rs']:.0%}  •  Vol {s['vol']:.2f}"
