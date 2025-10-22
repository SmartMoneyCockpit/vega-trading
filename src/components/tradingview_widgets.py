# src/components/tradingview_widgets.py
import json
import streamlit as st

def advanced_chart(symbol: str, height: int = 720):
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


def economic_calendar(country: str = "US", height: int = 520):
    """
    Fixed version: uses json.dumps to embed TradingView config safely.
    Prevents f-string format errors when { } braces appear in the JSON.
    """
    cfg = {
        "width": "100%",
        "height": str(height),
        "importanceFilter": "-1,0,1",
        "currencyFilter": country,
        "locale": "en",
    }
    html = f"""
<div class="tradingview-widget-container">
  <div id="economic-calendar-widget"></div>
  <script type="text/javascript" src="https://s3.tradingview.com/external-embedding/embed-widget-events.js" async>
  {json.dumps(cfg)}
  </script>
</div>
"""
    st.components.v1.html(html, height=height+10, scrolling=True)
