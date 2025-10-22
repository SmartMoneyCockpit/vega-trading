
import os
import requests

EODHD_API_TOKEN = os.getenv("EODHD_API_TOKEN", "")

BASE = "https://eodhd.com/api"

def _get(url: str, params: dict) -> dict:
    if not EODHD_API_TOKEN:
        return {"error": "EODHD_API_TOKEN not set"}
    p = dict(params)
    p["api_token"] = EODHD_API_TOKEN
    p["fmt"] = "json"
    r = requests.get(url, params=p, timeout=20)
    try:
        r.raise_for_status()
        return r.json()
    except Exception as e:
        return {"error": str(e), "status": getattr(r, "status_code", None), "text": getattr(r, "text", "")}

def get_price_quote(ticker: str, exchange: str = "") -> dict:
    symbol = f"{ticker}{('.' + exchange) if exchange else ''}"
    url = f"{BASE}/real-time/{symbol}"
    return _get(url, {})

def get_eod_history(ticker: str, exchange: str = "", period: str = "d", order: str = "a", from_="2020-01-01") -> dict:
    symbol = f"{ticker}{('.' + exchange) if exchange else ''}"
    url = f"{BASE}/eod/{symbol}"
    return _get(url, {"from": from_, "period": period, "order": order})
