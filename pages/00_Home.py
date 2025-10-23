
import os
import json
import datetime as dt
import streamlit as st

# ===== Optional project widgets (graceful fallbacks) =====
try:
    from src.components.tradingview_widgets import advanced_chart  # project-native
except Exception:
    advanced_chart = None

st.set_page_config(page_title="Home • Vega", page_icon="🏠", layout="wide")

# -----------------------------
# Helper: tiny badge/metric tile
# -----------------------------
def badge(label:str, value:str, help_text:str=""):
    with st.container(border=True):
        st.caption(label)
        st.markdown(f"### {value}")
        if help_text:
            st.write(help_text)

# -----------------------------
# Helper: load optional data
# -----------------------------
def load_json(path, default=None):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default

# Optional inputs (drop-in friendly)
breadth = load_json("data/breadth.json", default=None)
modes   = load_json("data/modes.json",   default=None)  # Buy/Sell/Hold per region
news    = load_json("data/news.json",    default={"items": []})

# Regions + symbols (edit here if you want different indices/ETFs)
REGIONS = [
    {"name":"USA",    "symbol":"SPY",     "fallback":"US market (SPY)"},
    {"name":"Canada", "symbol":"XIU.TO",  "fallback":"Canada TSX (XIU.TO)"},
    {"name":"Mexico", "symbol":"EWW",     "fallback":"Mexico (EWW)"},
    {"name":"LATAM",  "symbol":"ILF",     "fallback":"Latin America (ILF)"},
]

# -----------------------------
# Header: instant read panel
# -----------------------------
st.title("Home")
st.caption("One-glance market view — charts, breadth, news, and day mode (Buy / Hold / Sell).")

with st.container(border=True):
    cols = st.columns([1.2,1,1,1,1])
    # Score pill (optional composite if provided)
    with cols[0]:
        today = dt.datetime.now().strftime("%Y-%m-%d %H:%M")
        st.markdown(f"**Session:** {today}")
        if modes and isinstance(modes, dict) and "score" in modes:
            score = modes.get("score")
            summary = modes.get("summary", "")
            st.markdown(f"### {score}")
            if summary:
                st.write(summary)
        else:
            st.markdown("### Session Status")
            st.caption("Provide `data/modes.json` for composite score.")

    # Region badges (Buy/Hold/Sell + breadth if present)
    for i, region in enumerate(REGIONS, start=1):
        with cols[i]:
            mode = None
            if modes and isinstance(modes, dict):
                mode = modes.get(region["name"].lower()) or modes.get(region["name"])
            if not mode:
                mode = "—"
            b = None
            if breadth and isinstance(breadth, dict):
                b = breadth.get(region["name"].lower()) or breadth.get(region["name"])
            badge(
                label=f"{region['name']}",
                value=f"{mode}",
                help_text=f"Breadth: {b}"
                          if b is not None else "Breadth: n/a"
            )

# -----------------------------
# Charts row (4-up, fast glance)
# -----------------------------
st.markdown("#### Major Indices")
c1, c2, c3, c4 = st.columns(4, gap="small")

def render_chart(container, title, symbol):
    with container:
        st.markdown(f"**{title} — {symbol}**")
        if advanced_chart:
            # project-native TradingView widget (clean, fast)
            try:
                advanced_chart(symbol=symbol, height=260, studies=["EMA 20", "EMA 50", "RSI"])
            except Exception as e:
                st.info(f"Widget error, falling back. ({e})")
                tv_embed(symbol)
        else:
            tv_embed(symbol)

def tv_embed(symbol:str):
    import streamlit.components.v1 as components
    html = """
    <div class='tradingview-widget-container'>
      <div id='tradingview_{sym}' style='height:260px;'></div>
      <script type='text/javascript' src='https://s3.tradingview.com/tv.js'></script>
      <script type='text/javascript'>
      new TradingView.widget({{
        "width": "100%",
        "height": 260,
        "symbol": "{sym}",
        "interval": "60",
        "timezone": "Etc/UTC",
        "theme": "dark",
        "style": "1",
        "locale": "en",
        "hide_top_toolbar": true,
        "hide_legend": false,
        "save_image": false,
        "studies": ["RSI@tv-basicstudies", "MASimple@tv-basicstudies"],
        "container_id": "tradingview_{sym}"
      }});
      </script>
    </div>
    """.replace("{sym}", symbol)
    components.html(html, height=270)

render_chart(c1, "USA",    "SPY")
render_chart(c2, "Canada", "XIU.TO")
render_chart(c3, "Mexico", "EWW")
render_chart(c4, "LATAM",  "ILF")

# -----------------------------
# Breadth + News
# -----------------------------
left, right = st.columns([1,1.1])

with left:
    st.markdown("#### Market Breadth")
    if breadth:
        for region in REGIONS:
            key = region["name"]
            val = breadth.get(key.lower()) or breadth.get(key)
            if val is None:
                continue
            with st.container(border=True):
                st.caption(f"{key} breadth")
                st.progress(min(max(float(val), 0.0), 1.0), text=f"Advancing {(float(val)*100):.0f}%")
    else:
        st.info("Drop a simple JSON at `data/breadth.json` like:\n"
                "{\n  \"USA\": 0.55,\n  \"Canada\": 0.48,\n  \"Mexico\": 0.61,\n  \"LATAM\": 0.52\n}")

with right:
    st.markdown("#### News (Latest)")
    items = news.get("items", []) if isinstance(news, dict) else []
    if items:
        for n in items[:10]:
            title = n.get("title","(no title)")
            src   = n.get("source","")
            ts    = n.get("ts","")
            url   = n.get("url","")
            with st.container(border=True):
                st.markdown(f"**{title}**")
                meta = " • ".join([s for s in [src, ts] if s])
                if meta:
                    st.caption(meta)
                if url:
                    st.link_button("Open", url, use_container_width=True)
    else:
        st.info("Provide `data/news.json` with `items: [{title, source, ts, url}]`.")

# -----------------------------
# Footer: quick instructions
# -----------------------------
with st.expander("How to feed real data quickly (one-time setup)"):
    st.markdown(
        """
        **Breadth:** write a JSON file to `data/breadth.json` with 0-1 values per region (advancers %).  
        **Modes:** write `data/modes.json` with keys `usa`, `canada`, `mexico`, `latam` set to `"Buy"`, `"Hold"`, or `"Sell"`.  
        Optionally include a composite `"score"` and `"summary"` for the header pill.  
        **News:** write `data/news.json` with `{"items": [{"title": "...", "source": "...", "ts": "...", "url": "..."}]}`.  
        **Symbols:** edit the `REGIONS` list at the top of this file to map to your preferred indices/ETFs.
        """
    )
