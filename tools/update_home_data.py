
#!/usr/bin/env python3
"""
Update Home dashboard data files:
- data/breadth.json
- data/modes.json
- data/news.json

Dependencies: yfinance, pandas, numpy, feedparser
"""

import os
import json
import time
import math
import datetime as dt
from typing import Dict, List

# Soft deps
try:
    import yfinance as yf
except Exception as e:
    yf = None

try:
    import feedparser
except Exception as e:
    feedparser = None

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DATA_DIR = os.path.join(ROOT, "data")
os.makedirs(DATA_DIR, exist_ok=True)

# -----------------------------
# Config
# -----------------------------
REGIONS = {
    "USA":    {"index": "SPY",   "breadth_basket": ["SPY","QQQ","DIA","IWM","XLF","XLK","XLE","XLI","XLP","XLV","XLU"]},
    "Canada": {"index": "XIU.TO","breadth_basket": ["XIU.TO","XFN.TO","XIT.TO","XEG.TO","XMA.TO","XIC.TO"]},
    "Mexico": {"index": "EWW",   "breadth_basket": ["EWW"]},
    "LATAM":  {"index": "ILF",   "breadth_basket": ["ILF","EWZ","ECH","EWW","EPU"]},
}

NEWS_FEEDS = [
    ("Reuters Markets", "http://feeds.reuters.com/reuters/businessNews"),
    ("Bloomberg Markets", "https://www.bloomberg.com/feeds/podcasts/etf_report.xml"),  # sometimes empty
    ("Globe & Mail Business", "https://www.theglobeandmail.com/rss/business/"),
    ("El Financiero (MX) Markets", "https://www.elfinanciero.com.mx/arc/outboundfeeds/rss/?outputType=xml"),
    ("Financial Times Markets", "https://www.ft.com/markets?format=rss"),
]

# -----------------------------
# Helpers
# -----------------------------
def now_pt() -> str:
    # Show PT timestamp for the user's preference
    # Not doing tz conversion: just labeling local time; callers may adjust.
    return dt.datetime.now().strftime("%Y-%m-%d %H:%M")

def safe_write_json(path: str, obj):
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)
    os.replace(tmp, path)

def fetch_change_percent(ticker: str) -> float:
    """Return today's % change using yfinance (regular market)."""
    if yf is None:
        return float("nan")
    try:
        t = yf.Ticker(ticker)
        df = t.history(period="2d", interval="1d", auto_adjust=False)
        if df is None or df.empty or "Close" not in df.columns:
            return float("nan")
        if len(df) == 1:
            # No yesterday: 0 change
            return 0.0
        prev = float(df["Close"].iloc[-2])
        curr = float(df["Close"].iloc[-1])
        if prev == 0:
            return 0.0
        return (curr - prev) / prev
    except Exception:
        return float("nan")

def compute_breadth(basket: List[str]) -> float:
    """Breadth = % of basket showing positive day change."""
    ups = 0
    total = 0
    for sym in basket:
        chg = fetch_change_percent(sym)
        if math.isnan(chg):
            continue
        total += 1
        if chg > 0:
            ups += 1
    if total == 0:
        return float("nan")
    return ups / total

def classify_mode(index_symbol: str, breadth_val: float) -> str:
    """Very simple mode rules to start; adjust as needed.
       - If breadth >= 0.60 and index day change >= +0.30% => Buy
       - If breadth <= 0.40 and index day change <= -0.30% => Sell
       - Otherwise Hold
    """
    chg = fetch_change_percent(index_symbol)
    if math.isnan(chg) or math.isnan(breadth_val):
        return "Hold"
    if breadth_val >= 0.60 and chg >= 0.003:
        return "Buy"
    if breadth_val <= 0.40 and chg <= -0.003:
        return "Sell"
    return "Hold"

def build_news_items(max_items: int = 12) -> List[dict]:
    items = []
    if feedparser is None:
        return items
    for name, url in NEWS_FEEDS:
        try:
            feed = feedparser.parse(url)
            for e in feed.entries[:5]:
                title = e.get("title", "(no title)")
                link  = e.get("link", "")
                pub   = e.get("published", "") or e.get("updated", "")
                items.append({"title": title, "source": name, "ts": pub, "url": link})
                if len(items) >= max_items:
                    return items
        except Exception:
            continue
    return items[:max_items]

# -----------------------------
# Main
# -----------------------------
def main():
    # Compute breadth and modes
    breadth_out = {}
    modes_out = {}
    # simple composite score to mirror your current banner
    try:
        score_parts = []
        for region, cfg in REGIONS.items():
            b = compute_breadth(cfg["breadth_basket"])
            breadth_out[region] = None if math.isnan(b) else round(float(b), 3)
            mode = classify_mode(cfg["index"], breadth_out[region] if breadth_out[region] is not None else float("nan"))
            modes_out[region.lower()] = mode
            if breadth_out[region] is not None:
                score_parts.append(f"{region} breadth {int(breadth_out[region]*100)}% ({mode})")
        composite = " · ".join(score_parts) if score_parts else "Session"
        modes_out["score"] = composite
        modes_out["summary"] = f"Updated {now_pt()}"
    except Exception as e:
        modes_out["score"] = "Session"
        modes_out["summary"] = f"Updated {now_pt()} (partial data)"

    # News
    news_out = {"items": build_news_items()}

    # Write files
    safe_write_json(os.path.join(DATA_DIR, "breadth.json"), breadth_out)
    safe_write_json(os.path.join(DATA_DIR, "modes.json"), modes_out)
    safe_write_json(os.path.join(DATA_DIR, "news.json"), news_out)

    print("Updated:")
    print(os.path.join(DATA_DIR, "breadth.json"))
    print(os.path.join(DATA_DIR, "modes.json"))
    print(os.path.join(DATA_DIR, "news.json"))

if __name__ == "__main__":
    main()
