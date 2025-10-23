
# US Scanner Pro – Delta Patch

This delta adds:
1. **`pages/09_US_Scanner_Pro.py`** — a working scanner UI for Rising/Falling Wedge with “Run Scanner”, results table, and quick send-to-chart.
2. **`src/scanner/patterns.py`** — lightweight wedge detection via regression channels.
3. A **News + USA Morning Report** panel on the same page reading:
   - `data/news.json`
   - `reports/usa_morning.md`

> Keep your existing “US Stock Market” page. This new page is meant to be a fast, reliable fallback while we patch that original file.

---

## Known error on your current page
You’re hitting:
```
TypeError: Invalid comparison between dtype=datetime64[ns] and Timestamp
```
**Cause:** `within_earnings_window` (or equivalent) compares a NumPy/pandas datetime64 array against a pandas `Timestamp`. Fix by converting both sides to the same type.

### One-line safe compare
Replace comparisons like:
```python
if np_values <= pd.Timestamp(some_date):
```
with:
```python
lhs = pd.to_datetime(np_values).tz_localize(None)
rhs = pd.to_datetime(some_date).tz_localize(None)
mask = lhs <= rhs
```

### Drop-in helper you can paste into `src/engine/smart_money.py`
```python
import pandas as pd

def _norm_ts(x):
    x = pd.to_datetime(x, errors="coerce")
    try:
        return x.tz_localize(None)
    except Exception:
        return x

def within_earnings_window(dates, days=3, now=None):
    \"\"\"Return True if `now` is within +/- days of any date in `dates`.
    Accepts list/Series/ndarray of datetimes/strings.
    \"\"\"
    if now is None:
        now = pd.Timestamp.utcnow().tz_localize(None)
    else:
        now = _norm_ts(now)

    ser = pd.Series(dates)
    ser = _norm_ts(ser)
    ser = ser.dropna()

    if ser.empty:
        return False

    lower = now - pd.Timedelta(days=days)
    upper = now + pd.Timedelta(days=days)

    # All sides normalized to tz-naive pandas Timestamps
    in_window = (ser >= lower) & (ser <= upper)
    return bool(in_window.any())
```
This removes the dtype mismatch and will stop the crash you showed.

---

## Wiring notes
- The new Scanner page uses `yfinance` inside `src/scanner/patterns.py` for portability. If you already have your own data loader, swap `_load_ohlc` to call it.
- Morning Report loader expects `reports/usa_morning.md`. Your digest cron can write to that path.

---

## Next steps
1. Add the cron `vega-home-feeds` (already provided) to keep `data/news.json` fresh.
2. Patch `within_earnings_window` as shown.
3. Later, we can merge this scanner logic back into your original US page.
