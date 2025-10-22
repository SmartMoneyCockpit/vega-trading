
import streamlit as st, os, platform, time
from utils import title_with_flag
title_with_flag("System Status", "")
st.write({"python": platform.python_version(), "platform": platform.platform()})
st.write({"EODHD_API_TOKEN_set": bool(os.getenv("EODHD_API_TOKEN"))})
st.write({"time": time.ctime()})


import time
from src.eodhd_client import get_price_quote

st.markdown("### API Health Test")
t0 = time.time()
q = get_price_quote("SPY","US")
dt = (time.time() - t0)*1000
if "error" in q:
    st.error(f"EODHD quote error: {q['error']}")
else:
    st.success(f"EODHD OK. Latency: {dt:.0f} ms, Price: {q.get('close')}")

st.markdown("### Email Digest")
import os
st.write({"SENDGRID_API_KEY_set": bool(os.getenv("SENDGRID_API_KEY"))})
