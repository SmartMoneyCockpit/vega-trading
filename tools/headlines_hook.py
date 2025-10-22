# tools/headlines_hook.py
"""
Optional external headlines hook.
Return a list of dicts: {"title": str, "url": Optional[str], "source": Optional[str]}.
This is DISABLED by default (toggle in src/config/settings.yaml).
"""
from typing import List, Dict

def get_headlines(limit: int = 8) -> List[Dict]:
    # Placeholder: integrate your feed here (EODHD/news, RSS, etc.)
    # Example static sample; replace with real implementation.
    sample = [
        {"title": "Futures mixed ahead of data", "source": "Placeholder Wire"},
        {"title": "Energy climbs as crude stabilizes", "source": "Placeholder Wire"},
    ]
    return sample[:limit]
