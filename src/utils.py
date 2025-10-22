
import os
import streamlit as st

def country_flag(country: str) -> str:
    m = {"Canada":"🇨🇦","Mexico":"🇲🇽","United States":"🇺🇸","Europe":"🇪🇺","APAC":"🌏"}
    return m.get(country, "🌐")

def title_with_flag(title: str, country: str = ""):
    f = country_flag(country) if country else "📊"
    st.markdown(f"# {f} {title}")

def ensure_token_notice():
    if not os.getenv("EODHD_API_TOKEN"):
        st.warning("EODHD_API_TOKEN is not set. Add it in your environment (Render → Environment).")
