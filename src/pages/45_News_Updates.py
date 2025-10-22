
import streamlit as st, pandas as pd, datetime
from utils import title_with_flag
from components.news_store import get_updates, add_update
from components.vectorvest_scanner import compute_row_metrics

title_with_flag("News Updates", "")
st.caption("All updates are stored locally in the app and shown newest first.")

# --- Timeline ---
updates = get_updates()
for item in updates:
    with st.expander(f"🕒 {item.get('ts','')} — {item.get('title','(no title)')}", expanded=False):
        st.markdown(item.get("html",""), unsafe_allow_html=True)

st.markdown("---")
st.subheader("Midday 12:45 PM Update (PT)")

# Default watchlists (same as scanners)
wl_can = ['ZEB','CPD','ZPR','HPR','ZGRO']
wl_usa = ['SPY','AMZN','NEE','QQQ','RWM','SQQQ']
wl_mex = ['WALMEX','GMEXICO','KIMBER','ALFA']

def _gather(country: str, tickers, exch):
    rows = []
    for t in tickers:
        row = compute_row_metrics(t, exch, is_canada=(country=='Canada'))
        if 'error' in row:
            continue
        rows.append(row)
    if not rows:
        return ""
    df = pd.DataFrame(rows)
    # Pick top 3 by VST (if present), else by %
    if 'VST' in df.columns:
        df = df.sort_values(['VST','%'], ascending=[False,False]).head(3)
    elif '%' in df.columns:
        df = df.sort_values('%', ascending=False).head(3)
    # Build HTML block
    parts = [f"<h4>{country}</h4><table><tr><th>Ticker</th><th>%</th><th>VST</th></tr>"]
    for _, r in df.iterrows():
        parts.append(f"<tr><td>{r.get('ticker')}</td><td>{r.get('%')}</td><td>{r.get('VST')}</td></tr>")
    parts.append("</table>")
    return "\n".join(parts)

if st.button("Generate Midday Update Now"):
    now_pt = datetime.datetime.now(datetime.timezone.utc).astimezone(datetime.ZoneInfo("America/Los_Angeles"))
    title = f"Midday Update — {now_pt.strftime('%Y-%m-%d %H:%M %Z')}"
    html = []
    html.append("<h3>Market Midday Highlights</h3>")
    html.append(_gather("Canada", wl_can, "TO"))
    html.append(_gather("United States", wl_usa, "US"))
    html.append(_gather("Mexico", wl_mex, "MX"))
    payload = "\n".join([p for p in html if p])
    if not payload.strip():
        st.warning("No data to post.")
    else:
        add_update(title, payload)
        st.success("Midday update posted. Refresh to view at the top.")
