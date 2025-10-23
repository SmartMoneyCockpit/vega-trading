
"""
Run me once from your repo root:

    python tools/run_sector_tiles_fix.py

What it does:
  1) Lists all files that look like "Sector Momentum Tiles" pages.
  2) Calls tools/normalize_sector_tiles.py to archive duplicates.
  3) Lists again to confirm only src/pages/50_Sector_Momentum_Tiles.py remains.
"""

import os, re, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
keep = ROOT / "src" / "pages" / "50_Sector_Momentum_Tiles.py"

def find_candidates():
    pats = [re.compile(r".*Sector.*Momentum.*Tiles.*\.py$", re.I)]
    hits = []
    for p in ROOT.rglob("*.py"):
        rel = p.relative_to(ROOT).as_posix()
        if any(pat.match(rel) for pat in pats):
            hits.append(rel)
    return sorted(hits)

def main():
    print("=== BEFORE ===")
    for h in find_candidates():
        print("  ", h)

    norm = ROOT / "tools" / "normalize_sector_tiles.py"
    if not norm.exists():
        print("\n[ERROR] tools/normalize_sector_tiles.py not found. Make sure you copied the bundle files.")
        sys.exit(1)

    print("\nRunning normalizer...")
    # Use current Python to run the normalizer
    proc = subprocess.run([sys.executable, str(norm)], cwd=str(ROOT))
    print("\n=== AFTER ===")
    for h in find_candidates():
        print("  ", h)

    if keep.relative_to(ROOT).as_posix() in find_candidates():
        print("\n[OK] The correct page is present:", keep.relative_to(ROOT).as_posix())
        print("Restart Streamlit and click the Sector Momentum Tiles page again.")
    else:
        print("\n[WARN] The target page is missing. Ensure you copied src/pages/50_Sector_Momentum_Tiles.py")

if __name__ == "__main__":
    main()
