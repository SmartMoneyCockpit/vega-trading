
import streamlit as st

def embed(symbol: str, height: int = 610, interval: str = "D"):
    html = f'''
    <div class="tradingview-widget-container">
      <div id="tvchart"></div>
      <script type="text/javascript" src="https://s3.tradingview.com/tv.js"></script>
      <script type="text/javascript">
        new TradingView.widget({{
          "symbol": "{symbol}",
          "interval": "{interval}",
          "timezone": "Etc/UTC",
          "theme": "light",
          "style": "1",
          "locale": "en",
          "allow_symbol_change": true,
          "container_id": "tvchart",
          "autosize": true,
          "studies": ["MASimple@tv-basicstudies","RSI@tv-basicstudies","EMA@tv-basicstudies"]
        }});
      </script>
    </div>
    '''
    st.components.v1.html(html, height=height, scrolling=False)
