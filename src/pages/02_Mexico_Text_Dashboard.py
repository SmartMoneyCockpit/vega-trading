
import streamlit as st
from utils import title_with_flag, ensure_token_notice
from components.morning_report import render_morning_report
from components.macro_calendar import render_calendar
from components.tradingview import embed
from components.vectorvest_scanner import render_scanner

title_with_flag("Mexico Text Dashboard", "Mexico")
ensure_token_notice()

with st.expander("📰 Morning Report", expanded=True):
    render_morning_report("Mexico Morning Report", [('WALMEX','MX'),('AC','MX'),('NAFTRAC','MX')], notes="Auto-summary using benchmark quotes.")

with st.expander("📆 Economic Calendar", expanded=True):
    render_calendar("Mexico", "MX")

with st.expander("📈 TradingView Chart", expanded=True):
    sym = st.text_input("Symbol (TradingView, e.g., TSX:ZEB / NASDAQ:AMZN / BMV:WALMEX)", "BMV:WALMEX")
    embed(sym, height=610, interval="D")

with st.expander("📊 VectorVest-style Scanner", expanded=True):
    exch = st.selectbox("Exchange suffix", ['MX','BMV',''], index=0)
    render_scanner(['WALMEX','GMEXICO','KIMBER','ALFA'], exch, benchmark=[('WALMEX','MX'),('AC','MX'),('NAFTRAC','MX')])
