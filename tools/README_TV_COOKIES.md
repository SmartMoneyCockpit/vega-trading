# TradingView cookies for authenticated sector embeds

Set your cookies as a single header string (same as a browser 'Cookie' header).

## Environment variable
TRADINGVIEW_COOKIES="sessionid=...; tv_ecuid=...; device_id=..."

## Streamlit secrets (URLs)
[secrets.toml]
TV_URL_USA = "https://www.tradingview.com/screener/sector/usa/"
TV_URL_CAN = ""
TV_URL_MEX = ""
TV_URL_LATAM = ""

Run proxy:
uvicorn src.services.http_gateway.tv_proxy:app --host 0.0.0.0 --port 8081
