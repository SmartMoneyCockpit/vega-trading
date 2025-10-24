import os, json
from pathlib import Path
from typing import Any, Dict

DATA_ROOT = os.getenv("VEGA_DATA_ROOT", "data/vega")
TASKS_PATH = os.getenv("VEGA_TASKS_PATH", os.path.join(DATA_ROOT, "owners_tasks.json"))
NOTES_PATH = os.getenv("VEGA_NOTES_PATH", os.path.join(DATA_ROOT, "owners_notes.md"))
PNL_PATH   = os.getenv("VEGA_PNL_TODAY_PATH", os.path.join(DATA_ROOT, "pnl_today.json"))
HEALTH_PATH= os.getenv("VEGA_HEALTH_TODAY_PATH", os.path.join(DATA_ROOT, "health_today.json"))
MR_ROOT    = os.getenv("VEGA_MARKET_REPORTS_ROOT", os.path.join(DATA_ROOT, "market_reports"))
MR_MORNING = os.path.join(MR_ROOT, "morning.txt")
MR_EOD     = os.path.join(MR_ROOT, "evening.txt")

def _ensure_dir(path: str): Path(os.path.dirname(path)).mkdir(parents=True, exist_ok=True)

def _load_json(path: str, default: Any) -> Any:
    try:
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f: return json.load(f)
    except Exception: pass
    return default

def _save_json(path: str, obj: Any) -> None:
    _ensure_dir(path)
    with open(path, "w", encoding="utf-8") as f: json.dump(obj, f, indent=2)

def _load_text(path: str) -> str:
    try:
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f: return f.read().strip()
    except Exception: pass
    return ""

def _save_text(path: str, text: str) -> None:
    _ensure_dir(path)
    with open(path, "w", encoding="utf-8") as f: f.write(text)

def get_tasks() -> Dict: return _load_json(TASKS_PATH, {"tasks": []})
def set_tasks(obj: Dict) -> None: _save_json(TASKS_PATH, obj)
def get_notes() -> str: return _load_text(NOTES_PATH)
def set_notes(text: str) -> None: _save_text(NOTES_PATH, text)
def get_pnl() -> Dict: return _load_json(PNL_PATH, {"realized":0.0,"unrealized":0.0,"total":0.0,"currency":"USD","trades":0})
def get_health() -> Dict: return _load_json(HEALTH_PATH, {"bp_sys":0,"bp_dia":0,"hr":0,"sleep_hours":0.0,"vagal_score":0})
def get_market_reports() -> Dict[str,str]:
    return {"morning": _load_text(MR_MORNING), "evening": _load_text(MR_EOD)}
