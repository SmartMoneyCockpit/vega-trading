
import streamlit as st
import pandas as pd
from utils import title_with_flag
from components.email_digest import send_a_plus_digest

title_with_flag("A+ Digest Builder", "")
st.info("Build an email that sends ONLY when ≥1 Buy Today appears. Provide recipients and click Send.")

recipients_raw = st.text_area("Recipients (comma-separated emails)", "")
subject = st.text_input("Subject", "Vega A+ Setups")
html = st.text_area("HTML Content", "<h3>A+ Setups</h3><p>Attach CSV/PDF from scanner or paste highlights here.</p>", height=200)

if st.button("Send Test Email"):
    recips = [e.strip() for e in recipients_raw.split(",") if e.strip()]
    result = send_a_plus_digest(subject, html, recips)
    if "error" in result:
        st.error(result["error"])
    else:
        st.success(f"Email sent: status {result.get('status')}")
