
import os, datetime, requests, streamlit as st

def fetch_eodhd_calendar(date_from, date_to, country_code=None):
    token = os.getenv("EODHD_API_TOKEN", "")
    if not token:
        return {"error": "EODHD_API_TOKEN not set"}
    url = "https://eodhd.com/api/economic-events"
    params = {"from": date_from, "to": date_to, "fmt": "json", "api_token": token}
    if country_code:
        params["country"] = country_code
    try:
        r = requests.get(url, params=params, timeout=20)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        return {"error": str(e)}

def render_calendar(country_name: str, country_code: str):
    st.subheader("📆 Economic Calendar")
    today = datetime.date.today()
    mode = st.radio("Range", ["Today", "Tomorrow", "This Week"], horizontal=True, key=f"cal_{country_code}")
    if mode == "Today":
        d1 = d2 = today
    elif mode == "Tomorrow":
        d1 = d2 = today + datetime.timedelta(days=1)
    else:
        start = today - datetime.timedelta(days=today.weekday())
        end = start + datetime.timedelta(days=6)
        d1, d2 = start, end

    data = fetch_eodhd_calendar(d1.isoformat(), d2.isoformat(), country_code=country_code)
    if isinstance(data, dict) and "error" in data:
        st.warning(f"Calendar unavailable ({data['error']}).")
        return

    if isinstance(data, list) and data:
        cols = st.columns([2,2,5,2,2,2])
        with cols[0]: st.markdown("**Date**")
        with cols[1]: st.markdown("**Time**")
        with cols[2]: st.markdown("**Event**")
        with cols[3]: st.markdown("**Actual**")
        with cols[4]: st.markdown("**Forecast**")
        with cols[5]: st.markdown("**Previous**")
        for item in data:
            c = st.columns([2,2,5,2,2,2])
            with c[0]: st.write(item.get("date") or item.get("datetime",""))
            with c[1]: st.write(item.get("time",""))
            with c[2]: st.write(item.get("event",""))
            with c[3]: st.write(item.get("actual",""))
            with c[4]: st.write(item.get("forecast",""))
            with c[5]: st.write(item.get("previous",""))
    else:
        st.info("No events returned for the selected window.")
