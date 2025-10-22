
# CLI tool to generate the 12:45 PM PT News Update (no UI, cron-friendly).
# Run command on Render (Cron Job):  python tools/midday_post.py
import os, datetime, sys
from pathlib import Path
# Reuse app modules
sys.path.append(str(Path(__file__).resolve().parents[1]))
from src.components.news_store import add_update
from src.components.vectorvest_scanner import compute_row_metrics
import pandas as pd

WL_CAN = ['ZEB','CPD','ZPR','HPR','ZGRO']
WL_USA = ['SPY','AMZN','NEE','QQQ','RWM','SQQQ']
WL_MEX = ['WALMEX','GMEXICO','KIMBER','ALFA']

def _gather(country: str, tickers, exch):
    rows = []
    for t in tickers:
        row = compute_row_metrics(t, exch, is_canada=(country=='Canada'))
        if 'error' in row: continue
        rows.append(row)
    if not rows: return ""
    df = pd.DataFrame(rows)
    if 'VST' in df.columns:
        df = df.sort_values(['VST','%'], ascending=[False,False]).head(3)
    elif '%' in df.columns:
        df = df.sort_values('%', ascending=False).head(3)
    parts = [f"<h4>{country}</h4><table><tr><th>Ticker</th><th>%</th><th>VST</th></tr>"]
    for _, r in df.iterrows():
        parts.append(f"<tr><td>{r.get('ticker')}</td><td>{r.get('%')}</td><td>{r.get('VST')}</td></tr>")
    parts.append("</table>")
    return "\n".join(parts)

def main():
    now_pt = datetime.datetime.now(datetime.timezone.utc).astimezone(datetime.ZoneInfo("America/Los_Angeles"))
    title = f"Midday Update — {now_pt.strftime('%Y-%m-%d %H:%M %Z')}"
    html = []
    html.append("<h3>Market Midday Highlights</h3>")
    html.append(_gather("Canada", WL_CAN, "TO"))
    html.append(_gather("United States", WL_USA, "US"))
    html.append(_gather("Mexico", WL_MEX, "MX"))
    payload = "\n".join([p for p in html if p])
    if payload.strip():
        add_update(title, payload, keep_last=30)
        print("Midday update posted.")
    else:
        print("No data to post.")

if __name__ == "__main__":
    main()
