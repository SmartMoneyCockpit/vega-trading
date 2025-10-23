
import numpy as np
import pandas as pd

# ---- Helpers ----

def _to_returns(df: pd.DataFrame, price_col: str = "close", freq: str = "D") -> pd.Series:
    s = pd.to_numeric(df[price_col], errors="coerce").ffill()
    r = s.pct_change().dropna()
    # normalize freq (assume business days if daily; annualization factors below will handle scale)
    return r

def _ann_factor(freq: str) -> float:
    # Map to approximate periods per year
    if freq.upper() in ("D","DAY","DAILY"):
        return 252.0
    if freq.upper() in ("W","WEEK","WEEKLY"):
        return 52.0
    if freq.upper() in ("M","MO","MONTH","MONTHLY"):
        return 12.0
    if freq.upper() in ("H","HOUR","HOURLY"):
        return 252.0*6.5  # rough trading hours
    return 252.0

# ---- Core metrics ----

def sharpe(returns: pd.Series, rf: float = 0.0, freq: str = "D") -> float:
    ann = _ann_factor(freq)
    ex = returns - (rf/ann)
    mu = ex.mean()
    sd = ex.std(ddof=1)
    if sd == 0 or np.isnan(sd): 
        return np.nan
    return (mu / sd) * np.sqrt(ann)

def sortino(returns: pd.Series, rf: float = 0.0, freq: str = "D") -> float:
    ann = _ann_factor(freq)
    ex = returns - (rf/ann)
    downside = ex[ex < 0]
    dd = downside.std(ddof=1)
    if dd == 0 or np.isnan(dd):
        return np.nan
    mu = ex.mean()
    return (mu / dd) * np.sqrt(ann)

def beta_alpha(returns: pd.Series, bench: pd.Series, rf: float = 0.0, freq: str = "D"):
    # align
    df = pd.concat([returns, bench], axis=1).dropna()
    if df.shape[0] < 2:
        return np.nan, np.nan
    r = df.iloc[:,0] - 0.0  # rf in returns space approximated as 0 per step; ann handled in alpha calc
    b = df.iloc[:,1]
    cov = np.cov(r, b, ddof=1)
    var_b = cov[1,1]
    if var_b == 0 or np.isnan(var_b):
        return np.nan, np.nan
    beta = cov[0,1] / var_b
    # Jensen's alpha (annualized)
    ann = _ann_factor(freq)
    mean_r = r.mean() * ann
    mean_b = b.mean() * ann
    alpha = mean_r - (rf + beta * (mean_b - rf))
    return float(beta), float(alpha)

def volatility(returns: pd.Series, freq: str = "D") -> float:
    ann = _ann_factor(freq)
    return returns.std(ddof=1) * np.sqrt(ann)

def max_drawdown(series: pd.Series) -> float:
    # series can be price or equity curve
    s = series.dropna()
    if s.empty:
        return np.nan
    roll_max = s.cummax()
    dd = (s / roll_max) - 1.0
    return dd.min()

def cagr(df: pd.DataFrame, price_col: str = "close", freq: str = "D") -> float:
    s = pd.to_numeric(df[price_col], errors="coerce").ffill()
    s = s.dropna()
    if s.shape[0] < 2:
        return np.nan
    start, end = s.iloc[0], s.iloc[-1]
    # approximate years elapsed
    n = df.index.to_series().dropna()
    if isinstance(n.index, pd.RangeIndex) or not hasattr(n.iloc[0], "to_datetime64"):
        # Try to infer via count/ann
        ann = _ann_factor(freq)
        years = len(s) / ann
    else:
        years = (n.iloc[-1] - n.iloc[0]).days / 365.25
        if years <= 0:
            years = len(s) / _ann_factor(freq)
    if start <= 0:
        return np.nan
    return (end / start) ** (1.0 / years) - 1.0

def cvar(returns: pd.Series, alpha: float = 0.05) -> float:
    # Conditional Value at Risk (Expected Shortfall) at given tail prob
    if returns.empty:
        return np.nan
    q = returns.quantile(alpha)
    tail = returns[returns <= q]
    if tail.empty:
        return np.nan
    return tail.mean()

def rolling_metrics(returns: pd.Series, window: int = 63):
    # 63 trading days ~ quarter
    out = {}
    out["roll_sharpe"] = returns.rolling(window).apply(lambda x: np.sqrt(252)* (x.mean() / (x.std(ddof=1) if x.std(ddof=1)!=0 else np.nan)), raw=False)
    out["roll_vol"] = returns.rolling(window).std(ddof=1) * np.sqrt(252)
    return pd.DataFrame(out)

