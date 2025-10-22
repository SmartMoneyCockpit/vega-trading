# src/components/tradingview_widgets.py
import streamlit as st

def advanced_chart(symbol: str, height: int = 720):
    # TradingView Advanced Chart widget embed
    html = f"""
<div class="tradingview-widget-container" style="height:{height}px;">
  <div id="tv-advanced-chart"></div>
  <script type="text/javascript" src="https://s3.tradingview.com/tv.js"></script>
  <script type="text/javascript">
    new TradingView.widget({{
        "container_id": "tv-advanced-chart",
        "width": "100%",
        "height": "{height}",
        "symbol": "{symbol}",
        "interval": "D",
        "timezone": "America/Los_Angeles",
        "theme": "light",
        "style": "1",
        "locale": "en",
        "allow_symbol_change": true,
        "studies": ["RSI@tv-basicstudies","MAExp@tv-basicstudies","MASimple@tv-basicstudies"],
        "withdateranges": true,
        "hide_side_toolbar": false,
        "save_image": false
    }});
  </script>
</div>
"""
    st.components.v1.html(html, height=height+20, scrolling=False)

def economic_calendar(country: str = "CA", height: int = 520):
    # TradingView Economic Calendar widget (public)
    # country codes: US, CA, MX, etc. Multiple via comma like "US,CA,MX"
    html = f"""
<div class="tradingview-widget-container">
  <div id="economic-calendar-widget"></div>
  <script type="text/javascript" src="https://s3.tradingview.com/external-embedding/embed-widget-events.js" async>
  {{
    "width": "100%",
    "height": "{height}",
    "importanceFilter": "-1,0,1",
    "currencyFilter": "{country}",
    "locale": "en"
  }}
  </script>
</div>
"""
    st.components.v1.html(html, height=height+10, scrolling=True)
