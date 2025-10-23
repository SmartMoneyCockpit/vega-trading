# Defensive Overlay — Bundle

Adds a composite **Risk Index** (0–100) and status (🟢/🟡/🔴) using:
- **VIX**
- **TLT/SPY** defensive ratio
- **Yield curve** (10y-2y)
- **Sector breadth** from Sector Momentum Tiles CSV
- **RS flips** from `data/alerts/*_flips_*.json`

Files:
- `src/engine/defensive_signals.py`
- `src/pages/60_Defensive_Overlay_Status.py`

Run:
  streamlit run src/pages/60_Defensive_Overlay_Status.py
