# src/pages/09_Country_Hub.py
import streamlit as st

st.set_page_config(page_title="Country Hub", page_icon="🧭", layout="wide")
st.title("🧭 Country Hub")
st.caption("Quick links by group (no file renames).")

cols = st.columns(4)
with cols[0]:
    st.subheader("USA")
    st.link_button("Scanner (USA)", "/?page=01_Scanner_OnDemand.py", use_container_width=True)
    st.link_button("Morning Report (NA)", "/?page=02_Morning_Report.py", use_container_width=True)

with cols[1]:
    st.subheader("Canada")
    st.link_button("TSX Dashboard", "/?page=03_Canada_Dashboard.py", use_container_width=True)
    st.link_button("Preferreds Panel", "/?page=04_Preferreds.py", use_container_width=True)

with cols[2]:
    st.subheader("Mexico")
    st.link_button("Mexico Dashboard", "/?page=05_Mexico_Dashboard.py", use_container_width=True)

with cols[3]:
    st.subheader("System / News")
    st.link_button("System Status", "/?page=90_System_Status.py", use_container_width=True)
    st.link_button("News Updates", "/?page=91_News_Updates.py", use_container_width=True)
    st.link_button("Morning Post — Run Now", "/?page=99_Morning_Post_RunNow.py", use_container_width=True)

st.info("This hub organizes navigation without changing existing page filenames.")
