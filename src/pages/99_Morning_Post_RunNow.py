# src/pages/99_Morning_Post_RunNow.py
import os, json, subprocess, sys, time
import streamlit as st

st.set_page_config(page_title="Morning Post — Run Now", page_icon="📰", layout="centered")
st.title("📰 Morning Post — Run Now")

st.info("Posts are written to **VEGA_NEWS_PATH** (default `./data/news`). Email is disabled; posts appear in the in‑app News panel.")

key = st.text_input("Admin key (must match VEGA_ADMIN_KEY)", type="password")
no_auth = st.checkbox("Bypass auth (local test only)", value=False)

if st.button("Generate Morning Post now"):
    env = os.environ.copy()
    cmd = [sys.executable, "tools/morning_post.py"]
    if key and not no_auth:
        cmd += ["--key", key]
    if no_auth:
        cmd += ["--no-auth"]
    try:
        t0 = time.time()
        res = subprocess.run(cmd, capture_output=True, text=True, env=env, timeout=60)
        dt_ms = int((time.time() - t0)*1000)
        if res.returncode == 0:
            st.success(f"Done in {dt_ms} ms")
            st.code(res.stdout or "OK", language="json")
        else:
            st.error(f"Morning post failed (exit {res.returncode})")
            st.code(res.stderr or res.stdout, language="bash")
    except Exception as e:
        st.exception(e)

st.divider()
st.caption("Tip: schedule via Render Cron at 14:45 UTC (7:45 AM PT during DST).")