# ---- Composite Scoring ----

DEFAULT_WEIGHTS = {
    "sharpe": 0.22,
    "sortino": 0.18,
    "beta": 0.10,       # lower is better; we invert in scoring
    "vol": 0.10,        # lower is better; we invert
    "mdd": 0.15,        # higher drawdown is worse; invert
    "cvar": 0.10,       # more negative is worse; invert
    "cagr": 0.15
}

def _zscore(x: pd.Series) -> pd.Series:
    return (x - x.mean()) / (x.std(ddof=1) if x.std(ddof=1) else 1.0)

def composite_score(metrics: dict, weights: dict = None) -> float:
    """
    metrics keys: sharpe, sortino, beta, vol, mdd, cvar, cagr
    Returns 0..100 score.
    """
    if weights is None:
        weights = DEFAULT_WEIGHTS.copy()
    # Convert to a pandas series for consistent math
    m = pd.Series(metrics, dtype=float)

    # Build a "higher is better" vector
    # Invert risk-side:
    #   beta => (1 - abs(beta-1)) or simply negative zscore; we use negative zscore approach for stability
    #   vol, mdd, cvar => lower is better
    df = pd.DataFrame({k: [m.get(k, np.nan)] for k in ["sharpe","sortino","beta","vol","mdd","cvar","cagr"]})
    df = df.astype(float)

    # Zscore across a tiny reference isn't meaningful; instead, we transform features:
    # - keep sharpe, sortino, cagr as-is
    # - invert: inv_beta = -abs(beta-1), inv_vol = -vol, inv_mdd = -abs(mdd), inv_cvar = -abs(cvar)
    inv_beta = -abs(df.loc[0, "beta"]) if np.isfinite(df.loc[0, "beta"]) else np.nan
    inv_vol  = -df.loc[0, "vol"] if np.isfinite(df.loc[0, "vol"]) else np.nan
    inv_mdd  = -abs(df.loc[0, "mdd"]) if np.isfinite(df.loc[0, "mdd"]) else np.nan
    inv_cvar = -abs(df.loc[0, "cvar"]) if np.isfinite(df.loc[0, "cvar"]) else np.nan

    transformed = {
        "sharpe": df.loc[0,"sharpe"],
        "sortino": df.loc[0,"sortino"],
        "beta": inv_beta,
        "vol": inv_vol,
        "mdd": inv_mdd,
        "cvar": inv_cvar,
        "cagr": df.loc[0,"cagr"]
    }

    # Normalize each component to 0..1 via logistic-ish squashing for stability
    def squash(x):
        if not np.isfinite(x):
            return 0.5
        return 1.0 / (1.0 + np.exp(-x))

    contribs = {k: squash(v) * (weights.get(k,0)) for k,v in transformed.items()}
    raw = sum(contribs.values())
    # scale by sum of weights and convert to 0..100
    wsum = sum([weights.get(k,0) for k in transformed.keys()]) or 1.0
    score01 = raw / wsum
    return float(np.clip(score01 * 100.0, 0.0, 100.0))

def score_from_prices(
    df: pd.DataFrame,
    benchmark: pd.DataFrame = None,
    price_col: str = "close",
    rf: float = 0.0,
    freq: str = "D",
    weights: dict = None
) -> dict:
    # Prepare returns and equity
    r = _to_returns(df, price_col=price_col, freq=freq)
    eq = (1 + r).cumprod()

    if benchmark is not None:
        rb = _to_returns(benchmark, price_col=price_col, freq=freq)
    else:
        rb = None

    s = sharpe(r, rf=rf, freq=freq)
    so = sortino(r, rf=rf, freq=freq)
    b, a = (np.nan, np.nan)
    if rb is not None:
        b, a = beta_alpha(r, rb, rf=rf, freq=freq)
    vol = volatility(r, freq=freq)
    mdd = max_drawdown(eq)
    es  = cvar(r, alpha=0.05)
    cg  = cagr(df, price_col=price_col, freq=freq)

    metrics = {
        "sharpe": s,
        "sortino": so,
        "beta": b,
        "alpha": a,
        "vol": vol,
        "mdd": mdd,
        "cvar": es,
        "cagr": cg
    }

    score = composite_score(metrics, weights=weights)
    metrics["score"] = score
    return metrics
