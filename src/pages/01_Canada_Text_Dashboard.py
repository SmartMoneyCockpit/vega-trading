
import streamlit as st
from utils import title_with_flag, ensure_token_notice
from components.morning_report import render_morning_report
from components.macro_calendar import render_calendar
from components.tradingview import embed
from components.vectorvest_scanner import render_scanner

title_with_flag("Canada Text Dashboard", "Canada")
ensure_token_notice()

with st.expander("📰 Morning Report", expanded=True):
    render_morning_report("Canada Morning Report", [('ZEB','TO'),('XIU','TO'),('ZGRO','TO')], notes="Auto-summary using benchmark quotes.")

with st.expander("📆 Economic Calendar", expanded=True):
    render_calendar("Canada", "CA")

with st.expander("📈 TradingView Chart", expanded=True):
    sym = st.text_input("Symbol (TradingView, e.g., TSX:ZEB / NASDAQ:AMZN / BMV:WALMEX)", "TSX:ZEB")
    embed(sym, height=610, interval="D")

with st.expander("📊 VectorVest-style Scanner", expanded=True):
    exch = st.selectbox("Exchange suffix", ['TO','CN',''], index=0)
    render_scanner(['ZEB','CPD','ZPR','HPR','ZGRO'], exch, benchmark=[('ZEB','TO'),('XIU','TO'),('ZGRO','TO')])
