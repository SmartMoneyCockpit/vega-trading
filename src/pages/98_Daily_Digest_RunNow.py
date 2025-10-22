import os,sys,time,subprocess,streamlit as st
st.title('Daily Digest — Run Now')
if st.button('Generate'):
    res=subprocess.run([sys.executable,'tools/daily_digest.py'])
    st.success('Done')
