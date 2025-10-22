
import streamlit as st
from components.tradingview import embed
from utils import title_with_flag

title_with_flag("TradingView Charts", "")
symbol = st.text_input("Symbol (e.g., NASDAQ:AMZN, NYSE:SPY, TSX:ZEB, BMV:WALMEX)", "NASDAQ:AMZN")
height = st.slider("Height", 400, 1000, 610, 10)
interval = st.selectbox("Interval", ["D","240","60","30","15"], index=0)
embed(symbol, height=height, interval=interval)
