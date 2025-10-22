
import streamlit as st, pandas as pd, datetime, io
from utils import title_with_flag
from components.news_store import get_updates, add_update, export_csv, export_pdf
from components.vectorvest_scanner import compute_row_metrics

title_with_flag("News Updates", "")
st.caption("Updates are stored at VEGA_NEWS_PATH (default /data/vega_news.json). Kept: last 30.")

# --- Admin security
admin_ok = False
ADMIN_KEY = st.secrets.get("VEGA_ADMIN_KEY", None) or None
if ADMIN_KEY:
    with st.expander("Admin (required to post updates)", expanded=False):
        token = st.text_input("Enter admin key", type="password")
        if st.button("Unlock"):
            if token == ADMIN_KEY:
                admin_ok = True
                st.success("Admin unlocked.")
            else:
                st.error("Invalid key.")
else:
    st.info("VEGA_ADMIN_KEY is not set. Posting controls are visible to all users.")
    admin_ok = True

# --- Timeline UI
st.subheader("Timeline")
updates = get_updates()
for item in updates:
    label = f"🕒 {item.get('ts','')} — {item.get('title','(no title)')}"
    with st.expander(label, expanded=False):
        st.markdown(item.get("html",""), unsafe_allow_html=True)

# --- Exports
c1, c2 = st.columns(2)
with c1:
    if st.button("⬇️ Download CSV"):
        st.download_button("Save CSV", export_csv().encode("utf-8"), file_name="news_updates.csv", mime="text/csv", use_container_width=True)
with c2:
    if st.button("⬇️ Download PDF"):
        pdf = export_pdf()
        st.download_button("Save PDF", pdf, file_name="news_updates.pdf", mime="application/pdf", use_container_width=True)

st.markdown("---")

# --- Composer (secured)
st.subheader("Compose Update")
if admin_ok:
    title = st.text_input("Title", "A+ Setups — Midday Digest")
    html = st.text_area("HTML Content (HTML supported)", "<h3>A+ Setups</h3><ul><li>SPY — Buy Today (VST 1.12)</li></ul>", height=240)
    if st.button("Post to News Updates"):
        if add_update(title, html, keep_last=30):
            st.success("Posted to News Updates.")
else:
    st.warning("Admin key required to post.")

# --- Midday Generator (12:45 PM PT) — manual trigger; auto-run via CLI in tools/midday_post.py
st.subheader("Midday 12:45 PM PT — Generate Now")
if admin_ok and st.button("Generate Midday Update Now"):
    # Default watchlists
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
        if 'VST' in df.columns:
            df = df.sort_values(['VST','%'], ascending=[False,False]).head(3)
        elif '%' in df.columns:
            df = df.sort_values('%', ascending=False).head(3)
        parts = [f"<h4>{country}</h4><table><tr><th>Ticker</th><th>%</th><th>VST</th></tr>"]
        for _, r in df.iterrows():
            parts.append(f"<tr><td>{r.get('ticker')}</td><td>{r.get('%')}</td><td>{r.get('VST')}</td></tr>")
        parts.append("</table>")
        return "\n".join(parts)

    now_pt = datetime.datetime.now(datetime.timezone.utc).astimezone(datetime.ZoneInfo("America/Los_Angeles"))
    title = f"Midday Update — {now_pt.strftime('%Y-%m-%d %H:%M %Z')}"
    html = []
    html.append("<h3>Market Midday Highlights</h3>")
    html.append(_gather("Canada", wl_can, "TO"))
    html.append(_gather("United States", wl_usa, "US"))
    html.append(_gather("Mexico", wl_mex, "MX"))
    payload = "\n".join([p for p in html if p])
    if payload.strip():
        add_update(title, payload, keep_last=30)
        st.success("Midday update posted.")
    else:
        st.warning("No data to post.")
