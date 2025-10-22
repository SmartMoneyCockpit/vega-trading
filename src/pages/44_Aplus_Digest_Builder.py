
import streamlit as st
from utils import title_with_flag
from components.news_store import add_update

title_with_flag("A+ Digest Builder", "")
st.info("Compose an A+ Digest and post it to **News Updates** (no email).")

title = st.text_input("Title", "A+ Setups — Midday Digest")
html = st.text_area("HTML Content", "<h3>A+ Setups</h3><ul><li>SPY — Buy Today (VST 1.12)</li></ul>", height=240)

if st.button("Post to News Updates"):
    ok = add_update(title, html)
    if ok:
        st.success("Posted to News Updates.")
    else:
        st.error("Failed to post update.")
