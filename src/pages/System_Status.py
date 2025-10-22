
import streamlit as st, os, platform, time
from utils import title_with_flag
title_with_flag("System Status", "")
st.write({"python": platform.python_version(), "platform": platform.platform()})
st.write({"EODHD_API_TOKEN_set": bool(os.getenv("EODHD_API_TOKEN"))})
st.write({"time": time.ctime()})
