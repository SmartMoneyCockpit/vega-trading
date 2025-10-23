
"""
normalize_sector_tiles.py
Move old/duplicate Sector Momentum Tiles pages to _archive/ so Streamlit shows only the new one.

Run:
  python tools/normalize_sector_tiles.py
"""
import os, re, shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
archive = ROOT / "_archive"
archive.mkdir(exist_ok=True)

keep = ROOT / "src" / "pages" / "50_Sector_Momentum_Tiles.py"
patterns = [
    re.compile(r"^pages/.*Sector.*Momentum.*Tiles.*\.py$", re.I),
    re.compile(r"^src/pages/(?!50_).*Sector.*Momentum.*Tiles.*\.py$", re.I),
]

def move_if_match(p: Path):
    rel = p.relative_to(ROOT).as_posix()
    if rel == keep.relative_to(ROOT).as_posix():  # skip keeper
        return False
    for pat in patterns:
        if pat.match(rel):
            dst = archive / p.name
            try:
                shutil.move(str(p), str(dst))
                print(f"[OK] Archived duplicate: {rel} -> _archive/{p.name}")
                return True
            except Exception as e:
                print(f"[ERR] Failed to move {rel}: {e}")
                return False
    return False

moved = 0
for p in ROOT.rglob("*.py"):
    moved += 1 if move_if_match(p) else 0

if moved == 0:
    print("[SKIP] No duplicates found. Nothing moved.")
else:
    print(f"[DONE] Archived {moved} duplicate page(s). Keep file: {keep}")
