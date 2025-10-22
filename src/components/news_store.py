
import json, os, datetime
from pathlib import Path

NEWS_PATH = Path(os.getenv("VEGA_NEWS_PATH", "/tmp/vega_news.json"))

def _load():
    if NEWS_PATH.exists():
        try:
            return json.loads(NEWS_PATH.read_text(encoding="utf-8"))
        except Exception:
            return []
    return []

def _save(items):
    NEWS_PATH.parent.mkdir(parents=True, exist_ok=True)
    NEWS_PATH.write_text(json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8")

def add_update(title: str, html: str, ts_iso: str | None = None):
    items = _load()
    ts = ts_iso or datetime.datetime.now(datetime.timezone.utc).isoformat()
    items.append({"ts": ts, "title": title, "html": html})
    _save(items)
    return True

def get_updates():
    return sorted(_load(), key=lambda x: x.get("ts",""), reverse=True)
