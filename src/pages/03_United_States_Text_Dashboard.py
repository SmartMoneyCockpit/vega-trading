
import streamlit as st
from utils import title_with_flag, ensure_token_notice
from components.morning_report import render_morning_report
from components.macro_calendar import render_calendar
from components.tradingview import embed
from components.vectorvest_scanner import render_scanner

title_with_flag("United States Text Dashboard", "United States")
ensure_token_notice()

with st.expander("📰 Morning Report", expanded=True):
    render_morning_report("United States Morning Report", [('SPY','US'),('QQQ','US'),('RWM','US')], notes="Auto-summary using benchmark quotes.")

with st.expander("📆 Economic Calendar", expanded=True):
    render_calendar("United States", "US")

with st.expander("📈 TradingView Chart", expanded=True):
    sym = st.text_input("Symbol (TradingView, e.g., TSX:ZEB / NASDAQ:AMZN / BMV:WALMEX)", "NYSE:SPY")
    embed(sym, height=610, interval="D")

with st.expander("📊 VectorVest-style Scanner", expanded=True):
    exch = st.selectbox("Exchange suffix", ['US',''], index=0)
    render_scanner(['SPY','AMZN','NEE','QQQ','RWM','SQQQ'], exch, benchmark=[('SPY','US'),('QQQ','US'),('RWM','US')])
