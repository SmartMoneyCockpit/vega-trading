# src/pages/98_Daily_Digest_RunNow.py
import os, sys, time, subprocess, json
import streamlit as st

st.set_page_config(page_title="Daily Digest — Run Now", page_icon="🗞️", layout="centered")
st.title("🗞️ Daily Digest — Run Now")

variant = st.selectbox("Variant", ["morning","afternoon"], index=0)
key = st.text_input("Admin key (VEGA_ADMIN_KEY)", type="password")
no_auth = st.checkbox("Bypass auth (local only)", value=False)

if st.button("Generate"):
    env = os.environ.copy()
    cmd = [sys.executable, "tools/daily_digest.py", "--variant", variant]
    if no_auth:
        cmd += ["--no-auth"]
    elif key:
        cmd += ["--key", key]
    try:
        t0 = time.time()
        res = subprocess.run(cmd, capture_output=True, text=True, env=env, timeout=60)
        ms = int((time.time()-t0)*1000)
        if res.returncode == 0:
            st.success(f"Generated in {ms} ms")
            st.code(res.stdout or "OK", language="json")
        else:
            st.error(f"Failed (exit {res.returncode})")
            st.code(res.stderr or res.stdout, language="bash")
    except Exception as e:
        st.exception(e)

st.caption("Posts are appended to `data/news/vega_news.md` for the in‑app News panel.")
