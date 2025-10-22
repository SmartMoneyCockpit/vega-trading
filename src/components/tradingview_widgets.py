def advanced_chart(symbol,height=720):
    import streamlit as st
    html=f'''<div class="tradingview-widget-container" style="height:{height}px;"><div id="tv"></div><script src="https://s3.tradingview.com/tv.js"></script><script>new TradingView.widget({{"container_id":"tv","width":"100%","height":"{height}","symbol":"{symbol}","interval":"D","timezone":"America/Los_Angeles","theme":"light","style":"1","locale":"en","allow_symbol_change":true,"studies":["RSI@tv-basicstudies","MAExp@tv-basicstudies","MASimple@tv-basicstudies"],"withdateranges":true}});</script></div>'''
    st.components.v1.html(html,height=height+20)

def economic_calendar(country="US,CA,MX",height=520):
    import streamlit as st
    html=f'''<div class="tradingview-widget-container"><div id="cal"></div><script src="https://s3.tradingview.com/external-embedding/embed-widget-events.js" async>{ {"width":"100%","height":"%s","importanceFilter":"-1,0,1","currencyFilter":"%s","locale":"en"} }</script></div>'''%(height,country)
    st.components.v1.html(html,height=height+10)
