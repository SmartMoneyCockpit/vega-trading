# tools/daily_digest.py
"""
Vega Cockpit — Morning/Afternoon Daily Digest
Writes a compact trading digest into VEGA_NEWS_PATH for: USA, Canada, Mexico, LATAM (ex‑Mexico).
Variants:
  --variant morning    (pre‑market)
  --variant afternoon  (post‑market wrap)
Security: requires VEGA_ADMIN_KEY unless --no-auth
"""
from __future__ import annotations
import os, sys, json, time, argparse, datetime as dt
from pathlib import Path

# --- Helpers -----------------------------------------------------------------
def news_root() -> Path:
    base = os.getenv("VEGA_NEWS_PATH", "data/news")
    p = Path(base)
    (p / "posts").mkdir(parents=True, exist_ok=True)
    return p

def iso_now_pt() -> str:
    try:
        import zoneinfo
        tz = zoneinfo.ZoneInfo("America/Los_Angeles")
        return dt.datetime.now(tz).isoformat(timespec="seconds")
    except Exception:
        return dt.datetime.utcnow().isoformat(timespec="seconds") + "Z"

def require_admin_key(passed: str | None) -> None:
    if os.getenv("VEGA_NO_AUTH") == "1":
        return
    envk = os.getenv("VEGA_ADMIN_KEY")
    if not envk:
        return
    if passed != envk:
        print("ERROR: invalid admin key. Set VEGA_ADMIN_KEY or pass --key.", file=sys.stderr)
        sys.exit(2)

# --- Content builders (placeholders wired to your cockpit metrics later) -----
def traffic_light(score: float) -> str:
    # score ∈ [0,1]: >=0.65 🟢, 0.45–0.64 🟡, <0.45 🔴
    if score >= 0.65: return "🟢 Trade Today"
    if score >= 0.45: return "🟡 Wait / Selective"
    return "🔴 Avoid / Hedge"

def build_sections(variant: str) -> dict:
    """Return dict of markdown snippets for each region. Replace placeholders later."""
    if variant not in {"morning","afternoon"}:
        variant = "morning"
    pre = (variant == "morning")

    # Placeholder scoring (wire to breadth/RS/volatility later)
    # Keep deterministic but simple for now.
    base_score = 0.55 if pre else 0.52
    usa_score = base_score + 0.05
    can_score = base_score
    mex_score = base_score - 0.02
    lat_score = base_score - 0.03

    def sec(name, score):
        mood = traffic_light(score)
        lines = []
        if pre:
            lines += [
                f"- **Status**: {mood}",
                "- Futures/Pre‑market: _placeholder_",
                "- Sector tilt: _placeholder_ (leaders/laggards)",
                "- Macro watch: CPI/FOMC/earnings calendar",
                "- Breadth / RS / Volatility snapshot",
            ]
        else:
            lines += [
                f"- **Status**: {mood}",
                "- Close recap: index perf vs benchmarks",
                "- Sector summary: winners/losers",
                "- Notable movers / catalysts",
                "- Breadth / RS trend moves",
                "- Into tomorrow: key levels & events",
            ]
        return "\n".join(lines)

    return {
        "USA": sec("USA", usa_score),
        "Canada": sec("Canada", can_score),
        "Mexico": sec("Mexico", mex_score),
        "LATAM (ex‑Mexico)": sec("LATAM (ex‑Mexico)", lat_score),
        "System": "- Jobs ok • caches warm • alerts self‑silence after trigger • email disabled (in‑app posts only)",
    }

def build_markdown(title: str, sections: dict) -> str:
    order = ["USA","Canada","Mexico","LATAM (ex‑Mexico)","System"]
    lines = [f"# {title}", "", f"_Generated: {iso_now_pt()}_", ""]
    for k in order:
        blk = sections.get(k, "").strip()
        if not blk: continue
        lines += [f"## {k}", blk, ""]
    return "\n".join(lines).strip() + "\n"

def save_post(prefix: str, md: str, meta: dict) -> dict:
    root = news_root()
    ts = dt.datetime.utcnow().strftime("%Y%m%d-%H%M%S")
    slug = f"{prefix}_{ts}"
    md_path = root / "posts" / f"{slug}.md"
    json_path = root / "posts" / f"{slug}.json"
    index_md = root / "vega_news.md"
    md_path.write_text(md, encoding="utf-8")
    json_path.write_text(json.dumps(meta, indent=2), encoding="utf-8")
    with open(index_md, "a", encoding="utf-8") as f:
        f.write(md + "\n---\n\n")
    return {"slug": slug, "md": str(md_path), "json": str(json_path), "index": str(index_md)}

# --- CLI ---------------------------------------------------------------------
def main(argv=None):
    argv = argv or sys.argv[1:]
    ap = argparse.ArgumentParser()
    ap.add_argument("--variant", choices=["morning","afternoon"], default="morning")
    ap.add_argument("--key", default=None)
    ap.add_argument("--no-auth", action="store_true")
    args = ap.parse_args(argv)

    if not args.no_auth:
        require_admin_key(args.key)

    today = dt.date.today().strftime("%a, %b %d")
    title = ("Morning Digest" if args.variant=="morning" else "Afternoon Wrap") + f" — {today}"
    sections = build_sections(args.variant)
    md = build_markdown(title, sections)
    files = save_post(args.variant, md, {"title": title, "variant": args.variant})
    print(json.dumps({"ok": True, "written": files}, indent=2))

if __name__ == "__main__":
    main()
