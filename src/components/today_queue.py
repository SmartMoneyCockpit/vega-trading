# src/components/today_queue.py
import os
import json
from pathlib import Path
import streamlit as st

# Storage path (env override supported)
STORE = os.getenv("VEGA_TODAY_TRADES_PATH", "data/vega/today_trades.json")


# ========= low-level I/O =========
def _ensure_dir(p: str) -> None:
    d = os.path.dirname(p)
    if d:
        Path(d).mkdir(parents=True, exist_ok=True)

def _load() -> dict:
    try:
        if os.path.exists(STORE):
            with open(STORE, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception:
        pass
    return {"tickers": []}

def _save(obj: dict) -> None:
    _ensure_dir(STORE)
    tmp = STORE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)
    os.replace(tmp, STORE)


# ========= public API =========
def add(symbol: str, region: str) -> None:
    """Add a ticker to Today's Trades (de-duplicated)."""
    data = _load()
    symbol = (symbol or "").upper()
    rec = {"symbol": symbol, "region": region}
    if rec not in data["tickers"]:
        data["tickers"].append(rec)
        _save(data)

def list_items() -> list[dict]:
    """Return list of {'symbol','region'} currently in Today's Trades."""
    return list(_load().get("tickers", []))

def remove(symbol: str, region: str | None = None) -> bool:
    """Remove a ticker (optionally only for a specific region)."""
    data = _load()
    before = len(data["tickers"])
    symbol = (symbol or "").upper()
    data["tickers"] = [
        t for t in data["tickers"]
        if not (t.get("symbol") == symbol and (region is None or t.get("region") == region))
    ]
    _save(data)
    return len(data["tickers"]) < before

def clear() -> None:
    """Remove all tickers."""
    _save({"tickers": []})

def prune_by(predicate) -> list[str]:
    """
    Keep only items where predicate(symbol, region) returns True.
    Returns list of removed symbols.
    """
    data = _load()
    keep, removed = [], []
    for t in data.get("tickers", []):
        sym = (t.get("symbol") or "").upper()
        reg = t.get("region") or "USA"
        ok = False
        try:
            ok = bool(predicate(sym, reg))
        except Exception:
            ok = False
        if ok:
            keep.append(t)
        else:
            removed.append(sym)
    data["tickers"] = keep
    _save(data)
    return removed


# ========= UI renderer =========
def render() -> None:
    """Streamlit UI: shows the current queue with per-item remove buttons."""
    st.subheader("📌 Today's Trades Queue")
    data = _load()
    tickers = list(data.get("tickers", []))

    if not tickers:
        st.caption("No tickers yet. Add from scanners or charts.")
        return

    for rec in list(tickers):
        cols = st.columns([4, 2, 2])
        with cols[0]:
            st.code(rec.get("symbol", "—"))
        with cols[1]:
            st.write(rec.get("region", "USA"))
        with cols[2]:
            if st.button("Remove", key=f"rm_{rec.get('symbol','')}_{rec.get('region','USA')}"):
                remove(rec.get("symbol", ""), rec.get("region"))
                st.experimental_rerun()
