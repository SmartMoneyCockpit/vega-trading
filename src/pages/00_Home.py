# src/pages/00_Home.py
import os
import streamlit as st
from pathlib import Path
from src.engine.smart_money import compute_status

try:
    from src.components.tradingview_widgets import economic_calendar
    HAVE_TV = True
except Exception:
    HAVE_TV = False

st.set_page_config(page_title="Home", page_icon="🏠", layout="wide")
st.title("Home — Market Overview")
st.caption("Live overview for Canada, USA, Mexico, LATAM (ex‑Mexico).")

def decision_from_light(light: str) -> str:
    if light.startswith("🟢"): return "Buy Today"
    if light.startswith("🟡"): return "Hold / Wait"
    return "Sell / Avoid"

regions = [("USA","SPY / QQQ"),("Canada","TSX / XIU.TO"),("Mexico","IPC / leaders"),("LATAM","ILF / leaders")]
st.markdown("### 🌎 Market Status by Region")
cols = st.columns(4)
for (name, idx), col in zip(regions, cols):
    with col:
        st.subheader(name)
        s = compute_status(name)
        st.metric("Smart‑Money Score", s["score"], help=f"Breadth {s['breadth']:.0%} • RS {s['rs']:.0%} • Vol {s['vol']:.2f}")
        if s["light"].startswith("🟢"): st.success(s["light"])
        elif s["light"].startswith("🟡"): st.warning(s["light"])
        else: st.error(s["light"])
        st.caption(f"Benchmarks: {idx}")
        st.write(f"**Decision:** {decision_from_light(s['light'])}")

st.divider()
st.markdown("### 🗞️ Major News / Events")
news_root = Path(os.getenv("VEGA_NEWS_PATH", "data/news"))
index_md = news_root / "vega_news.md"
if index_md.exists():
    text = index_md.read_text(encoding="utf-8", errors="ignore")
    lines = text.strip().splitlines()
    # show last 50 lines (most recent posts)
    preview = "\n".join(lines[-50:]) if lines else "No posts yet."
    st.markdown(preview)
else:
    st.info("No news index yet. Your scheduled digests will create it automatically.")

st.divider()
st.markdown("### 🗓️ Economic Calendar (Today)")
if HAVE_TV:
    economic_calendar(country="US,CA,MX", height=280)
else:
    st.caption("TradingView calendar widget unavailable in this build.")
