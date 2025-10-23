
# Sector Flip Alerts — Bundle

**Rules (default)**
1. **Relative return flip:** sector vs country index changes sign and exceeds **±0.6%** over the last **15 minutes**.
2. **Momentum + volume:** **EMA(10) – EMA(30)** crosses zero **AND** volume ≥ **1.2×** 20‑bar average.

**What this page does**
- Upload intraday CSVs (index + sector ETFs), run the flip detector, view alerts, and save them to `data/alerts/`.
- Exports a CSV for other cockpit modules (Defensive Overlay, A+ digest).

**Files**
- `src/engine/sector_flip.py`
- `src/pages/70_Sector_Flip_Alerts.py`
- `tools/sector_flips_settings.example.toml`

**CSV formats**
```
datetime,close,volume
2025-10-21 09:35,152.34,123456
2025-10-21 09:36,152.41,101234
...
```

**Run**
```bash
streamlit run src/pages/70_Sector_Flip_Alerts.py
```
