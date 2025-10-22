
import json, os, datetime
from pathlib import Path
from typing import List, Dict, Any

NEWS_PATH = Path(os.getenv("VEGA_NEWS_PATH", "/data/vega_news.json"))

def _load() -> List[Dict[str, Any]]:
    if NEWS_PATH.exists():
        try:
            return json.loads(NEWS_PATH.read_text(encoding="utf-8"))
        except Exception:
            return []
    return []

def _save(items: List[Dict[str, Any]]):
    NEWS_PATH.parent.mkdir(parents=True, exist_ok=True)
    NEWS_PATH.write_text(json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8")

def add_update(title: str, html: str, ts_iso: str | None = None, keep_last: int = 30):
    items = _load()
    ts = ts_iso or datetime.datetime.now(datetime.timezone.utc).isoformat()
    items.append({"ts": ts, "title": title, "html": html})
    # retention
    if keep_last and len(items) > keep_last:
        items = sorted(items, key=lambda x: x.get("ts",""), reverse=True)[:keep_last]
    _save(items)
    return True

def get_updates() -> List[Dict[str, Any]]:
    items = _load()
    return sorted(items, key=lambda x: x.get("ts",""), reverse=True)

def export_csv() -> str:
    import csv, io
    items = get_updates()
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["ts","title"])
    for it in items:
        w.writerow([it.get("ts",""), it.get("title","")])
    return buf.getvalue()

def export_pdf(title: str = "Vega News Updates") -> bytes:
    from reportlab.lib.pagesizes import letter
    from reportlab.pdfgen import canvas
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=letter)
    width, height = letter
    y = height - 50
    c.setFont("Helvetica-Bold", 14)
    c.drawString(40, y, title)
    y -= 20
    c.setFont("Helvetica", 10)
    for it in get_updates():
        line = f"{it.get('ts','')}  {it.get('title','')}"
        c.drawString(40, y, line[:110])
        y -= 14
        if y < 50:
            c.showPage(); y = height - 50
    c.save()
    return buf.getvalue()
