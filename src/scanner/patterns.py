
import numpy as np
import pandas as pd

def _load_ohlc(symbol: str, lookback: int = 400):
    """Lightweight loader using pandas_datareader fallback to yfinance if available in the parent app.
    Expect the parent app to have a data loader; if not, we try yfinance here.
    """
    try:
        import yfinance as yf
        df = yf.download(symbol, period="2y", interval="1d", auto_adjust=True, progress=False)
    except Exception:
        df = pd.DataFrame()
    if df is None or df.empty:
        return pd.DataFrame()
    df = df.tail(lookback)
    df = df.rename(columns=str.title)
    if "Close" not in df.columns:
        if "Adj Close" in df.columns:
            df["Close"] = df["Adj Close"]
    return df[["Open","High","Low","Close"]].copy()

def _linreg(x, y):
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    n = len(x)
    if n < 2:
        return (0.0, 0.0)
    A = np.vstack([x, np.ones(n)]).T
    m, b = np.linalg.lstsq(A, y, rcond=None)[0]
    return (m, b)

def _channel_slope_quality(highs, lows):
    """Compute simple upper/lower regression channels and return slope + fit quality."""
    idx = np.arange(len(highs))
    m_hi, b_hi = _linreg(idx, highs)
    m_lo, b_lo = _linreg(idx, lows)
    # quality = negative mean absolute error to favor tighter channels
    fit_hi = -np.mean(np.abs((m_hi*idx + b_hi) - highs))
    fit_lo = -np.mean(np.abs((m_lo*idx + b_lo) - lows))
    fit = (fit_hi + fit_lo) / 2.0
    return (m_hi, b_hi, m_lo, b_lo, fit)

def _is_rising_wedge(df: pd.DataFrame) -> (bool, float):
    highs = df["High"].values
    lows  = df["Low"].values
    m_hi, b_hi, m_lo, b_lo, fit = _channel_slope_quality(highs, lows)
    # Rising wedge: both slopes positive but upper slope (m_hi) < lower slope (m_lo)
    cond = (m_hi > 0) and (m_lo > 0) and (m_hi < m_lo)
    # score favors tight channels and bigger slope difference
    score = float(fit + (m_lo - m_hi))
    return cond, score

def _is_falling_wedge(df: pd.DataFrame) -> (bool, float):
    highs = df["High"].values
    lows  = df["Low"].values
    m_hi, b_hi, m_lo, b_lo, fit = _channel_slope_quality(highs, lows)
    # Falling wedge: both slopes negative but lower slope (m_lo) > upper slope (m_hi) (closer to zero)
    cond = (m_hi < 0) and (m_lo < 0) and (m_lo > m_hi)
    score = float(fit + (m_lo - m_hi))
    return cond, score

def find_wedges(symbol: str, pattern: str = "Both", lookback: int = 400):
    df = _load_ohlc(symbol, lookback)
    if df.empty or len(df) < 100:
        return None

    res = {"symbol": symbol, "rising": 0, "falling": 0, "score": 0.0}
    if pattern in ("Rising Wedge","Both"):
        ok, sc = _is_rising_wedge(df)
        if ok:
            res["rising"] = 1
            res["score"] = max(res["score"], sc)
    if pattern in ("Falling Wedge","Both"):
        ok, sc = _is_falling_wedge(df)
        if ok:
            res["falling"] = 1
            res["score"] = max(res["score"], sc)
    if (res["rising"] == 0) and (res["falling"] == 0):
        return None
    return res

def find_wedges_batch(symbols, pattern="Both", lookback=400):
    out = []
    for sym in symbols:
        try:
            r = find_wedges(sym, pattern=pattern, lookback=lookback)
            if r:
                out.append(r)
        except Exception:
            continue
    if not out:
        return pd.DataFrame(columns=["symbol","rising","falling","score"])
    df = pd.DataFrame(out).sort_values("score", ascending=False).reset_index(drop=True)
    return df
