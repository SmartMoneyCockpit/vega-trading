# tools/morning_post.py
"""
Vega Cockpit — Morning Post Generator (7:45 AM PT pre‑market summary)
- Writes a markdown + json post into VEGA_NEWS_PATH (or ./data/news by default)
- Optional external headlines hook (disabled by default; toggle in settings.yaml)
- Locked behind VEGA_ADMIN_KEY (env) unless --no-auth is passed (for local tests)
"""
from __future__ import annotations
import os, sys, json, time, argparse, datetime as dt
from pathlib import Path

# --- Settings (simple yaml-less fallback) ------------------------------------
DEFAULT_SETTINGS = {
    "EXTERNAL_HEADLINES_ENABLED": False,
    "EXTERNAL_HEADLINES_LIMIT": 8,
    "COUNTRY_GROUPS": ["USA", "Canada", "Mexico", "System", "News"],
}
SETTINGS_PATH = os.getenv("VEGA_SETTINGS_PATH", "src/config/settings.yaml")

def load_settings() -> dict:
    try:
        import yaml  # optional dependency in your app; if missing we fallback
        if os.path.exists(SETTINGS_PATH):
            with open(SETTINGS_PATH, "r", encoding="utf-8") as f:
                cfg = yaml.safe_load(f) or {}
            return {**DEFAULT_SETTINGS, **cfg}
    except Exception:
        pass
    return DEFAULT_SETTINGS.copy()

# --- Optional external headlines hook ----------------------------------------
def get_external_headlines(limit: int = 8):
    """
    Import and call tools.headlines_hook:get_headlines() if present.
    Must return a list[dict] with keys: title, url (optional), source (optional).
    """
    try:
        from tools.headlines_hook import get_headlines  # type: ignore
        items = get_headlines(limit=limit) or []
        # simple normalization
        out = []
        for x in items[:limit]:
            if isinstance(x, dict):
                out.append({
                    "title": x.get("title", ""),
                    "url": x.get("url"),
                    "source": x.get("source"),
                })
            elif isinstance(x, str):
                out.append({"title": x})
        return out
    except Exception:
        return []

# --- Security ----------------------------------------------------------------
def require_admin_key(passed_key: str | None) -> None:
    if os.getenv("VEGA_NO_AUTH") == "1":
        return
    if passed_key == "":
        passed_key = None
    env_key = os.getenv("VEGA_ADMIN_KEY")
    if not env_key:
        # No env key set → allow run but warn
        return
    if passed_key != env_key:
        print("ERROR: invalid admin key. Set VEGA_ADMIN_KEY or pass --key.", file=sys.stderr)
        sys.exit(2)

# --- Writer helpers -----------------------------------------------------------
def news_root() -> Path:
    base = os.getenv("VEGA_NEWS_PATH", "data/news")
    p = Path(base)
    (p / "posts").mkdir(parents=True, exist_ok=True)
    return p

def iso_now_pt() -> str:
    # Display timestamp in Pacific Time
    try:
        import zoneinfo
        tz = zoneinfo.ZoneInfo("America/Los_Angeles")
        return dt.datetime.now(tz).isoformat(timespec="seconds")
    except Exception:
        return dt.datetime.utcnow().isoformat(timespec="seconds") + "Z"

def build_markdown(title: str, sections: dict, headlines: list[dict]) -> str:
    lines = [f"# {title}", "", f"_Generated: {iso_now_pt()}_",""]
    # Country sections
    for name in ["USA","Canada","Mexico","System","News"]:
        block = sections.get(name, "").strip()
        if not block:
            continue
        lines.append(f"## {name}")
        lines.append(block)
        lines.append("")
    # External headlines
    if headlines:
        lines.append("## Headlines")
        for h in headlines:
            ttl = h.get("title","").strip()
            url = h.get("url")
            src = h.get("source")
            bullet = f"- {ttl}"
            if src:
                bullet += f" — _{src}_"
            if url:
                bullet += f"  \n  {url}"
            lines.append(bullet)
        lines.append("")
    return "\n".join(lines).strip() + "\n"

def generate_content() -> dict:
    # Placeholder content; your cockpit can later replace with real data pulls
    today = dt.date.today().strftime("%a, %b %d")
    title = f"Pre‑Market Summary — {today}"
    sections = {
        "USA": "- Benchmarks: SPY/QQQ futures overview\n- FX overlay if material\n- Sector leaders/laggards\n- Notable catalysts (CPI/FOMC/etc.)",
        "Canada": "- TSX futures / sector snapshot\n- Tariff‑resilient ideas\n- CAD‑USD FX note if material",
        "Mexico": "- IPC overview\n- USDMXN watch\n- Key movers / catalysts",
        "System": "- Latency OK, jobs green, caches warm\n- Auto‑hedging engine: standby\n- Alerts: self‑silenced after triggers per rule",
        "News": "- In‑app posts only (email disabled)\n- Manual ‘Run Now’ available in Admin tools",
    }
    return {"title": title, "sections": sections}

def save_post(md: str, meta: dict) -> dict:
    root = news_root()
    ts = dt.datetime.utcnow().strftime("%Y%m%d-%H%M%S")
    slug = f"morning_{ts}"
    md_path = root / "posts" / f"{slug}.md"
    json_path = root / "posts" / f"{slug}.json"
    index_md = root / "vega_news.md"
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(md)
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2)
    # Append to rolling index (simple feed)
    with open(index_md, "a", encoding="utf-8") as f:
        f.write(md + "\n---\n\n")
    return {"slug": slug, "md": str(md_path), "json": str(json_path), "index": str(index_md)}

def main(argv=None):
    argv = argv or sys.argv[1:]
    ap = argparse.ArgumentParser()
    ap.add_argument("--key", default=None, help="Admin key (matches VEGA_ADMIN_KEY)")
    ap.add_argument("--no-auth", action="store_true", help="Bypass key check (local testing)")
    args = ap.parse_args(argv)

    if not args.no_auth:
        require_admin_key(args.key)

    t0 = time.time()
    cfg = load_settings()
    payload = generate_content()

    headlines = []
    if cfg.get("EXTERNAL_HEADLINES_ENABLED"):
        headlines = get_external_headlines(limit=int(cfg.get("EXTERNAL_HEADLINES_LIMIT", 8)))

    md = build_markdown(payload["title"], payload["sections"], headlines)
    files = save_post(md, {"title": payload["title"], "headlines_count": len(headlines)})
    dt_ms = int((time.time() - t0) * 1000)

    print(json.dumps({
        "ok": True,
        "written": files,
        "latency_ms": dt_ms
    }, indent=2))

if __name__ == "__main__":
    main()
