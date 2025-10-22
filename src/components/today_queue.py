# src/components/today_queue.py
import os, json, streamlit as st
from pathlib import Path

STORE = os.getenv("VEGA_TODAY_TRADES_PATH", "data/vega/today_trades.json")

def _load():
    try:
        if os.path.exists(STORE):
            with open(STORE,"r",encoding="utf-8") as f: return json.load(f)
    except Exception:
        pass
    return {"tickers":[]}

def _save(obj):
    Path(os.path.dirname(STORE)).mkdir(parents=True, exist_ok=True)
    with open(STORE,"w",encoding="utf-8") as f: json.dump(obj,f,indent=2)

def add(symbol: str, region: str):
    data = _load()
    rec = {"symbol": symbol, "region": region}
    if rec not in data["tickers"]:
        data["tickers"].append(rec)
        _save(data)

def render():
    st.subheader("📌 Today's Trades Queue")
    data = _load()
    if not data["tickers"]:
        st.caption("No tickers yet. Add from scanners or charts.")
        return
    for rec in list(data["tickers"]):
        cols = st.columns([4,2,2])
        with cols[0]: st.code(rec["symbol"])
        with cols[1]: st.write(rec["region"])
        with cols[2]:
            if st.button("Remove", key=f"rm_{rec['symbol']}"):
                data["tickers"].remove(rec); _save(data); st.experimental_rerun()
