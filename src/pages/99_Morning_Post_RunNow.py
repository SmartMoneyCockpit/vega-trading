import os,sys,time,subprocess,streamlit as st
st.title('Morning Post — Run Now')
if st.button('Generate Morning Post'):
    res=subprocess.run([sys.executable,'tools/morning_post.py'])
    st.success('Done')
